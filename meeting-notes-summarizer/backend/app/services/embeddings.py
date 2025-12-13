"""
Embeddings + semantic search service using Pinecone.

This service focuses on embedding structured meeting artifacts (summaries, action items, decisions)
and enabling semantic retrieval + answering via an LLM.
All comments in code must be written in English.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy.orm import Session

from openai import AzureOpenAI, AuthenticationError
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings
from app.models import ActionItem, Decision, Meeting, Summary

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for indexing meeting artifacts into Pinecone and answering questions using semantic search."""

    # -----------------------------
    # Azure OpenAI clients
    # -----------------------------

    @staticmethod
    def _get_embeddings_client() -> AzureOpenAI:
        """Client used ONLY for embeddings."""
        return AzureOpenAI(
            api_key=settings.azure_openai_embedding_api_key,
            api_version=settings.azure_openai_embedding_api_version,
            azure_endpoint=settings.azure_openai_embedding_endpoint,
        )

    @staticmethod
    def _get_chat_client() -> AzureOpenAI:
        """Client used ONLY for chat completions."""
        return AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )

    # -----------------------------
    # Embeddings
    # -----------------------------

    @staticmethod
    def _embed_text(text: str) -> List[float]:
        """Create an embedding vector for the given text using Azure OpenAI embeddings."""
        text = (text or "").strip()
        if not text:
            return []

        client = EmbeddingsService._get_embeddings_client()
        try:
            resp = client.embeddings.create(
                model=settings.azure_openai_embedding_deployment_name,
                input=text,
            )
            return resp.data[0].embedding
        except AuthenticationError:
            logger.exception(
                "Embedding request failed (auth/model access). "
                "Check Azure embeddings deployment + AZURE_OPENAI_EMBEDDING_* settings."
            )
            return []

    @staticmethod
    def _embedding_dimension() -> int:
        """
        Determine embedding vector dimension from the configured embeddings deployment.

        Pinecone index dimension must exactly match the embedding vector length.
        """
        vec = EmbeddingsService._embed_text("dimension_probe")
        if not vec:
            raise RuntimeError(
                "Unable to create embeddings to determine vector dimension. "
                "Check AZURE_OPENAI_EMBEDDING_* settings and model permissions."
            )
        return len(vec)

    # -----------------------------
    # Text formatting (what gets embedded)
    # -----------------------------

    @staticmethod
    def _format_summary_text(summary: Summary) -> str:
        """Convert stored bullets into a single text chunk suitable for embedding."""
        bullets = summary.bullets_json or []
        if isinstance(bullets, list):
            bullet_text = "\n".join(f"- {b}" for b in bullets if isinstance(b, str) and b.strip())
        else:
            bullet_text = ""
        return bullet_text.strip()

    @staticmethod
    def _format_action_item_text(item: ActionItem) -> str:
        """Convert an ActionItem into a text chunk suitable for embedding."""
        parts: List[str] = []
        parts.append("Type: ActionItem")
        parts.append(f"Task: {str(item.task or '').strip()}")

        if item.assignee:
            parts.append(f"Assignee: {str(item.assignee).strip()}")

        if item.deadline:
            # Use ISO format for consistent retrieval.
            if isinstance(item.deadline, datetime):
                parts.append(f"Deadline: {item.deadline.date().isoformat()}")
            else:
                parts.append(f"Deadline: {str(item.deadline)}")

        if item.priority:
            parts.append(f"Priority: {str(item.priority).strip()}")

        if item.status:
            parts.append(f"Status: {str(item.status).strip()}")

        if item.source_quote:
            sq = str(item.source_quote).strip()
            if sq:
                parts.append(f"Source quote: {sq}")

        return "\n".join(parts).strip()

    @staticmethod
    def _format_decision_text(decision: Decision) -> str:
        """Convert a Decision into a text chunk suitable for embedding."""
        parts: List[str] = []
        parts.append("Type: Decision")
        parts.append(f"Decision: {str(decision.decision or '').strip()}")

        # Owner/source_quote exist on your model; indexing them improves retrieval even if you only asked for `decision`.
        if getattr(decision, "owner", None):
            owner = str(getattr(decision, "owner") or "").strip()
            if owner:
                parts.append(f"Owner: {owner}")

        if getattr(decision, "source_quote", None):
            sq = str(getattr(decision, "source_quote") or "").strip()
            if sq:
                parts.append(f"Source quote: {sq}")

        return "\n".join(parts).strip()

    # -----------------------------
    # Pinecone
    # -----------------------------

    @staticmethod
    def _pinecone_client():
        """
        Create a Pinecone client instance.

        Uses pinecone-client v3 API.
        """
        try:
            from pinecone import Pinecone  # type: ignore
        except Exception as e:  # noqa
            raise RuntimeError(
                "Pinecone client is not installed. Ensure pinecone-client is in requirements.txt and installed."
            ) from e

        return Pinecone(api_key=settings.pinecone_api_key)

    @staticmethod
    def _ensure_pinecone_index_exists() -> None:
        """
        Ensure Pinecone index exists. If missing, create it.

        This makes POST /api/chatbot/index succeed on fresh environments without requiring manual index creation.
        """
        pc = EmbeddingsService._pinecone_client()
        index_name = settings.pinecone_index_name

        existing = pc.list_indexes()
        names = set(getattr(existing, "names", lambda: [])())
        if index_name in names:
            return

        try:
            from pinecone import ServerlessSpec  # type: ignore
        except Exception as e:  # noqa
            raise RuntimeError(
                "Pinecone ServerlessSpec is unavailable. Ensure pinecone-client is installed and up to date."
            ) from e

        dimension = EmbeddingsService._embedding_dimension()

        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )

        # Wait briefly for the index to become ready.
        for _ in range(30):
            existing = pc.list_indexes()
            names = set(getattr(existing, "names", lambda: [])())
            if index_name in names:
                return
            time.sleep(1)

        raise RuntimeError(f"Pinecone index '{index_name}' was requested to be created but is not visible yet.")

    @staticmethod
    def _pinecone_index():
        """Get Pinecone Index handle; auto-creates index if missing."""
        EmbeddingsService._ensure_pinecone_index_exists()
        pc = EmbeddingsService._pinecone_client()
        return pc.Index(settings.pinecone_index_name)

    # -----------------------------
    # Upserts (one record at a time)
    # -----------------------------

    @staticmethod
    def _upsert_vector(
        *,
        vector_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Internal helper to upsert a single vector into Pinecone."""
        index = EmbeddingsService._pinecone_index()
        index.upsert(
            vectors=[{"id": vector_id, "values": vector, "metadata": metadata}],
            namespace=settings.pinecone_namespace,
        )

    @staticmethod
    def upsert_summary(db: Session, summary_id: int) -> int:
        """
        Upsert a single Summary into Pinecone.

        Returns:
            1 if upserted, 0 if skipped
        """
        summary: Optional[Summary] = db.query(Summary).filter(Summary.id == summary_id).first()
        if not summary:
            return 0

        meeting: Optional[Meeting] = db.query(Meeting).filter(Meeting.id == summary.meeting_id).first()
        if not meeting:
            return 0

        text = EmbeddingsService._format_summary_text(summary)
        if not text:
            return 0

        vector = EmbeddingsService._embed_text(text)
        if not vector:
            return 0

        vector_id = f"meeting-{meeting.id}-summary-{summary.id}"
        metadata = {
            "source_type": "summary",
            "source_id": summary.id,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "text": text,
        }
        EmbeddingsService._upsert_vector(vector_id=vector_id, vector=vector, metadata=metadata)
        return 1

    @staticmethod
    def upsert_action_item(db: Session, action_item_id: int) -> int:
        """
        Upsert a single ActionItem into Pinecone.

        Returns:
            1 if upserted, 0 if skipped
        """
        item: Optional[ActionItem] = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
        if not item:
            return 0

        meeting: Optional[Meeting] = db.query(Meeting).filter(Meeting.id == item.meeting_id).first()
        if not meeting:
            return 0

        text = EmbeddingsService._format_action_item_text(item)
        if not text:
            return 0

        vector = EmbeddingsService._embed_text(text)
        if not vector:
            return 0

        vector_id = f"meeting-{meeting.id}-action-item-{item.id}"
        metadata = {
            "source_type": "action_item",
            "source_id": item.id,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "text": text,
        }
        EmbeddingsService._upsert_vector(vector_id=vector_id, vector=vector, metadata=metadata)
        return 1

    @staticmethod
    def upsert_decision(db: Session, decision_id: int) -> int:
        """
        Upsert a single Decision into Pinecone.

        Returns:
            1 if upserted, 0 if skipped
        """
        dec: Optional[Decision] = db.query(Decision).filter(Decision.id == decision_id).first()
        if not dec:
            return 0

        meeting: Optional[Meeting] = db.query(Meeting).filter(Meeting.id == dec.meeting_id).first()
        if not meeting:
            return 0

        text = EmbeddingsService._format_decision_text(dec)
        if not text:
            return 0

        vector = EmbeddingsService._embed_text(text)
        if not vector:
            return 0

        vector_id = f"meeting-{meeting.id}-decision-{dec.id}"
        metadata = {
            "source_type": "decision",
            "source_id": dec.id,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "text": text,
        }
        EmbeddingsService._upsert_vector(vector_id=vector_id, vector=vector, metadata=metadata)
        return 1

    # -----------------------------
    # Indexing entry points (called by chatbot.py)
    # -----------------------------

    @staticmethod
    def index_meeting_summaries(db: Session, meeting_id: int) -> int:
        """
        Index all meeting artifacts (Summary + ActionItem + Decision) for a specific meeting.

        NOTE: Method name is kept for compatibility with chatbot.py, but indexing now includes more than summaries.
        Returns the total number of vectors successfully upserted.
        """
        count = 0

        summaries: List[Summary] = db.query(Summary).filter(Summary.meeting_id == meeting_id).all()
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)

        action_items: List[ActionItem] = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
        for ai in action_items:
            count += EmbeddingsService.upsert_action_item(db, ai.id)

        decisions: List[Decision] = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
        for d in decisions:
            count += EmbeddingsService.upsert_decision(db, d.id)

        return count

    @staticmethod
    def index_all_summaries(db: Session, limit: Optional[int] = None) -> int:
        """
        Index meeting artifacts (Summary + ActionItem + Decision) for all meetings (optionally limited).

        NOTE: Method name is kept for compatibility with chatbot.py, but indexing now includes more than summaries.
        Returns the total number of vectors successfully upserted.
        """
        count = 0

        # Summaries
        q_s = db.query(Summary).order_by(Summary.id.asc())
        if limit is not None:
            q_s = q_s.limit(limit)
        summaries: List[Summary] = q_s.all()
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)

        # Action items (use the same limit as a safety cap if provided)
        q_a = db.query(ActionItem).order_by(ActionItem.id.asc())
        if limit is not None:
            q_a = q_a.limit(limit)
        action_items: List[ActionItem] = q_a.all()
        for ai in action_items:
            count += EmbeddingsService.upsert_action_item(db, ai.id)

        # Decisions
        q_d = db.query(Decision).order_by(Decision.id.asc())
        if limit is not None:
            q_d = q_d.limit(limit)
        decisions: List[Decision] = q_d.all()
        for d in decisions:
            count += EmbeddingsService.upsert_decision(db, d.id)

        return count

    # -----------------------------
    # Query + Answer
    # -----------------------------

    @staticmethod
    def _query_pinecone(
        question: str,
        top_k: int = 5,
        meeting_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone by embedding the question and returning raw match dicts.

        Returns:
            List of dicts with keys: id, score, metadata
        """
        vector = EmbeddingsService._embed_text(question)
        if not vector:
            return []

        index = EmbeddingsService._pinecone_index()

        query_kwargs: Dict[str, Any] = {
            "namespace": settings.pinecone_namespace,
            "vector": vector,
            "top_k": max(1, min(int(top_k), 20)),
            "include_metadata": True,
        }

        if meeting_ids:
            query_kwargs["filter"] = {"meeting_id": {"$in": [int(x) for x in meeting_ids]}}

        res = index.query(**query_kwargs)
        matches = getattr(res, "matches", None) or []

        out: List[Dict[str, Any]] = []
        for m in matches:
            out.append(
                {
                    "id": getattr(m, "id", None),
                    "score": float(getattr(m, "score", 0.0) or 0.0),
                    "metadata": getattr(m, "metadata", None) or {},
                }
            )
        return out

    @staticmethod
    def answer_question(
        db: Session,
        question: str,
        top_k: int = 5,
        meeting_ids: Optional[List[int]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Semantic search meeting artifacts in Pinecone and generate an answer grounded on retrieved snippets.

        Returns:
            answer_text, sources
        """
        question = (question or "").strip()
        if not question:
            return "Please provide a question.", []

        matches = EmbeddingsService._query_pinecone(question=question, top_k=top_k, meeting_ids=meeting_ids)

        sources: List[Dict[str, Any]] = []
        context_blocks: List[str] = []

        for m in matches:
            md = m.get("metadata") or {}
            meeting_id = int(md.get("meeting_id") or 0)
            source_id = int(md.get("source_id") or 0)  # stored from any table
            title = str(md.get("title") or "")
            text = str(md.get("text") or "")
            score = float(m.get("score") or 0.0)

            snippet = text[:400].strip()
            sources.append(
                {
                    "meeting_id": meeting_id,
                    "summary_id": source_id,  # schema compatibility (represents the underlying source record id)
                    "title": title,
                    "score": score,
                    "snippet": snippet,
                }
            )

            if snippet:
                context_blocks.append(f"[{meeting_id}/{source_id}] {title}\n{snippet}")

        if not context_blocks:
            return (
                "I couldn't find relevant indexed meeting information yet. "
                "Try indexing first, and make sure summaries/action items/decisions exist in the database.",
                [],
            )

        system = (
            "You are a helpful assistant. Answer the user's question using ONLY the provided meeting snippets. "
            "If the answer is not present in the snippets, say you don't know. Keep the answer concise and practical."
        )
        user = (
            "Question:\n"
            f"{question}\n\n"
            "Meeting snippets:\n"
            + "\n\n---\n\n".join(context_blocks)
        )

        client = EmbeddingsService._get_chat_client()
        messages: List[ChatCompletionMessageParam] = [
            cast(ChatCompletionMessageParam, {"role": "system", "content": system}),
            cast(ChatCompletionMessageParam, {"role": "user", "content": user}),
        ]
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            temperature=0.2,
            top_p=0.1,
            max_tokens=500,
            messages=messages,
        )

        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            answer = "I couldn't generate an answer from the available snippets."

        return answer, sources