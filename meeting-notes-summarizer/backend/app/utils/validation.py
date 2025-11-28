"""
Validation, normalization and repair utilities.
All comments in code must be written in English.
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from dateparser import parse as dp_parse
from datetime import datetime


def normalize_deadline_iso(text: Optional[str], ref: Optional[datetime] = None) -> Optional[str]:
    """Normalize a natural language date to ISO YYYY-MM-DD if possible."""
    if not text:
        return None
    settings = {
        "RELATIVE_BASE": ref or datetime.utcnow(),
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    dt = dp_parse(text, settings=settings)
    if not dt:
        return None
    try:
        return dt.date().isoformat()
    except Exception:
        return None


def is_one_sentence(text: str) -> bool:
    """Check if the text is one sentence (simple heuristic)."""
    if not text:
        return False
    # Count sentence enders
    count = len(re.findall(r"[.!?]", text))
    # Allow zero or one terminator as one sentence
    return count <= 1 and len(text.splitlines()) == 1


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def too_verbatim(bullet: str, transcript: str, threshold: float = 0.4) -> bool:
    """Check if bullet looks copied from transcript by simple ratio heuristic."""
    if not bullet:
        return False
    b = bullet.strip().lower()
    t = transcript.lower()
    if b in t and len(b) >= 20:  # substring and not too short
        return True
    # Jaccard-like check
    bw = set(re.findall(r"\w+", b))
    tw = set(re.findall(r"\w+", t))
    if not bw:
        return False
    inter = len(bw & tw)
    ratio = inter / max(1, len(bw))
    return ratio >= threshold


def enforce_action_item_rules(item: Dict[str, Any], participants: List[str], ref: Optional[datetime] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Enforce action item rules: one-sentence task, assignee in participants, normalize deadline.
    Returns (fixed_item, flags)
    """
    fixed = dict(item)
    flags: Dict[str, Any] = {"modified": False, "issues": []}

    # Task must be one sentence and concise
    task = fixed.get("task", "").strip()
    if not is_one_sentence(task) or word_count(task) > 24:
        # Simplify by truncating heuristically; LLM rewrite may be applied later by caller
        task = re.sub(r"\s+", " ", task)
        # Keep first sentence up to a terminator or 24 words
        m = re.split(r"[.!?]", task, maxsplit=1)
        first = m[0].strip()
        words = first.split()
        if len(words) > 24:
            first = " ".join(words[:24])
        fixed["task"] = first
        flags["modified"] = True
        flags["issues"].append("task_trimmed")

    # Assignee must be a participant name
    assignee = fixed.get("assignee")
    if assignee and assignee not in participants:
        fixed["assignee"] = None
        flags["modified"] = True
        flags["issues"].append("assignee_not_in_participants")

    # Normalize deadline to ISO
    deadline = fixed.get("deadline")
    norm = normalize_deadline_iso(deadline, ref)
    if deadline and norm != deadline:
        fixed["deadline"] = norm
        flags["modified"] = True
        flags["issues"].append("deadline_normalized")

    return fixed, flags


def enforce_decision_rules(dec: Dict[str, Any], participants: List[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Ensure decision is one sentence and owner is in participants if present."""
    fixed = dict(dec)
    flags: Dict[str, Any] = {"modified": False, "issues": []}

    decision = fixed.get("decision", "").strip()
    if not is_one_sentence(decision) or word_count(decision) > 28:
        m = re.split(r"[.!?]", decision, maxsplit=1)
        first = (m[0] if m else decision).strip()
        words = first.split()
        if len(words) > 28:
            first = " ".join(words[:28])
        fixed["decision"] = first
        flags["modified"] = True
        flags["issues"].append("decision_trimmed")

    owner = fixed.get("owner")
    if owner and owner not in participants:
        fixed["owner"] = None
        flags["modified"] = True
        flags["issues"].append("owner_not_in_participants")

    return fixed, flags


def build_quality_report(summary: Dict[str, Any], action_items: List[Dict[str, Any]], decisions: List[Dict[str, Any]], transcript: str, participants: List[str]) -> Dict[str, Any]:
    """Compute simple quality metrics for audit."""
    rep: Dict[str, Any] = {}
    # Summary
    bullets = summary.get("bullets", []) if summary else []
    verbatim_count = sum(1 for b in bullets if too_verbatim(b, transcript))
    rep["summary_verbatim_bullets"] = verbatim_count

    # Actions
    actions_no_assignee = sum(1 for a in action_items if not a.get("assignee"))
    actions_long_task = sum(1 for a in action_items if word_count(a.get("task", "")) > 24)
    rep["actions_no_assignee"] = actions_no_assignee
    rep["actions_long_task"] = actions_long_task

    # Decisions
    decisions_no_owner = sum(1 for d in decisions if not d.get("owner"))
    rep["decisions_no_owner"] = decisions_no_owner

    rep["participants"] = participants
    return rep

