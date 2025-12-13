"""
Embeddings + semantic search service using Pinecone.

This service focuses on embedding *summarized output* (Summary.bullets_json)
and enabling semantic retrieval + answering via an LLM.
All comments in code must be written in English.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy.orm import Session

from openai import AzureOpenAI, AuthenticationError
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings
from app.models import Meeting, Summary

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for indexing summaries into Pinecone and answering questions using semantic search."""

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
            # If embeddings are not available, return empty vector so indexing/querying can gracefully skip.
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
        Ensure pinecone index exists. If missing, create it.

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
        # Pinecone can take a moment after create_index before operations succeed.
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

    @staticmethod
    def upsert_summary(db: Session, summary_id: int) -> int:
        """
        Upsert a single Summary into Pinecone.

        Returns:
            1 if upserted, 0 if skipped (e.g., missing summary or empty text)
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
            # If embeddings are unavailable, skip indexing instead of crashing the whole job.
            return 0

        vector_id = f"meeting-{meeting.id}-summary-{summary.id}"
        metadata = {
            "meeting_id": meeting.id,
            "summary_id": summary.id,
            "title": meeting.title,
            "language": meeting.language,
            "text": text,
        }

        index = EmbeddingsService._pinecone_index()
        index.upsert(
            vectors=[{"id": vector_id, "values": vector, "metadata": metadata}],
            namespace=settings.pinecone_namespace,
        )
        return 1

    @staticmethod
    def index_meeting_summaries(db: Session, meeting_id: int) -> int:
        """
        Index all summaries for a specific meeting into Pinecone.

        Used by POST /api/chatbot/index when meeting_id is provided.
        Returns the number of summaries successfully upserted.
        """
        summaries: List[Summary] = db.query(Summary).filter(Summary.meeting_id == meeting_id).all()
        count = 0
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)
        return count

    @staticmethod
    def index_all_summaries(db: Session, limit: Optional[int] = None) -> int:
        """
        Index summaries for all meetings into Pinecone (optionally limited).

        Used by POST /api/chatbot/index when meeting_id is NOT provided.
        Returns the number of summaries successfully upserted.
        """
        q = db.query(Summary).order_by(Summary.id.asc())
        if limit is not None:
            q = q.limit(limit)
        summaries: List[Summary] = q.all()

        count = 0
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)
        return count

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
        Semantic search summaries in Pinecone and generate an answer grounded on retrieved snippets.

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
            summary_id = int(md.get("summary_id") or 0)
            title = str(md.get("title") or "")
            text = str(md.get("text") or "")
            score = float(m.get("score") or 0.0)

            snippet = text[:400].strip()
            sources.append(
                {
                    "meeting_id": meeting_id,
                    "summary_id": summary_id,
                    "title": title,
                    "score": score,
                    "snippet": snippet,
                }
            )

            if snippet:
                context_blocks.append(f"[{meeting_id}/{summary_id}] {title}\n{snippet}")

        if not context_blocks:
            return (
                "I couldn't find relevant meeting summaries yet (or semantic search isn't available). "
                "Try indexing summaries first, and verify embeddings + Pinecone configuration.",
                [],
            )

        system = (
            "You are a helpful assistant. Answer the user's question using ONLY the provided meeting summary snippets. "
            "If the answer is not present in the snippets, say you don't know. Keep the answer concise and practical."
        )
        user = (
            "Question:\n"
            f"{question}\n\n"
            "Meeting summary snippets:\n"
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
            answer = "I couldn't generate an answer from the available summaries."

        return answer, sources