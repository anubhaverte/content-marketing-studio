# Card Studio Frontend (Phase 6)

Modern SaaS-style web interface for the ID Card Studio event badge engine.

Built with **Next.js (App Router)**, **React**, **TypeScript**, and **Tailwind CSS**.

---

## 1. Prerequisites

- **Node.js**: v18.17+ or v20+ (LTS recommended)
- **FastAPI Backend**: Running at `http://localhost:8000`

If Node.js is not yet installed on your machine, see Section 4 below for installation instructions.

---

## 2. Quickstart

In a terminal window (Terminal B):

```powershell
# Navigate to the frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Then open your browser to **[http://localhost:3000](http://localhost:3000)**.

---

## 3. End-to-End Workflow

The application guides the event organizer through 5 interconnected steps:

1. **Step 1: Event Brief (`POST /brief`)**:
   - Natural language description extraction.
   - Extracts event name, dates, venue, tagline, and roles.
   - Displays clarification prompts for missing information.
   - Indicates whether Gemini AI extraction or deterministic offline fallback was used.

2. **Step 2: Attendee Data (`POST /data/upload`)**:
   - Multipart CSV roster upload.
   - Authoritative backend schema validation (`people_loaded`, column mappings, issue counts, warnings).
   - In-browser attendee preview table with role tags and skipped row reporting.

3. **Step 3: Design Drafts (`POST /drafts`)**:
   - Queries candidate `DesignSpec` templates from the backend catalog.
   - Color swatch previews and layout metadata.
   - Selection of candidate card design.

4. **Step 4: Badge Preview (`POST /render/preview`)**:
   - Live deterministic SVG badge rendering directly from the backend pipeline.
   - Multi-attendee navigation (`◀ Prev` / `Next ▶`).
   - Print guides overlay (`debug_guides: true`) displaying bleed (red), trim (green), and safe margin (blue).
   - Live automated QA diagnostic panel (contrast ratio, photo resolution, OpenCV blur score warnings, missing logo fallbacks).

5. **Step 5: Batch Export (`POST /render/batch`)**:
   - Print format selection: PDF (vector print), PNG (300 DPI raster), SVG (source markup).
   - Packaging options:
     - Multi-page collated PDF (single document with 1 page per attendee).
     - ZIP archive (individual badge files plus `report.json` QA audit report).
   - Direct native browser file download with backend export statistics (`X-Total-Count`, `X-Exported-Count`, `X-QA-Issue-Count`).

---

## 4. Node.js Installation Guide (Windows)

If `node` or `npm` are not recognized in PowerShell:

### Option A: Using Windows Package Manager (winget) - Recommended
Run in PowerShell:
```powershell
winget install OpenJS.NodeJS.LTS
```
After installation completes, restart PowerShell to refresh `$env:PATH`.

### Option B: Official Installer
1. Download the LTS Windows Installer (`.msi`) from [https://nodejs.org/en/download/](https://nodejs.org/en/download/).
2. Run the installer and accept standard defaults.
3. Restart PowerShell and verify with:
   ```powershell
   node -v
   npm -v
   ```

---

## 5. Configuration

Default backend URL is `http://localhost:8000`. To customize:

Create `.env.local` in `frontend/`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
