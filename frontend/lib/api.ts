/**
 * Card Studio Backend API Client.
 * Connects the Next.js frontend to the FastAPI backend running on port 8000.
 */

import {
  BriefResponse,
  DataSummary,
  DesignSpec,
  DraftsResponse,
  EventBrief,
  Person,
  RenderBatchRequest,
  RenderPreviewResponse,
} from "../types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        if (typeof errJson.detail === "string") {
          errorDetail = errJson.detail;
        } else if (Array.isArray(errJson.detail)) {
          errorDetail = errJson.detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
        } else {
          errorDetail = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(res.status, errorDetail);
  }
  return res.json() as Promise<T>;
}

export async function checkBackendHealth(): Promise<{ status: string; version?: string }> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: "GET" });
    return await handleResponse<{ status: string; version?: string }>(res);
  } catch (err: any) {
    throw new ApiError(0, err.message || "Failed to reach backend server");
  }
}

export async function submitBrief(text: string): Promise<BriefResponse> {
  const res = await fetch(`${API_BASE}/brief`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return handleResponse<BriefResponse>(res);
}

export async function uploadAttendeeCsv(file: File): Promise<DataSummary> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/data/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<DataSummary>(res);
}

export async function generateDrafts(
  brief: EventBrief,
  count = 3
): Promise<DraftsResponse> {
  const eventPayload = {
    event_name: brief.event_name || "Event Name",
    tagline: brief.tagline || "",
    venue: brief.venue || "",
    dates: brief.dates || "",
  };

  const res = await fetch(`${API_BASE}/drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      brief,
      event: eventPayload,
      count,
    }),
  });
  return handleResponse<DraftsResponse>(res);
}

export async function renderPreview(
  spec: DesignSpec,
  person: Person,
  debugGuides = false
): Promise<RenderPreviewResponse> {
  const res = await fetch(`${API_BASE}/render/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      spec,
      person,
      debug_guides: debugGuides,
    }),
  });
  return handleResponse<RenderPreviewResponse>(res);
}

export interface BatchDownloadResult {
  blob: Blob;
  filename: string;
  totalCount: number;
  exportedCount: number;
  failedCount: number;
  qaIssueCount: number;
}

export async function renderBatch(
  request: RenderBatchRequest
): Promise<BatchDownloadResult> {
  const res = await fetch(`${API_BASE}/render/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
    } catch {
      // not JSON
    }
    throw new ApiError(res.status, errorDetail);
  }

  // Extract metadata headers returned by backend
  const totalCount = parseInt(res.headers.get("X-Total-Count") || "0", 10);
  const exportedCount = parseInt(res.headers.get("X-Exported-Count") || "0", 10);
  const failedCount = parseInt(res.headers.get("X-Failed-Count") || "0", 10);
  const qaIssueCount = parseInt(res.headers.get("X-QA-Issue-Count") || "0", 10);

  // Filename from Content-Disposition header
  const disposition = res.headers.get("Content-Disposition") || "";
  let filename = request.collate_pdf ? "cards.pdf" : "cards.zip";
  const match = disposition.match(/filename="?([^"]+)"?/);
  if (match && match[1]) {
    filename = match[1];
  }

  const blob = await res.blob();
  return {
    blob,
    filename,
    totalCount,
    exportedCount,
    failedCount,
    qaIssueCount,
  };
}

export async function patchSpec(
  spec: DesignSpec,
  ops: Array<{ op: string; path: string; value?: any }>
): Promise<DesignSpec> {
  const res = await fetch(`${API_BASE}/spec/patch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec, ops }),
  });
  const data = await handleResponse<{ spec: DesignSpec }>(res);
  return data.spec;
}

export async function getLayoutTemplates(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/templates/layouts`, { method: "GET" });
  return handleResponse<string[]>(res);
}

export async function getThemeTemplates(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/templates/themes`, { method: "GET" });
  return handleResponse<string[]>(res);
}

export async function getRoles(): Promise<Array<{ id: string; name: string; badge_text: string }>> {
  const res = await fetch(`${API_BASE}/roles`, { method: "GET" });
  return handleResponse<Array<{ id: string; name: string; badge_text: string }>>(res);
}

export interface PrintSheetDownloadResult {
  blob: Blob;
  filename: string;
  totalPages: number;
  totalCards: number;
}

export async function renderPrintSheet(
  spec: DesignSpec,
  people: Person[],
  page: "A4" | "A3" = "A4",
  cropMarks: boolean = true
): Promise<PrintSheetDownloadResult> {
  const res = await fetch(`${API_BASE}/render/print-sheet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec, people, page, crop_marks: cropMarks }),
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
    } catch {
      // not JSON
    }
    throw new ApiError(res.status, errorDetail);
  }

  const totalPages = parseInt(res.headers.get("X-Total-Pages") || "1", 10);
  const totalCards = parseInt(res.headers.get("X-Total-Cards") || String(people.length), 10);
  const disposition = res.headers.get("Content-Disposition") || "";
  let filename = `print_sheet_${page}.pdf`;
  const match = disposition.match(/filename="?([^"]+)"?/);
  if (match && match[1]) {
    filename = match[1];
  }

  const blob = await res.blob();
  return {
    blob,
    filename,
    totalPages,
    totalCards,
  };
}

export interface RefineResponse {
  spec: DesignSpec;
  ops: Array<{ op: string; path: string; value?: any }>;
  summary: string;
}

export async function refineSpec(
  spec: DesignSpec,
  prompt: string
): Promise<RefineResponse> {
  const res = await fetch(`${API_BASE}/spec/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec, prompt }),
  });
  return handleResponse<RefineResponse>(res);
}
