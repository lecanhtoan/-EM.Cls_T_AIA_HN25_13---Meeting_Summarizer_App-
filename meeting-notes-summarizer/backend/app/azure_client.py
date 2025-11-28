"""
Azure OpenAI client wrapper with function calling support.
Implements strict prompts, function-calling orchestration, validation helpers,
paraphrase utilities, and retry logic to improve extraction quality.
All comments in code must be written in English.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import AzureOpenAI
from app.config import settings
from app.utils.validation import too_verbatim


def _now_ms() -> int:
    import time as _t
    return int(_t.time() * 1000)


class AzureOpenAIClient:
    """Wrapper around Azure OpenAI client for function calling and prompts."""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )
        self.deployment_name = settings.azure_openai_deployment_name
        self.model_name = settings.azure_openai_deployment_name

        # Redesigned tools with stronger constraints
        self.TOOLS = [
            {
                "type": "function",
                "function": {
                    "name": "extract_summary",
                    "description": "Summarize meeting into concise bullets (no verbatim copying).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transcript": {"type": "string"},
                            "language": {"type": "string", "default": "en"},
                            "max_bullets": {"type": "integer", "minimum": 3, "maximum": 10, "default": 6},
                            "constraints": {
                                "type": "object",
                                "properties": {
                                    "no_verbatim": {"type": "boolean", "default": True},
                                    "bullet_max_words": {"type": "integer", "default": 20},
                                    "must_cover": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                        "required": ["transcript"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_action_items",
                    "description": "Extract actionable tasks with assignees and deadlines.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transcript": {"type": "string"},
                            "language": {"type": "string", "default": "en"},
                            "participants": {"type": "array", "items": {"type": "string"}},
                            "rules": {
                                "type": "object",
                                "properties": {
                                    "assignee_must_be_person_name": {"type": "boolean", "default": True},
                                    "assignee_must_be_in_participants": {"type": "boolean", "default": True},
                                    "task_must_be_one_sentence": {"type": "boolean", "default": True},
                                    "normalize_deadline_to_iso": {"type": "boolean", "default": True},
                                    "max_items": {"type": "integer", "default": 10},
                                },
                            },
                        },
                        "required": ["transcript"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_decisions",
                    "description": "Extract key decisions with owner and decision date if present.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transcript": {"type": "string"},
                            "language": {"type": "string", "default": "en"},
                            "participants": {"type": "array", "items": {"type": "string"}},
                            "rules": {
                                "type": "object",
                                "properties": {
                                    "decision_must_be_one_sentence": {"type": "boolean", "default": True},
                                    "owner_must_be_person_name": {"type": "boolean", "default": True},
                                },
                            },
                        },
                        "required": ["transcript"],
                    },
                },
            },
        ]

    # ------------------------ Low-level chat helper with retry ------------------------
    def _chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.1,
        max_tokens: int = 1500,
        retries: int = 2,
    ) -> Any:
        last_err = None
        for attempt in range(retries + 1):
            try:
                return self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
            except Exception as e:  # noqa
                last_err = e
                time.sleep(0.8 * (attempt + 1))
        raise last_err

    # ------------------------ High-level function-call orchestrator ------------------------
    def call_functions(self, transcript: str, language: str = "en", participants: Optional[List[str]] = None) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "summary": None,
            "action_items": [],
            "decisions": [],
            "tool_runs": [],
        }

        system_message = (
            "You are an expert meeting-miner. Always produce concise, structured outputs. "
            "Never copy transcript verbatim except when explicitly asked for source_quote fields."
        )
        developer_guidance = (
            "You MUST call the following tools in any order to complete the task: "
            "extract_summary, extract_action_items, extract_decisions. "
            "Follow constraints strictly. If uncertain, return null values rather than guessing."
        )
        user_message = f"""Analyze the transcript and call the tools:

{transcript}
"""

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": developer_guidance},
            {"role": "user", "content": user_message},
        ]

        start = _now_ms()
        response = self._chat(messages, tools=self.TOOLS, tool_choice="required")
        latency = _now_ms() - start

        # Iterate over tool calling cycle
        while response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls
            assistant_msg = {
                "role": "assistant",
                "content": response.choices[0].message.content or "",
            }
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            tool_results_msgs: List[Dict[str, Any]] = []
            for tc in tool_calls:
                t0 = _now_ms()
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments or "{}")

                # Inject participants and constraints/rules if missing
                if tool_name == "extract_summary":
                    tool_args.setdefault("language", language)
                    tool_args.setdefault("max_bullets", 6)
                    tool_args.setdefault("constraints", {})
                    tool_args["constraints"].setdefault("no_verbatim", True)
                    tool_args["constraints"].setdefault("bullet_max_words", 20)
                    tool_args["constraints"].setdefault("must_cover", [
                        "allocations/points distribution",
                        "roadmap priorities",
                        "timelines (e.g., end of October, Q1)",
                    ])
                    output = self._call_llm_for_summary(tool_args)
                elif tool_name == "extract_action_items":
                    tool_args.setdefault("language", language)
                    tool_args.setdefault("participants", participants or [])
                    tool_args.setdefault("rules", {})
                    tool_args["rules"].setdefault("assignee_must_be_person_name", True)
                    tool_args["rules"].setdefault("assignee_must_be_in_participants", True)
                    tool_args["rules"].setdefault("task_must_be_one_sentence", True)
                    tool_args["rules"].setdefault("normalize_deadline_to_iso", True)
                    tool_args["rules"].setdefault("max_items", 10)
                    output = self._call_llm_for_action_items(tool_args)
                elif tool_name == "extract_decisions":
                    tool_args.setdefault("language", language)
                    tool_args.setdefault("participants", participants or [])
                    tool_args.setdefault("rules", {})
                    tool_args["rules"].setdefault("decision_must_be_one_sentence", True)
                    tool_args["rules"].setdefault("owner_must_be_person_name", True)
                    output = self._call_llm_for_decisions(tool_args)
                else:
                    output = {}

                t_latency = _now_ms() - t0

                # Update results
                if tool_name == "extract_summary":
                    results["summary"] = output
                elif tool_name == "extract_action_items":
                    results["action_items"] = output
                elif tool_name == "extract_decisions":
                    results["decisions"] = output

                # Log run
                results["tool_runs"].append(
                    {
                        "tool_name": tool_name,
                        "input": tool_args,
                        "output": output,
                        "model_name": self.model_name,
                        "latency_ms": t_latency,
                    }
                )

                tool_results_msgs.append(
                    {
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(output),
                    }
                )

            messages.extend(tool_results_msgs)

            # Continue tool loop
            start = _now_ms()
            response = self._chat(messages, tools=self.TOOLS, tool_choice="auto")
            latency = _now_ms() - start

        return results

    # ------------------------ Specialized sub-prompts ------------------------
    def _call_llm_for_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        transcript = args.get("transcript", "")
        language = args.get("language", "en")
        max_bullets = args.get("max_bullets", 6)
        constraints = args.get("constraints", {})
        bullet_max_words = constraints.get("bullet_max_words", 20)
        must_cover = constraints.get("must_cover", [])

        system = (
            "You generate concise bullet-point summaries of meetings. "
            "Do not copy verbatim sentences from the transcript. Each bullet must be <= %d words." % bullet_max_words
        )
        developer = (
            "If topics appear, ensure bullets cover them: %s. "
            "Avoid greetings, pleasantries, and low-signal chatter."
            % (", ".join(must_cover) or "none")
        )
        user = f"""Transcript:
{transcript}

Return JSON with keys: bullets (array of strings, length <= {max_bullets}), style="short", max_bullets={max_bullets}.
"""

        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": developer},
            # Few-shot example: do NOT copy verbatim, cover allocations and timelines
            {"role": "user", "content": "Transcript:\nJohn: We have 120 points this quarter. Sarah: Allocate 30 to analytics, 20 dashboard, 15 mobile, 55 tech-debt. Mike: Announce analytics by end of October. Sarah: Mobile redesign moved to Q1."},
            {"role": "assistant", "content": json.dumps({
                "bullets": [
                    "Engineering capacity ~120 points across quarter",
                    "Points allocation: 30 analytics, 20 dashboard, 15 mobile, 55 technical debt",
                    "Announce analytics to customers by end of October",
                    "Mobile redesign shifted to Q1 to free capacity"
                ],
                "style": "short",
                "max_bullets": max_bullets,
            })},
            # Negative example note
            {"role": "system", "content": "Never output bullets like: 'Sarah: Good morning', 'We need to...', 'John: Sure'. Avoid greetings and verbatim copying."},
            {"role": "user", "content": user},
        ]
        resp = self._chat(messages, tools=None, tool_choice=None, temperature=0.2, top_p=0.1, max_tokens=900)
        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except Exception:
            data = {"bullets": [], "style": "short", "max_bullets": max_bullets}
        # Ensure structure
        data.setdefault("style", "short")
        data.setdefault("max_bullets", max_bullets)
        data.setdefault("bullets", [])
        if isinstance(data.get("bullets"), list):
            data["bullets"] = data["bullets"][: max_bullets]
        else:
            data["bullets"] = []
        return data

    def _call_llm_for_action_items(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        transcript = args.get("transcript", "")
        language = args.get("language", "en")
        participants = args.get("participants", [])
        rules = args.get("rules", {})
        max_items = rules.get("max_items", 10)

        system = (
            "You extract clear, actionable tasks. Each task is a single imperative sentence. "
            "Assignee must be a person name and belong to participants. Normalize deadlines to ISO when possible."
        )
        developer = (
            f"Participants: {participants}. If no explicit deadline, set null. Output at most {max_items} items."
        )
        user = f"""Transcript:
{transcript}

Return a JSON array of items: [{{"task":str, "assignee":str|null, "deadline":YYYY-MM-DD|null, "priority":"high|medium|low", "status":"open"}}]
- task: single sentence, <= 24 words
- assignee: must be in participants or null
- deadline: ISO date when explicit (e.g., 'Friday', 'next Wednesday', 'end of October'), else null
- priority: infer high for critical items otherwise medium
"""
        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": developer},
            # Few-shot (good)
            {"role": "user", "content": "Transcript:\nSarah: John will lead analytics implementation. John: I will prepare the technical design doc by Friday. Lisa: I will deliver dashboard mockups next Wednesday."},
            {"role": "assistant", "content": json.dumps([
                {"task": "Lead analytics implementation", "assignee": "John", "deadline": None, "priority": "high", "status": "open"},
                {"task": "Prepare technical design document", "assignee": "John", "deadline": "2025-01-17", "priority": "high", "status": "open"},
                {"task": "Deliver dashboard mockups", "assignee": "Lisa", "deadline": "2025-01-22", "priority": "high", "status": "open"}
            ])},
            # Negative note
            {"role": "system", "content": "Do NOT set assignee to verbs like 'finalize' or 'allocate'. Do NOT copy entire paragraphs as tasks."},
            {"role": "user", "content": user},
        ]
        resp = self._chat(messages, tools=None, tool_choice=None, temperature=0.2, top_p=0.1, max_tokens=1200)
        content = resp.choices[0].message.content or "[]"
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []
        return data[: max_items]

    def _call_llm_for_decisions(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        transcript = args.get("transcript", "")
        language = args.get("language", "en")
        participants = args.get("participants", [])

        system = (
            "You extract clear decisions. Each decision is one sentence. Owner must be a person name in participants."
        )
        developer = f"Participants: {participants}. If owner cannot be determined, set null."
        user = f"""Transcript:
{transcript}

Return a JSON array of decisions: [{{"decision":str, "owner":str|null}}]
- decision: one sentence, <= 28 words, paraphrased (no verbatim copy)
- owner: person who made/confirmed the decision when explicit; else null
"""
        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": developer},
            {"role": "user", "content": user},
        ]
        resp = self._chat(messages, tools=None, tool_choice=None, temperature=0.2, top_p=0.1, max_tokens=900)
        content = resp.choices[0].message.content or "[]"
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []
        return data

    # ------------------------ Paraphrase helper ------------------------
    def paraphrase_bullets(self, bullets: List[str], language: str = "en") -> List[str]:
        if not bullets:
            return bullets
        system = (
            "You paraphrase bullets concisely. Keep <= 20 words per bullet. Do not copy phrases verbatim."
        )
        user = json.dumps({"bullets": bullets, "language": language})
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = self._chat(messages, tools=None, tool_choice=None, temperature=0.2, top_p=0.1, max_tokens=600)
        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
            if isinstance(data, dict) and isinstance(data.get("bullets"), list):
                return data.get("bullets")
        except Exception:
            pass
        return bullets


# Global client instance
azure_client = AzureOpenAIClient()
