"""
SQLAlchemy ORM models for the Meeting Notes Summarizer.
Defines all database tables and relationships.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model - stores user information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meetings = relationship("Meeting", back_populates="user")


class Meeting(Base):
    """Meeting model - represents a single meeting."""
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    meeting_date = Column(DateTime, nullable=True)
    source = Column(String(50), default="upload")  # upload, zoom, meet, etc.
    language = Column(String(10), default="en")
    duration_sec = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="meetings")
    transcript = relationship("Transcript", back_populates="meeting", uselist=False)
    summaries = relationship("Summary", back_populates="meeting")
    action_items = relationship("ActionItem", back_populates="meeting")
    decisions = relationship("Decision", back_populates="meeting")
    tool_runs = relationship("ToolRun", back_populates="meeting")


class Transcript(Base):
    """Transcript model - stores the original meeting transcript."""
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), unique=True, nullable=False)
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)  # txt, md, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="transcript")


class Summary(Base):
    """Summary model - stores extracted summary from a meeting."""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    style = Column(String(50), default="short")  # short, detailed
    max_bullets = Column(Integer, default=5)
    bullets_json = Column(JSON, nullable=False)  # List of bullet points
    model_name = Column(String(100), default="gpt-4")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="summaries")


class ActionItem(Base):
    """ActionItem model - stores extracted action items from a meeting."""
    __tablename__ = "action_items"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    assignee = Column(String(255), nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String(50), default="medium")  # low, medium, high
    status = Column(String(50), default="open")  # open, done, canceled
    source_quote = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")


class Decision(Base):
    """Decision model - stores key decisions made in a meeting."""
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    decision = Column(Text, nullable=False)
    owner = Column(String(255), nullable=True)
    decision_date = Column(DateTime, default=datetime.utcnow)
    source_quote = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")


class ToolRun(Base):
    """ToolRun model - logs each function calling invocation."""
    __tablename__ = "tool_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)  # extract_summary, extract_action_items, etc.
    input_json = Column(JSON, nullable=False)
    output_json = Column(JSON, nullable=False)
    model_name = Column(String(100), default="gpt-4")
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="tool_runs")


