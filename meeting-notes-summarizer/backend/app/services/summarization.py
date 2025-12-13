"""
Summarization service that orchestrates the complete pipeline.

Flow:
    transcript -> preprocessing -> Azure OpenAI function calling -> validation/repair
        -> persistence to PostgreSQL (Meeting/Transcript/Summary/ActionItem/Decision/ToolRun)
            -> best-effort Pinecone indexing (Summary + ActionItem + Decision) via EmbeddingsService
All comments in code must be written in English.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.azure_client import azure_client
from app.models import ActionItem, Decision, Meeting, Summary, ToolRun, Transcript, User
from app.services.embeddings import EmbeddingsService
from app.utils.preprocess import extract_participants, normalize_transcript_text, segment_by_speaker
from app.utils.validation import (
    build_quality_report,
    enforce_action_item_rules,
    enforce_decision_rules,
    too_verbatim,
)

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for processing transcripts and persisting results to database."""

    @staticmethod
    def process_transcript(
        db: Session,
        transcript_text: str,
        title: str,
        language: str = "en",
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        user_id: int = 1,  # Default user for MVP
    ) -> Dict[str, Any]:
        """
        Process a transcript through the complete pipeline:
        1) Create Meeting + Transcript records
        2) Preprocess transcript (speaker segmentation, participants extraction, normalization)
        3) Call Azure OpenAI with function calling to extract summary/action items/decisions
        4) Validate/repair outputs and persist Summary/ActionItem/Decision + ToolRun logs
        5) Commit and then best-effort index ALL artifacts (Summary + ActionItem + Decision) into Pinecone

        Returns:
            Dict ready for API response
        """
        transcript_text = transcript_text or ""
        title = (title or "").strip()
        language = (language or "en").strip()

        if not title:
            title = "Untitled meeting"

        # Get or create default user for MVP
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email="demo@example.com",
                full_name="Demo User",
            )
            db.add(user)
            db.commit()

        # Create meeting record
        meeting = Meeting(
            user_id=user_id,
            title=title,
            language=language,
            source="upload" if file_name else "text",
            meeting_date=datetime.utcnow(),
        )
        db.add(meeting)
        db.flush()  # Allocate meeting.id

        # Create transcript record
        transcript = Transcript(
            meeting_id=meeting.id,
            raw_text=transcript_text,
            clean_text=transcript_text,
            file_name=file_name,
            file_type=file_type,
        )
        db.add(transcript)
        db.flush()

        # Preprocess transcript: segment speakers and normalize text
        segments = segment_by_speaker(transcript_text)
        participants: List[str] = extract_participants(segments)
        normalized_text = normalize_transcript_text(segments)

        # Call Azure OpenAI with function calling (participants-aware)
        ai_results = azure_client.call_functions(
            normalized_text,
            language,
            participants,
        )

        # -----------------------------
        # Summary handling
        # -----------------------------
        summary_payload = ai_results.get("summary") or {}
        bullets = summary_payload.get("bullets", [])
        if any(too_verbatim(b, normalized_text) for b in bullets):
            bullets = azure_client.paraphrase_bullets(bullets, language=language)
        summary_payload["bullets"] = bullets

        if summary_payload:
            summary = Summary(
                meeting_id=meeting.id,
                style=summary_payload.get("style", "short"),
                max_bullets=summary_payload.get("max_bullets", 6),
                bullets_json=summary_payload.get("bullets", []),
                model_name=(
                    ai_results.get("tool_runs", [{}])[-1].get("model_name", "gpt-4")
                    if ai_results.get("tool_runs")
                    else "gpt-4"
                ),
            )
            db.add(summary)

        # -----------------------------
        # Action items handling
        # -----------------------------
        fixed_actions: List[Dict[str, Any]] = []
        for item_data in ai_results.get("action_items", []) or []:
            fixed, _flags = enforce_action_item_rules(
                item_data,
                participants,
                ref=meeting.meeting_date,
            )
            fixed_actions.append(fixed)

            # Convert ISO-like string to datetime if present; else store None
            deadline_dt: Optional[datetime] = None
            deadline_value = fixed.get("deadline")
            if isinstance(deadline_value, str) and deadline_value.strip():
                try:
                    if "T" in deadline_value:
                        deadline_dt = datetime.fromisoformat(deadline_value)
                    else:
                        deadline_dt = datetime.strptime(deadline_value, "%Y-%m-%d")
                except Exception:
                    deadline_dt = None

            action_item = ActionItem(
                meeting_id=meeting.id,
                task=str(fixed.get("task", "") or ""),
                assignee=fixed.get("assignee"),
                deadline=deadline_dt,
                priority=str(fixed.get("priority", "medium") or "medium"),
                status=str(fixed.get("status", "open") or "open"),
                # Store source_quote if your model includes it (it does); improves retrieval if present.
                source_quote=fixed.get("source_quote"),
            )
            db.add(action_item)

        # -----------------------------
        # Decisions handling
        # -----------------------------
        fixed_decisions: List[Dict[str, Any]] = []
        for decision_data in ai_results.get("decisions", []) or []:
            fixed_dec, _flags = enforce_decision_rules(decision_data, participants)
            fixed_decisions.append(fixed_dec)

            decision = Decision(
                meeting_id=meeting.id,
                decision=str(fixed_dec.get("decision", "") or ""),
                owner=fixed_dec.get("owner"),
                # Store source_quote if present.
                source_quote=fixed_dec.get("source_quote"),
            )
            db.add(decision)

        # -----------------------------
        # Tool run logging
        # -----------------------------
        if ai_results.get("tool_runs"):
            for tool_run_data in ai_results["tool_runs"]:
                tool_run = ToolRun(
                    meeting_id=meeting.id,
                    tool_name=tool_run_data.get("tool_name", "") or "",
                    input_json=tool_run_data.get("input", {}) or {},
                    output_json=tool_run_data.get("output", {}) or {},
                    model_name=tool_run_data.get("model_name", "gpt-4") or "gpt-4",
                    latency_ms=tool_run_data.get("latency_ms"),
                )
                db.add(tool_run)

        # Quality report as dedicated ToolRun
        quality_report = build_quality_report(
            summary_payload or {},
            fixed_actions,
            fixed_decisions,
            normalized_text,
            participants,
        )
        quality_run = ToolRun(
            meeting_id=meeting.id,
            tool_name="quality_report",
            input_json={"participants": participants},
            output_json=quality_report,
            model_name="validator",
            latency_ms=0,
        )
        db.add(quality_run)

        # Commit all DB changes to ensure IDs exist for Pinecone vector IDs
        db.commit()
        db.refresh(meeting)

        # -----------------------------
        # Pinecone indexing (FULL: Summary + ActionItem + Decision)
        # -----------------------------
        try:
            indexed = EmbeddingsService.index_meeting_summaries(db, meeting_id=meeting.id)
            logger.info("Auto-indexed %s vectors to Pinecone for meeting_id=%s", indexed, meeting.id)
        except Exception:
            # Best-effort: do not fail the summarization endpoint if Pinecone/embeddings are unavailable.
            logger.exception("Auto-indexing to Pinecone failed for meeting_id=%s", meeting.id)

        # -----------------------------
        # Response payload
        # -----------------------------
        response: Dict[str, Any] = {
            "meeting_id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "created_at": meeting.created_at,
            "summary": None,
            "action_items": [],
            "decisions": [],
        }

        # Fetch and include summary
        summary = db.query(Summary).filter(Summary.meeting_id == meeting.id).first()
        if summary:
            response["summary"] = {
                "bullets": summary.bullets_json,
                "style": summary.style,
                "max_bullets": summary.max_bullets,
            }

        # Fetch and include action items
        action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).all()
        response["action_items"] = [
            {
                "id": item.id,
                "task": item.task,
                "assignee": item.assignee,
                "deadline": item.deadline,
                "priority": item.priority,
                "status": item.status,
            }
            for item in action_items
        ]

        # Fetch and include decisions
        decisions = db.query(Decision).filter(Decision.meeting_id == meeting.id).all()
        response["decisions"] = [
            {
                "id": d.id,
                "decision": d.decision,
                "owner": d.owner,
                "decision_date": d.decision_date,
            }
            for d in decisions
        ]

        return response

    @staticmethod
    def get_meeting_details(db: Session, meeting_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete details for a meeting.

        Returns:
            Dict with meeting details or None if not found
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return None

        response: Dict[str, Any] = {
            "id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "source": meeting.source,
            "created_at": meeting.created_at,
            "summary": None,
            "action_items": [],
            "decisions": [],
        }

        summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
        if summary:
            response["summary"] = {
                "bullets": summary.bullets_json,
                "style": summary.style,
                "max_bullets": summary.max_bullets,
            }

        action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
        response["action_items"] = [
            {
                "id": item.id,
                "task": item.task,
                "assignee": item.assignee,
                "deadline": item.deadline,
                "priority": item.priority,
                "status": item.status,
            }
            for item in action_items
        ]

        decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
        response["decisions"] = [
            {
                "id": d.id,
                "decision": d.decision,
                "owner": d.owner,
                "decision_date": d.decision_date,
            }
            for d in decisions
        ]

        return response