/**
 * Type definitions matching backend FastAPI schemas.
 * Single source of truth: backend/app/api/models.py and backend/app/api/render_models.py
 */

export interface EventBrief {
  design_type: string;
  event_name: string | null;
  tagline: string | null;
  dates: string | null;
  venue: string | null;
  roles: string[] | null;
  counts: Record<string, number> | null;
  fields_to_show: string[] | null;
  card_size: string | null;
  orientation: string | null;
  style_hint: string | null;
  lanyard_hole: boolean | null;
}

export interface BriefQuestion {
  field: string;
  text: string;
  kind: "text" | "choice" | "boolean" | "number";
  options: string[] | null;
  default: any | null;
  skippable: boolean;
}

export interface BriefResponse {
  brief: EventBrief;
  missing: string[];
  questions: BriefQuestion[];
  mock?: boolean;
}

export interface DataSummary {
  people_loaded: number;
  column_mapping: Record<string, string>;
  issues: Record<string, number>;
  warnings: string[];
  mock?: boolean;
}

export interface Person {
  name: string;
  role?: string;
  id?: string;
  team?: string;
  email?: string;
  photo?: string;
  qr_url?: string;
  extra?: Record<string, any>;
}

export interface ThemeColors {
  primary: string;
  secondary: string;
  background: string;
  accent: string;
  text: string;
  text_on_primary?: string;
}

export interface ThemeFonts {
  heading: string;
  body: string;
}

export interface Theme {
  name: string;
  colors: ThemeColors;
  fonts: ThemeFonts;
  role_colors: Record<string, string>;
}

export interface PageSpec {
  width_mm: number;
  height_mm: number;
  bleed_mm: number;
  safe_mm: number;
}

export interface EventInfo {
  event_name: string;
  tagline?: string;
  dates?: string;
  venue?: string;
}

export interface BrandKit {
  logos?: Record<string, string>;
  colors?: Record<string, string>;
  fonts?: Record<string, string>;
}

export interface LayoutElement {
  id: string;
  type: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  field?: string;
  font_role?: string;
  color_role?: string;
  align?: string;
  [key: string]: any;
}

export interface DesignSpec {
  schema_version: string;
  layout_name: string;
  theme_name: string;
  page: PageSpec;
  event: EventInfo;
  brand: BrandKit;
  theme: Theme;
  elements: LayoutElement[];
}

export interface DraftsResponse {
  drafts: DesignSpec[];
  mock?: boolean;
}

export interface QAIssue {
  check: string;
  severity: "error" | "warning" | "info";
  message: string;
  person_id?: string;
}

export interface RenderPreviewResponse {
  svg: string;
  qa_issues: QAIssue[];
}

export interface BatchExportSettings {
  format: "pdf" | "png" | "svg";
  dpi: number;
  orientation: "portrait" | "landscape";
  bleed: boolean;
}

export interface RenderBatchRequest {
  spec: DesignSpec;
  people: Person[];
  settings?: BatchExportSettings;
  format?: "pdf" | "png" | "svg" | "zip";
  collate_pdf?: boolean;
  skipped_rows?: Record<string, any>[];
  return_json?: boolean;
}

export interface RenderBatchResponse {
  totals: {
    people: number;
    exported: number;
    failed: number;
    skipped_rows: number;
    qa_issues: number;
  };
  people: { id: string; status: string }[];
  skipped_rows: Record<string, any>[];
  settings: Record<string, any>;
  archive_base64: string;
  filename: string;
  media_type: string;
}
