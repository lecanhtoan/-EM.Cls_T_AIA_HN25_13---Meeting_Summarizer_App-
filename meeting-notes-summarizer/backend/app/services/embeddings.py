"""
Embeddings + semantic search service using Pinecone.

This service focuses on embedding *summarized output* (Summary.bullets_json)
and enabling semantic retrieval + answering via an LLM.
All comments in code must be written in English.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from openai import AzureOpenAI

from app.config import settings
from app.models import Meeting, Summary


class EmbeddingsService:
    """Service for indexing summaries into Pinecone and answering questions using semantic search."""

    @staticmethod
    def _get_openai_client() -> AzureOpenAI:
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

        client = EmbeddingsService._get_openai_client()
        resp = client.embeddings.create(
            model=settings.azure_openai_embedding_deployment_name,
            input=text,
        )
        return resp.data[0].embedding

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

        Supports the modern 'pinecone' client API if available via pinecone-client.
        """
        try:
            from pinecone import Pinecone  # type: ignore
        except Exception as e:  # noqa
            raise RuntimeError(
                "Pinecone client is not installed. Ensure pinecone-client is in requirements.txt and installed."
            ) from e

        return Pinecone(api_key=settings.pinecone_api_key)

    @staticmethod
    def _pinecone_index():
        """Get Pinecone Index handle."""
        # assumes the index already exists in Pinecone. If it doesn’t, the first auto-index after summarization will fail
        #  but summarization will still succeed—which is good
        pc = EmbeddingsService._pinecone_client()
        return pc.Index(settings.pinecone_index_name)

    @staticmethod
    def upsert_summary(db: Session, summary_id: int) -> int:
        """
        Upsert a single Summary into Pinecone.

        Returns:
            1 if upserted, 0 if skipped (e.g., missing summary or empty text)
        """
        summary = db.query(Summary).filter(Summary.id == summary_id).first()
        if not summary:
            return 0

        meeting = db.query(Meeting).filter(Meeting.id == summary.meeting_id).first()
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
        """Index all summaries for a specific meeting into Pinecone."""
        summaries = db.query(Summary).filter(Summary.meeting_id == meeting_id).all()
        count = 0
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)
        return count

    @staticmethod
    def index_all_summaries(db: Session, limit: Optional[int] = None) -> int:
        """Index summaries for all meetings into Pinecone (optionally limited)."""
        q = db.query(Summary).order_by(Summary.id.asc())
        if limit is not None:
            q = q.limit(limit)
        summaries = q.all()

        count = 0
        for s in summaries:
            count += EmbeddingsService.upsert_summary(db, s.id)
        return count

    @staticmethod
    def _query_pinecone(question: str, top_k: int = 5, meeting_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Query Pinecone by embedding the question and returning raw match dicts."""
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
        # Normalize to plain dicts for easier downstream usage
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
            return "I couldn't find relevant meeting summaries for that question yet. Try indexing first.", []

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

        client = EmbeddingsService._get_openai_client()
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            temperature=0.2,
            top_p=0.1,
            max_tokens=500,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            answer = "I couldn't generate an answer from the available summaries."

        return answer, sources
