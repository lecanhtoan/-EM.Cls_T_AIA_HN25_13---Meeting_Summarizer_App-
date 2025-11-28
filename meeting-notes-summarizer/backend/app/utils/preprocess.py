"""
Preprocessing utilities: speaker segmentation and participant extraction.
All comments in code must be written in English.
"""
from typing import List, Dict, Tuple
import re

SPEAKER_LINE_RE = re.compile(r"^([A-Z][a-zA-Z]+)\s*:\s*(.*)$")


def segment_by_speaker(text: str) -> List[Dict[str, str]]:
    """Split transcript into segments by speaker: [{'speaker','text'}]."""
    segments: List[Dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = SPEAKER_LINE_RE.match(line)
        if m:
            speaker = m.group(1).strip()
            content = m.group(2).strip()
            segments.append({"speaker": speaker, "text": content})
        else:
            # Append to last speaker if exists, otherwise create anonymous
            if segments:
                segments[-1]["text"] = (segments[-1]["text"] + " " + line).strip()
            else:
                segments.append({"speaker": "Unknown", "text": line})
    return segments


def extract_participants(segments: List[Dict[str, str]]) -> List[str]:
    """Collect unique speakers as participants preserving first appearance order."""
    seen = set()
    participants: List[str] = []
    for seg in segments:
        spk = seg.get("speaker", "").strip()
        if spk and spk not in seen and spk != "Unknown":
            seen.add(spk)
            participants.append(spk)
    return participants


def normalize_transcript_text(segments: List[Dict[str, str]]) -> str:
    """Rebuild a normalized transcript text without multiple blank lines."""
    lines: List[str] = []
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        content = seg.get("text", "").strip()
        if content:
            lines.append(f"{speaker}: {content}")
    return "\n".join(lines)

