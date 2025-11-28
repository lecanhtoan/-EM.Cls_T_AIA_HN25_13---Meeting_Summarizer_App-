# API Response Examples

## Endpoint: POST /api/meetings/upload

### Request
```bash
curl -X POST http://localhost:8000/api/meetings/upload \
  -F "file=@transcript.txt" \
  -F "title=Q4 Product Planning" \
  -F "language=en"
```

### Response (200 OK)
```json
{
  "meeting_id": 1,
  "title": "Q4 Product Planning",
  "language": "en",
  "created_at": "2024-01-15T10:30:00",
  "summary": {
    "bullets": [
      "Q4 planning session to finalize product roadmap",
      "Engineering has 120 story points available across 3 sprints",
      "Dashboard redesign (20 points), mobile app design (15 points), and analytics feature (30 points) are key priorities",
      "Remaining 55 points allocated for bug fixes and technical debt",
      "Analytics feature announcement planned for end of October"
    ],
    "style": "short",
    "max_bullets": 5
  },
  "action_items": [
    {
      "id": 1,
      "task": "Lead analytics implementation",
      "assignee": "John",
      "deadline": null,
      "priority": "high",
      "status": "open"
    },
    {
      "id": 2,
      "task": "Prepare technical design doc for analytics",
      "assignee": "John",
      "deadline": "2024-01-19",
      "priority": "high",
      "status": "open"
    },
    {
      "id": 3,
      "task": "Coordinate design with John on analytics",
      "assignee": "Lisa",
      "deadline": null,
      "priority": "high",
      "status": "open"
    },
    {
      "id": 4,
      "task": "Prepare design mockups for dashboard",
      "assignee": "Lisa",
      "deadline": "2024-01-17",
      "priority": "high",
      "status": "open"
    },
    {
      "id": 5,
      "task": "Prepare customer announcement for analytics feature",
      "assignee": "Mike",
      "deadline": "2024-01-31",
      "priority": "high",
      "status": "open"
    }
  ],
  "decisions": [
    {
      "id": 1,
      "decision": "Allocate 30 points to analytics feature, 20 to dashboard redesign, 15 to mobile design, 55 to technical debt",
      "owner": "Sarah",
      "decision_date": "2024-01-15T10:30:00"
    },
    {
      "id": 2,
      "decision": "Analytics feature to be announced to customers by end of October",
      "owner": "Mike",
      "decision_date": "2024-01-15T10:30:00"
    },
    {
      "id": 3,
      "decision": "Push mobile redesign from Q4 to Q1",
      "owner": "Sarah",
      "decision_date": "2024-01-15T10:30:00"
    }
  ]
}
```

---

## Endpoint: POST /api/meetings/text

### Request
```json
POST http://localhost:8000/api/meetings/text

{
  "title": "Team Standup",
  "language": "en",
  "transcript_text": "John: We completed the user authentication module. Sarah: Great! What's next? John: We need to integrate it with the database. Sarah: Can you have that done by tomorrow? John: Yes, I'll prioritize it. Sarah: Perfect. Also, we need to fix the login page styling. Lisa: I can take that. Sarah: Thanks Lisa. Let's reconvene tomorrow at 10 AM."
}
```

### Response (200 OK)
```json
{
  "meeting_id": 2,
  "title": "Team Standup",
  "language": "en",
  "created_at": "2024-01-15T11:00:00",
  "summary": {
    "bullets": [
      "User authentication module completed",
      "Next priority: integrate authentication with database",
      "Database integration to be completed by tomorrow",
      "Login page styling needs to be fixed",
      "Team to reconvene tomorrow at 10 AM"
    ],
    "style": "short",
    "max_bullets": 5
  },
  "action_items": [
    {
      "id": 6,
      "task": "Integrate authentication module with database",
      "assignee": "John",
      "deadline": "2024-01-16",
      "priority": "high",
      "status": "open"
    },
    {
      "id": 7,
      "task": "Fix login page styling",
      "assignee": "Lisa",
      "deadline": null,
      "priority": "medium",
      "status": "open"
    }
  ],
  "decisions": [
    {
      "id": 4,
      "decision": "Prioritize database integration for authentication module",
      "owner": "Sarah",
      "decision_date": "2024-01-15T11:00:00"
    }
  ]
}
```

---

## Endpoint: GET /api/meetings/{id}

### Request
```bash
curl http://localhost:8000/api/meetings/1
```

### Response (200 OK)
```json
{
  "id": 1,
  "title": "Q4 Product Planning",
  "language": "en",
  "source": "upload",
  "created_at": "2024-01-15T10:30:00",
  "summary": {
    "bullets": [
      "Q4 planning session to finalize product roadmap",
      "Engineering has 120 story points available across 3 sprints",
      "Dashboard redesign (20 points), mobile app design (15 points), and analytics feature (30 points) are key priorities",
      "Remaining 55 points allocated for bug fixes and technical debt",
      "Analytics feature announcement planned for end of October"
    ],
    "style": "short",
    "max_bullets": 5
  },
  "action_items": [
    {
      "id": 1,
      "task": "Lead analytics implementation",
      "assignee": "John",
      "deadline": null,
      "priority": "high",
      "status": "open"
    },
    {
      "id": 2,
      "task": "Prepare technical design doc for analytics",
      "assignee": "John",
      "deadline": "2024-01-19",
      "priority": "high",
      "status": "open"
    }
  ],
  "decisions": [
    {
      "id": 1,
      "decision": "Allocate 30 points to analytics feature, 20 to dashboard redesign, 15 to mobile design, 55 to technical debt",
      "owner": "Sarah",
      "decision_date": "2024-01-15T10:30:00"
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request - Invalid File Type
```json
{
  "detail": "Only .txt and .md files are supported"
}
```

### 400 Bad Request - Missing Fields
```json
{
  "detail": "Please select a file and enter a title"
}
```

### 404 Not Found - Meeting Not Found
```json
{
  "detail": "Meeting not found"
}
```

### 500 Internal Server Error - Azure OpenAI Error
```json
{
  "detail": "Failed to process transcript with Azure OpenAI"
}
```

---

## Database Schema - Sample Data

### users table
```sql
INSERT INTO users (id, email, full_name, created_at, updated_at)
VALUES (1, 'demo@example.com', 'Demo User', NOW(), NOW());
```

### meetings table
```sql
INSERT INTO meetings (id, user_id, title, meeting_date, source, language, created_at)
VALUES (
  1,
  1,
  'Q4 Product Planning',
  NOW(),
  'upload',
  'en',
  NOW()
);
```

### transcripts table
```sql
INSERT INTO transcripts (id, meeting_id, raw_text, clean_text, file_name, file_type, created_at)
VALUES (
  1,
  1,
  '[full transcript text]',
  '[cleaned transcript text]',
  'q4_planning.txt',
  'txt',
  NOW()
);
```

### summaries table
```sql
INSERT INTO summaries (id, meeting_id, style, max_bullets, bullets_json, model_name, created_at)
VALUES (
  1,
  1,
  'short',
  5,
  '["bullet1", "bullet2", "bullet3", "bullet4", "bullet5"]',
  'gpt-4',
  NOW()
);
```

### action_items table
```sql
INSERT INTO action_items (id, meeting_id, task, assignee, deadline, priority, status, created_at)
VALUES (
  1,
  1,
  'Lead analytics implementation',
  'John',
  NULL,
  'high',
  'open',
  NOW()
);
```

### decisions table
```sql
INSERT INTO decisions (id, meeting_id, decision, owner, decision_date, created_at)
VALUES (
  1,
  1,
  'Allocate 30 points to analytics feature',
  'Sarah',
  NOW(),
  NOW()
);
```

### tool_runs table
```sql
INSERT INTO tool_runs (id, meeting_id, tool_name, input_json, output_json, model_name, latency_ms, created_at)
VALUES (
  1,
  1,
  'extract_summary',
  '{"transcript": "[...]", "language": "en", "max_bullets": 5, "style": "short"}',
  '{"bullets": [...], "style": "short", "max_bullets": 5}',
  'gpt-4',
  1250,
  NOW()
);
```


