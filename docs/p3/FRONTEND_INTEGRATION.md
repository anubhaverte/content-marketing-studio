# Person 3 Frontend Integration & Architecture Specification

## 1. Overview
This document specifies the integration architecture for **Phase 6: Frontend Development Readiness and Integration**.

Owner: **Person 3** (`frontend/`, `docs/p3/`).

---

## 2. API Contract Endpoints

| Endpoint | Method | Payload / Request | Response Schema | Frontend Usage |
|---|---|---|---|---|
| `/health` | `GET` | None | `{"status": "ok", "version": "0.0.1"}` | Liveness check & navbar status badge |
| `/brief` | `POST` | `{"text": string}` | `BriefResponse` (`brief`, `missing`, `questions`, `mock`) | Screen 1: Event description extraction |
| `/data/upload` | `POST` | `multipart/form-data` with `file=@attendees.csv` | `DataSummary` (`people_loaded`, `column_mapping`, `issues`, `warnings`, `mock`) | Screen 2: Roster ingestion & validation |
| `/drafts` | `POST` | `{"brief": {...}, "event": {...}, "count": 3}` | `DraftsResponse` (`drafts`: `DesignSpec[]`, `mock`) | Screen 3: Card design candidate gallery |
| `/render/preview` | `POST` | `{"spec": DesignSpec, "person": Person, "debug_guides": boolean}` | `RenderPreviewResponse` (`svg`: string, `qa_issues`: `QAIssue[]`) | Screen 4: Real-time SVG badge rendering & QA warnings |
| `/render/batch` | `POST` | `RenderBatchRequest` | Binary Stream (`application/zip` or `application/pdf`) | Screen 5: Direct print export download with metadata headers |

---

## 3. Data Flow & Integration Patterns

### 3.1 Brief Extraction (`POST /brief`)
- Sends natural language string describing event parameters.
- If Gemini API is configured, receives AI-extracted structure.
- If offline, backend gracefully falls back to deterministic token extraction and returns `mock: true`.
- Missing fields prompt interactive question forms for the organizer.

### 3.2 CSV Attendee Roster (`POST /data/upload`)
- Sends the actual uploaded CSV via multipart form.
- Backend parses headers with UTF-8 / UTF-8 BOM safety, validates against role schemas, and calculates issue tallies.
- The browser client parses the CSV locally to populate attendee preview records and supply attendee models to `/render/preview` and `/render/batch`.

### 3.3 Candidate Drafts (`POST /drafts`)
- Requests available design combinations from the backend catalog.
- Each candidate contains full layout, page geometry (60 × 92 mm, 3mm bleed), theme tokens (`primary`, `secondary`, `accent`, `text`, `background`), and role color mappings.

### 3.4 Card Rendering & Photo Processing (`POST /render/preview`)
- Renders deterministic vector SVG.
- Backend pipeline applies OpenCV photo processing (face-centered cropping, resolution verification, blur analysis).
- Frontend visualizes live QA feedback including low resolution, high blur, contrast ratio, and placeholder logo notices.
- Print guides toggle displays bleed (red), trim (green), and safe (blue) boundaries.

### 3.5 Batch Print Export (`POST /render/batch`)
- Accepts all parsed attendees and the chosen `DesignSpec`.
- Supports collated multi-page PDF (`collate_pdf: true`) or packaged ZIP archive (`collate_pdf: false`).
- Handles response as a binary `Blob`, creating an instant native file download.
- Reads `X-Total-Count`, `X-Exported-Count`, `X-Failed-Count`, and `X-QA-Issue-Count` headers for immediate user confirmation.

---

## 4. Local Execution Protocol

### Terminal A (Backend)
```powershell
cd backend
..\.venv\Scripts\uvicorn.exe app.main:app --port 8000 --reload
```

### Terminal B (Frontend)
```powershell
cd frontend
npm install
npm run dev
```

### Browser
Open `http://localhost:3000`.
