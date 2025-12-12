"""
API routes for chatbot conversations operations.
Handles user prompt that requests questions from summarized meetings notes
and response with answers
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ChatbotAskRequest,
    ChatbotAskResponse,
    ChatbotIndexRequest,
    ChatbotIndexResponse,
    ChatbotSource,
)
from app.services.embeddings import EmbeddingsService

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


@router.post("/index", response_model=ChatbotIndexResponse)
async def index_summaries(payload: ChatbotIndexRequest, db: Session = Depends(get_db)):
    """
    Index stored meeting summaries into Pinecone.

    - If meeting_id is provided: index only that meeting.
    - Else: index all summaries (optionally limited by payload.limit).
    """
    try:
        if payload.meeting_id is not None:
            indexed = EmbeddingsService.index_meeting_summaries(db, meeting_id=payload.meeting_id)
        else:
            indexed = EmbeddingsService.index_all_summaries(db, limit=payload.limit)
        return {"indexed": indexed}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Indexing failed") from e


@router.post("/ask", response_model=ChatbotAskResponse)
async def ask_question(payload: ChatbotAskRequest, db: Session = Depends(get_db)):
    """
    Ask a question over past meeting summaries.

    This endpoint:
    1) Embeds the question
    2) Retrieves top_k relevant summary chunks from Pinecone
    3) Uses Azure OpenAI to answer grounded on retrieved snippets
    """
    try:
        answer, sources = EmbeddingsService.answer_question(
            db=db,
            question=payload.question,
            top_k=payload.top_k,
            meeting_ids=payload.meeting_ids,
        )
        return {
            "answer": answer,
            "sources": [ChatbotSource(**s) for s in sources],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Chatbot query failed") from e