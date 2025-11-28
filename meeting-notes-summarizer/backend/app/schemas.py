"""
Pydantic schemas for request/response validation.
Defines the data structures for API endpoints.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ============================================================================
# Request Schemas
# ============================================================================

class TextMeetingRequest(BaseModel):
    """Request schema for processing transcript text directly."""
    title: str
    language: str = "en"
    transcript_text: str


class ActionItemUpdate(BaseModel):
    """Update schema for a single action item."""
    id: int
    task: Optional[str] = None
    assignee: Optional[str] = None
    deadline: Optional[str] = None  # ISO date string
    priority: Optional[str] = None  # low|medium|high
    status: Optional[str] = None    # open|done|canceled


class UpdateActionItemsRequest(BaseModel):
    """Request to update multiple action items for a meeting."""
    items: List[ActionItemUpdate]


# ============================================================================
# Response Schemas
# ============================================================================

class SummaryResponse(BaseModel):
    """Response schema for summary data."""
    bullets: List[str]
    style: str
    max_bullets: int
    
    class Config:
        from_attributes = True


class ActionItemResponse(BaseModel):
    """Response schema for action item data."""
    id: int
    task: str
    assignee: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = "medium"
    status: str = "open"
    
    class Config:
        from_attributes = True


class DecisionResponse(BaseModel):
    """Response schema for decision data."""
    id: int
    decision: str
    owner: Optional[str] = None
    decision_date: datetime
    
    class Config:
        from_attributes = True


class MeetingResultResponse(BaseModel):
    """Response schema for complete meeting results."""
    meeting_id: int
    title: str
    language: str
    created_at: datetime
    summary: Optional[SummaryResponse] = None
    action_items: List[ActionItemResponse] = []
    decisions: List[DecisionResponse] = []
    
    class Config:
        from_attributes = True


class MeetingDetailResponse(BaseModel):
    """Response schema for detailed meeting information."""
    id: int
    title: str
    language: str
    source: str
    created_at: datetime
    summary: Optional[SummaryResponse] = None
    action_items: List[ActionItemResponse] = []
    decisions: List[DecisionResponse] = []
    
    class Config:
        from_attributes = True


class MeetingListItem(BaseModel):
    """List item schema for meetings overview."""
    id: int
    title: str
    language: str
    source: str
    created_at: datetime


class MeetingListResponse(BaseModel):
    """Meetings list response."""
    meetings: List[MeetingListItem]
