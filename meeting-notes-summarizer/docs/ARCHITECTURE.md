# Architecture & Design Decisions (Updated)

## Overview

The Meeting Notes Summarizer is a full-stack web application that processes meeting transcripts using Azure OpenAI's function calling capabilities and persists structured outputs to PostgreSQL. This document reflects the latest improvements: redesigned function-calling schemas and prompts, preprocessing pipeline with participants extraction, validation/post-processing, UI updates (card grid Action Items; Meetings list), and new backend endpoints.

## Architecture Diagram (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  TranscriptInput (File Upload / Text Paste)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Right Panel                                             │  │
│  │  ├─ Empty State → MeetingsList (GET /api/meetings)       │  │
│  │  │   └─ Click item → GET /api/meetings/{id}              │  │
│  │  ├─ Meeting Details                                      │  │
│  │  │   ├─ Back button → return to MeetingsList             │  │
│  │  │   ├─ SummaryView                                      │  │
│  │  │   ├─ ActionItemsView (card grid 3/row)                │  │
│  │  │   │   └─ Inline edit → PUT /api/meetings/{id}         │  │
│  │  │   └─ DecisionsView                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Routes (app/routes/meetings.py)                    │  │
│  │  ├─ POST /api/meetings/upload                           │  │
│  │  ├─ POST /api/meetings/text                             │  │
│  │  ├─ GET  /api/meetings                                  │  │
│  │  ├─ GET  /api/meetings/{id}                             │  │
│  │  └─ PUT  /api/meetings/{id} (update action items)       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Services (app/services/summarization.py)               │  │
│  │  └─ SummarizationService                                │  │
│  │     ├─ process_transcript()                             │  │
│  │     │   1) Preprocess (segment speakers, participants)  │  │
│  │     │   2) Call Azure tools (summary/actions/decisions) │  │
│  │     │   3) Validate & post-process (names/dates/format) │  │
│  │     │   4) Paraphrase bullets if verbatim               │  │
│  │     │   5) Persist + quality_report tool_run            │  │
│  │     └─ get_meeting_details()                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Azure OpenAI Client (app/azure_client.py)              │  │
│  │  └─ AzureOpenAIClient                                   │  │
│  │     ├─ call_functions() (tool_choice=required)          │  │
│  │     ├─ _call_llm_for_summary()                          │  │
│  │     ├─ _call_llm_for_action_items()                     │  │
│  │     ├─ _call_llm_for_decisions()                        │  │
│  │     └─ paraphrase_bullets()                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Utils                                                  │  │
│  │  ├─ app/utils/preprocess.py (segment, participants)     │  │
│  │  └─ app/utils/validation.py (dates, rules, quality)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ORM Models (app/models.py)                             │  │
│  │  ├─ User  ├ Meeting  ├ Transcript  ├ Summary            │  │
│  │  ├─ ActionItem  ├ Decision  └ ToolRun                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ SQL
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                         │
│  ├─ users  ├ meetings  ├ transcripts  ├ summaries               │
│  ├─ action_items  ├ decisions  └ tool_runs                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓ API
┌─────────────────────────────────────────────────────────────────┐
│                Azure OpenAI (Function Calling)                   │
│  ├─ extract_summary (constraints: no_verbatim, bullet_max_words) │
│  ├─ extract_action_items (participants & rules enforced)         │
│  └─ extract_decisions (owner & one-sentence constraints)         │
└─────────────────────────────────────────────────────────────────┘
```

## Backend API (Updated)

- POST /api/meetings/upload — Upload transcript file (.txt/.md) and process
- POST /api/meetings/text — Process raw transcript text
- GET  /api/meetings — List all processed meetings (id, title, language, source, created_at)
- GET  /api/meetings/{id} — Retrieve meeting details (summary, actions, decisions)
- PUT  /api/meetings/{id} — Update multiple action items (task, assignee, deadline, priority, status)

## Function Calling Redesign

- Tools are redefined with stronger parameters:
  - extract_summary: constraints.no_verbatim, constraints.bullet_max_words, constraints.must_cover
  - extract_action_items: participants + rules (assignee_must_be_in_participants, task_must_be_one_sentence, normalize_deadline_to_iso, max_items)
  - extract_decisions: participants + rules (decision_must_be_one_sentence, owner_must_be_person_name)
- Prompts include few-shot and negative examples to avoid verbatim copying and to enforce structure.
- Model config:
  - tool_choice="required", temperature=0.2, top_p=0.1, max_tokens≈900–1500, retries with backoff

## Preprocessing & Validation Pipeline

1) Preprocessing (app/utils/preprocess.py)
- segment_by_speaker: split transcript by speaker lines (e.g., "Sarah:"), accumulate content
- extract_participants: collect unique speakers
- normalize_transcript_text: rebuild clean text for LLM

2) LLM Extraction (app/azure_client.py)
- call_functions() orchestrates function calling loops
- Specialized sub-prompts per extraction type

3) Post-processing (app/utils/validation.py; app/services/summarization.py)
- Action items: enforce single-sentence tasks (trim if too long), assignee ∈ participants (else null), normalize deadline via dateparser (YYYY-MM-DD), keep priority/status
- Decisions: ensure one sentence; owner ∈ participants (else null)
- Summary: detect verbatim bullets (token overlap heuristic); if any, paraphrase via paraphrase_bullets()

4) Persistence & Audit
- Persist summary/action_items/decisions as before
- Add an extra ToolRun row named quality_report with metrics:
  - summary_verbatim_bullets, actions_no_assignee, actions_long_task, decisions_no_owner, participants

## Frontend (Updated)

- Empty state right panel now shows MeetingsList (GET /api/meetings). Clicking a meeting loads its details (GET /api/meetings/{id}).
- Meeting details screen includes a Back button to return to MeetingsList.
- ActionItemsView is a responsive card grid (1/row small, 2/row sm, 3/row lg):
  - Each card shows Task (textarea), Assignee, Deadline (date), Priority, Status.
  - Supports inline editing and bulk save via PUT /api/meetings/{id}.

## Data Flow (Updated)

```
1. User Input
   ├─ File Upload → Extract text
   └─ Text Paste → Use text directly

2. Preprocessing
   ├─ Segment speakers, extract participants
   └─ Normalize transcript text

3. Azure OpenAI Processing (strict tools)
   ├─ extract_summary (no_verbatim, max words, must-cover topics)
   ├─ extract_action_items (participants/rules)
   └─ extract_decisions (owner/rules)

4. Validation & Post-processing
   ├─ Summary: detect verbatim bullets → paraphrase if needed
   ├─ Action Items: one sentence, assignee in participants, normalize deadline
   └─ Decisions: one sentence, owner in participants

5. Persistence & Audit
   ├─ Save Summary, ActionItem, Decision
   └─ Save ToolRun + Quality Report

6. UI
   ├─ Empty state: MeetingsList
   ├─ Details: Summary / Action Items (card grid) / Decisions + Back button
```

## Error Handling & Quality Gates

- Backend validates action items and decisions; normalizes deadlines; trims oversize texts.
- Summary paraphrasing reduces verbatim copying.
- Quality report saved to tool_runs for monitoring.

## Performance & Security

- DB indices and connection pooling unchanged.
- Model calls use low temperature, minimal tokens, and retries.
- CORS configured via FRONTEND_URL; ensure frontend port matches.

## Future Enhancements

- Name/Date NER with spaCy (optional) to reinforce parsing.
- Advanced evaluation suite comparing outputs with expected templates.
- Item-level confidence scores and review workflow.
