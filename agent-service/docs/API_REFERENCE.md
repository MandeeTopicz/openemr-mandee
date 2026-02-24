# CareTopicz Agent Service — API Reference

Base URL: `http://localhost:8000` (or your deployed URL).

## Endpoints

### GET /health

Health check for load balancers and monitoring.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "CareTopicz Agent",
  "version": "0.1.0"
}
```

---

### POST /chat

Send a user message and receive an agent response.

**Request body:**

| Field       | Type   | Required | Description                    |
|------------|--------|----------|--------------------------------|
| message    | string | yes      | User message text              |
| session_id | string | no       | Session ID for continuity      |
| patient_id | string | no       | Optional patient context ID    |

**Response:** `200 OK`

```json
{
  "response": "Agent reply text...",
  "session_id": "optional-session-id",
  "run_id": "uuid-for-feedback-linking"
}
```

**Errors:** `500` (agent error), `503` (e.g. API key not set).

---

### POST /chat/feedback

Submit user feedback (thumbs up/down) linked to a trace. Requires `run_id` from the chat response.

**Request body:**

| Field   | Type   | Required | Description                          |
|--------|--------|----------|--------------------------------------|
| run_id | string | yes      | LangSmith run ID from chat response  |
| score  | number | yes      | 1 = thumbs up, 0 = thumbs down       |
| comment| string | no       | Optional comment                     |

**Response:** `200 OK` — `{"status": "ok", "message": "Feedback recorded"}`

**Errors:** `400` if `run_id` invalid or LangSmith unreachable.

---

### Interactive docs

- **Swagger UI:** `GET /docs`
- **ReDoc:** `GET /redoc`
