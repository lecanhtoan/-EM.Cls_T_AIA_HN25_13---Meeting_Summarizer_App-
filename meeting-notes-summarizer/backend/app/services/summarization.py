"""
Summarization service that orchestrates the complete pipeline.
Handles transcript processing,
    -> function calling,
        -> database persistence
            -> and automatically Pinecone indexing after a meeting is summarized.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models import Meeting, Transcript, Summary, ActionItem, Decision, ToolRun, User
from app.azure_client import azure_client
from app.utils.preprocess import segment_by_speaker, extract_participants, normalize_transcript_text
from app.utils.validation import enforce_action_item_rules, enforce_decision_rules, build_quality_report, too_verbatim

import logging
from app.services.embeddings import EmbeddingsService

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
            user_id: int = 1  # Default user for MVP
    ) -> Dict[str, Any]:
        """
        Process a transcript through the complete pipeline:
        1. Create meeting and transcript records
        2. Call Azure OpenAI with function calling
        3. Parse and persist results to database
        4. Return structured results

        Args:
            db: Database session
            transcript_text: The transcript content
            title: Meeting title
            language: Language code (default: en)
            file_name: Original file name (if uploaded)
            file_type: File type (txt, md, etc.)
            user_id: User ID (default: 1 for MVP)

        Returns:
            Dictionary with meeting_id and extracted data
        """

        # Get or create default user for MVP
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email="demo@example.com",
                full_name="Demo User"
            )
            db.add(user)
            db.commit()

        # Create meeting record
        meeting = Meeting(
            user_id=user_id,
            title=title,
            language=language,
            source="upload" if file_name else "text",
            meeting_date=datetime.utcnow()
        )
        db.add(meeting)
        db.flush()  # Get the meeting ID without committing

        # Create transcript record
        transcript = Transcript(
            meeting_id=meeting.id,
            raw_text=transcript_text,
            clean_text=transcript_text,
            file_name=file_name,
            file_type=file_type
        )
        db.add(transcript)
        db.flush()

        # Preprocess transcript: segment speakers and normalize text
        segments = segment_by_speaker(transcript_text)
        participants: List[str] = extract_participants(segments)
        normalized_text = normalize_transcript_text(segments)

        # Call Azure OpenAI with function calling (participants-aware)
        ai_results = azure_client.call_functions(
            normalized_text, language, participants)

        # Post-process summary: paraphrase bullets if too verbatim
        summary_payload = ai_results.get("summary") or {}
        bullets = summary_payload.get("bullets", [])
        if any(too_verbatim(b, normalized_text) for b in bullets):
            bullets = azure_client.paraphrase_bullets(
                bullets, language=language)
        summary_payload["bullets"] = bullets

        # Process and persist summary
        if summary_payload:
            summary = Summary(
                meeting_id=meeting.id,
                style=summary_payload.get("style", "short"),
                max_bullets=summary_payload.get("max_bullets", 6),
                bullets_json=summary_payload.get("bullets", []),
                model_name=ai_results.get("tool_runs", [
                    {}])[-1].get("model_name", "gpt-4") if ai_results.get("tool_runs") else "gpt-4"
            )
            db.add(summary)

        # Post-process action items
        fixed_actions = []
        for item_data in ai_results.get("action_items", []):
            fixed, flags = enforce_action_item_rules(
                item_data, participants, ref=meeting.meeting_date)
            fixed_actions.append(fixed)
            # Convert ISO date string to datetime if present
            deadline_value = fixed.get("deadline")
            deadline_dt = None
            if isinstance(deadline_value, str):
                try:
                    if "T" in deadline_value:
                        deadline_dt = datetime.fromisoformat(deadline_value)
                    else:
                        deadline_dt = datetime.strptime(
                            deadline_value, "%Y-%m-%d")
                except Exception:
                    deadline_dt = None

            action_item = ActionItem(
                meeting_id=meeting.id,
                task=fixed.get("task", ""),
                assignee=fixed.get("assignee"),
                deadline=deadline_dt,
                priority=fixed.get("priority", "medium"),
                status=fixed.get("status", "open")
            )
            db.add(action_item)

        # Post-process decisions
        fixed_decisions = []
        for decision_data in ai_results.get("decisions", []):
            fixed_dec, flags = enforce_decision_rules(
                decision_data, participants)
            fixed_decisions.append(fixed_dec)
            decision = Decision(
                meeting_id=meeting.id,
                decision=fixed_dec.get("decision", ""),
                owner=fixed_dec.get("owner")
            )
            db.add(decision)

        # Log tool runs
        if ai_results.get("tool_runs"):
            for tool_run_data in ai_results["tool_runs"]:
                tool_run = ToolRun(
                    meeting_id=meeting.id,
                    tool_name=tool_run_data.get("tool_name", ""),
                    input_json=tool_run_data.get("input", {}),
                    output_json=tool_run_data.get("output", {}),
                    model_name=tool_run_data.get("model_name", "gpt-4"),
                    latency_ms=tool_run_data.get("latency_ms")
                )
                db.add(tool_run)

        # Quality report as dedicated tool_run
        quality_report = build_quality_report(
            summary_payload or {}, fixed_actions, fixed_decisions, normalized_text, participants)
        quality_run = ToolRun(
            meeting_id=meeting.id,
            tool_name="quality_report",
            input_json={"participants": participants},
            output_json=quality_report,
            model_name="validator",
            latency_ms=0,
        )
        db.add(quality_run)

        # Commit all changes
        db.commit()
        db.refresh(meeting)

        # Auto-index meeting summaries into Pinecone (best-effort; do not fail the API on indexing errors)
        try:
            EmbeddingsService.index_meeting_summaries(db, meeting_id=meeting.id)
        except Exception:
            logger.exception("Auto-indexing to Pinecone failed for meeting_id=%s", meeting.id)

        # Prepare response
        response = {
            "meeting_id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "created_at": meeting.created_at,
            "summary": None,
            "action_items": [],
            "decisions": []
        }

        # Fetch and include summary
        summary = db.query(Summary).filter(
            Summary.meeting_id == meeting.id).first()
        if summary:
            response["summary"] = {
                "bullets": summary.bullets_json,
                "style": summary.style,
                "max_bullets": summary.max_bullets
            }

        # Fetch and include action items
        action_items = db.query(ActionItem).filter(
            ActionItem.meeting_id == meeting.id).all()
        response["action_items"] = [
            {
                "id": item.id,
                "task": item.task,
                "assignee": item.assignee,
                "deadline": item.deadline,
                "priority": item.priority,
                "status": item.status
            }
            for item in action_items
        ]

        # Fetch and include decisions
        decisions = db.query(Decision).filter(
            Decision.meeting_id == meeting.id).all()
        response["decisions"] = [
            {
                "id": decision.id,
                "decision": decision.decision,
                "owner": decision.owner,
                "decision_date": decision.decision_date
            }
            for decision in decisions
        ]

        return response

    @staticmethod
    def get_meeting_details(db: Session, meeting_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete details for a meeting.

        Args:
            db: Database session
            meeting_id: Meeting ID

        Returns:
            Dictionary with meeting details or None if not found
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return None

        response = {
            "id": meeting.id,
            "title": meeting.title,
            "language": meeting.language,
            "source": meeting.source,
            "created_at": meeting.created_at,
            "summary": None,
            "action_items": [],
            "decisions": []
        }

        # Fetch summary
        summary = db.query(Summary).filter(
            Summary.meeting_id == meeting_id).first()
        if summary:
            response["summary"] = {
                "bullets": summary.bullets_json,
                "style": summary.style,
                "max_bullets": summary.max_bullets
            }

        # Fetch action items
        action_items = db.query(ActionItem).filter(
            ActionItem.meeting_id == meeting_id).all()
        response["action_items"] = [
            {
                "id": item.id,
                "task": item.task,
                "assignee": item.assignee,
                "deadline": item.deadline,
                "priority": item.priority,
                "status": item.status
            }
            for item in action_items
        ]

        # Fetch decisions
        decisions = db.query(Decision).filter(
            Decision.meeting_id == meeting_id).all()
        response["decisions"] = [
            {
                "id": decision.id,
                "decision": decision.decision,
                "owner": decision.owner,
                "decision_date": decision.decision_date
            }
            for decision in decisions
        ]

        return response
