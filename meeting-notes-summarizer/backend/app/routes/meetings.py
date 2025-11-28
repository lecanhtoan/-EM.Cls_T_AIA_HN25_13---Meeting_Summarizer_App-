"""
API routes for meeting operations.
Handles file uploads, text input, and meeting retrieval.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    TextMeetingRequest,
    MeetingResultResponse,
    MeetingDetailResponse,
    MeetingListResponse,
    MeetingListItem,
    UpdateActionItemsRequest,
)
from app.services.summarization import SummarizationService
from app.models import Meeting, ActionItem
from datetime import datetime

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("/upload", response_model=MeetingResultResponse)
async def upload_transcript(
    file: UploadFile = File(...),
    title: str = Form(...),
    language: str = Form(default="en"),
    db: Session = Depends(get_db)
):
    """
    Upload a transcript file (.txt or .md) and process it.
    
    Args:
        file: The transcript file to upload
        title: Meeting title
        language: Language code (default: en)
        db: Database session
    
    Returns:
        Meeting results with summary, action items, and decisions
    """
    
    # Validate file type
    if file.filename.endswith(('.txt', '.md')):
        file_type = file.filename.split('.')[-1]
    else:
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")
    
    # Read file content
    content = await file.read()
    transcript_text = content.decode('utf-8')
    
    # Process transcript
    result = SummarizationService.process_transcript(
        db=db,
        transcript_text=transcript_text,
        title=title,
        language=language,
        file_name=file.filename,
        file_type=file_type
    )
    
    return result


@router.post("/text", response_model=MeetingResultResponse)
async def process_text_transcript(
    request: TextMeetingRequest,
    db: Session = Depends(get_db)
):
    """
    Process transcript text directly (paste mode).
    
    Args:
        request: Request containing title, language, and transcript_text
        db: Database session
    
    Returns:
        Meeting results with summary, action items, and decisions
    """
    
    # Process transcript
    result = SummarizationService.process_transcript(
        db=db,
        transcript_text=request.transcript_text,
        title=request.title,
        language=request.language
    )
    
    return result


@router.get("/", response_model=MeetingListResponse)
async def list_meetings(db: Session = Depends(get_db)):
    """List all processed meetings."""
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    items = [
        MeetingListItem(
            id=m.id, title=m.title, language=m.language, source=m.source, created_at=m.created_at
        )
        for m in meetings
    ]
    return {"meetings": items}


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve complete details for a meeting.
    """
    result = SummarizationService.get_meeting_details(db, meeting_id)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return result


@router.put("/{meeting_id}", response_model=MeetingDetailResponse)
async def update_meeting_action_items(
    meeting_id: int,
    payload: UpdateActionItemsRequest,
    db: Session = Depends(get_db),
):
    """Update multiple action items for a given meeting and return updated details."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Update each action item if it belongs to the meeting
    from datetime import datetime
    for it in payload.items:
        ai = db.query(ActionItem).filter(ActionItem.id == it.id, ActionItem.meeting_id == meeting_id).first()
        if not ai:
            continue
        if it.task is not None:
            ai.task = it.task
        if it.assignee is not None:
            ai.assignee = it.assignee
        if it.priority is not None:
            ai.priority = it.priority
        if it.status is not None:
            ai.status = it.status
        if it.deadline is not None:
            # Parse ISO-like date string; accept YYYY-MM-DD or full ISO
            try:
                if "T" in it.deadline:
                    ai.deadline = datetime.fromisoformat(it.deadline)
                else:
                    ai.deadline = datetime.strptime(it.deadline, "%Y-%m-%d")
            except Exception:
                ai.deadline = None

    db.commit()

    # Return updated meeting details
    result = SummarizationService.get_meeting_details(db, meeting_id)
    return result


