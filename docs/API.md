# DocMind AI - API Documentation

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.docmindai.com` (to be deployed)

## Authentication

All endpoints (except `/auth/*` registration/login) require JWT token in header:

```
Authorization: Bearer <your_token>
```

## Endpoints

### Authentication

#### POST `/auth/register`
Register new user
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "secure_password"
}
```
Response: `{ "access_token": "jwt...", "token_type": "bearer", "expires_in": 1800 }`

#### POST `/auth/login`
Login user
```json
{
  "email": "user@example.com",
  "password": "password"
}
```
Response: `{ "access_token": "jwt...", "token_type": "bearer" }`

#### POST `/auth/verify-email`
Verify email with code
```json
{
  "email": "user@example.com",
  "code": "verification_code"
}
```

#### POST `/auth/forgot-password`
Request password reset
```
?email=user@example.com
```

#### POST `/auth/reset-password`
Reset password
```json
{
  "email": "user@example.com",
  "token": "reset_token",
  "new_password": "new_password"
}
```

---

### Documents

#### POST `/documents/upload`
Upload document (multipart/form-data)
- File: document file
- workspace_id: workspace ID
- Returns: `{ "document_id": 1, "status": "processing" }`

#### GET `/documents/`
List documents in workspace
- Query params: `workspace_id`, `skip` (default 0), `limit` (default 20)

#### GET `/documents/{document_id}`
Get document details

#### DELETE `/documents/{document_id}`
Delete document

#### GET `/documents/{document_id}/summary`
Get AI-generated summary of document

---

### Chat

#### POST `/chat/sessions`
Create chat session
- Query params: `document_id` (optional), `workspace_id`, `user_id`
- Returns: `{ "session_id": 1, "document_id": null, "created_at": "..." }`

#### POST `/chat/ask`
Ask question (non-streaming)
- Query params: `session_id`, `query`, `document_ids[]` (optional)
- Returns: 
```json
{
  "message_id": 1,
  "content": "Answer text...",
  "sources": [
    {
      "document_id": 1,
      "page": 4,
      "chunk_id": 10,
      "score": 0.95
    }
  ]
}
```

#### WS `/chat/ws/{session_id}`
WebSocket for streaming responses
- Send: `{ "query": "...", "document_ids": [1, 2] }`
- Receive: `{ "type": "stream", "content": "chunk..." }`
- Final: `{ "type": "sources", "sources": [...] }`

#### GET `/chat/sessions/{session_id}/messages`
Get chat history
- Query params: `skip` (default 0), `limit` (default 50)

#### POST `/chat/regenerate`
Regenerate previous response
- Query params: `message_id`

#### GET `/chat/sessions/{session_id}/export`
Export chat as PDF/Markdown/DOCX
- Query params: `format` (md|pdf|docx)

---

### Search

#### GET `/search/`
Search across documents
- Query params:
  - `query`: search term (required)
  - `workspace_id`: workspace (required)
  - `document_ids[]`: filter by documents (optional)
  - `search_type`: semantic|keyword|hybrid (default: hybrid)
  - `filter_file_type`: pdf|docx|etc (optional)
  - `filter_date_from`: ISO date (optional)
  - `filter_date_to`: ISO date (optional)
  - `skip`: pagination (default 0)
  - `limit`: results per page (default 20)

- Returns:
```json
{
  "results": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "page": 4,
      "content": "text snippet...",
      "score": 0.92,
      "highlight": "...matched **text**..."
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 20
}
```

#### GET `/search/suggestions`
Get search suggestions
- Query params: `query`, `workspace_id`

#### GET `/search/filters`
Get available filters
- Query params: `workspace_id`

---

### Workspace

#### POST `/workspace/create`
Create workspace
- Query params: `name`, `is_personal` (default false)

#### GET `/workspace/{workspace_id}`
Get workspace details

#### POST `/workspace/{workspace_id}/members/invite`
Invite member
- Query params: `email`, `role` (member|manager|owner)

#### GET `/workspace/{workspace_id}/members`
List workspace members

#### DELETE `/workspace/{workspace_id}/members/{user_id}`
Remove member

#### GET `/workspace/`
List user's workspaces
- Query params: `user_id`

---

### Analytics

#### GET `/analytics/workspace/{workspace_id}`
Get workspace analytics
- Returns: total_documents, total_chunks, questions_asked

#### GET `/analytics/usage/{workspace_id}`
Get usage over time
- Query params: `days` (default 30)

#### GET `/analytics/top-documents/{workspace_id}`
Get most accessed documents
- Query params: `limit` (default 10)

#### GET `/analytics/document/{document_id}/stats`
Get stats for document

---

## Error Responses

All errors return JSON with `detail` field:

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Server Error

---

## Rate Limiting

- 100 requests per minute per user
- Search: 30 requests per minute
- Chat: 60 requests per minute

---

## Pagination

For list endpoints, use `skip` and `limit` for pagination:
- `skip`: number of items to skip (default 0)
- `limit`: max items to return (default 20, max 100)

---

## File Upload

Maximum file size: 50MB
Supported formats: PDF, DOCX, PPTX, TXT, CSV, MD

---

## WebSocket

Connect to `/chat/ws/{session_id}` with valid JWT token:

```javascript
const ws = new WebSocket(
  `ws://localhost:8000/chat/ws/1?token=${token}`
)

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'stream') {
    // Streaming response
  } else if (data.type === 'sources') {
    // Sources list
  }
}
```

---

## Examples

### Upload and Chat

1. Register/Login to get token
2. Create chat session: POST `/chat/sessions`
3. Upload document: POST `/documents/upload`
4. Ask question: POST `/chat/ask`

### Search Workflow

1. GET `/search/filters` to see available filters
2. GET `/search/` with query and filters
3. GET `/search/suggestions` for autocomplete

### Team Collaboration

1. Create workspace: POST `/workspace/create`
2. Invite members: POST `/workspace/{id}/members/invite`
3. Share documents in workspace
4. View analytics: GET `/analytics/workspace/{id}`
