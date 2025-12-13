"""
Embeddings + semantic search service using Pinecone.

This service focuses on embedding *summarized output* (Summary.bullets_json)
and enabling semantic retrieval + answering via an LLM.
All comments in code must be written in English.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from openai import AzureOpenAI
from openai import AuthenticationError

from app.config import settings
from app.models import Meeting, Summary

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for indexing summaries into Pinecone and answering questions using semantic search."""

    @staticmethod
    def _get_openai_client() -> AzureOpenAI:
        return AzureOpenAI(
            api_key=settings.azure_openai_embedding_api_key,
            api_version=settings.azure_openai_embedding_api_version,
            azure_endpoint=settings.azure_openai_embedding_endpoint,
        )

    @staticmethod
    def _embed_text(text: str) -> List[float]:
        """Create an embedding vector for the given text using Azure OpenAI embeddings."""
        text = (text or "").strip()
        if not text:
            return []

        client = EmbeddingsService._get_openai_client()
        try:
            resp = client.embeddings.create(
                model=settings.azure_openai_embedding_deployment_name,
                input=text,
            )
            return resp.data[0].embedding
        except AuthenticationError as e:
            # Most common cause: the API key does not have access to the embedding deployment/model.
            # Example: key only allows GPT-4o-mini but embeddings call needs an embeddings-capable deployment.
            logger.error(
                "Embedding request failed due to authentication/authorization. "
                "Check AZURE_OPENAI_API_KEY permissions and "
                "azure_openai_embedding_deployment_name. Details: %s",
                str(e),
            )
            return []

    # ... existing code ...

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
            # Make the failure mode explicit (common when embeddings are unavailable/unauthorized).
            return (
                "I couldn't run semantic search (embeddings unavailable) or no relevant meeting summaries were found yet. "
                "If you're just setting up, ensure your embeddings deployment/key is configured and index a meeting first.",
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