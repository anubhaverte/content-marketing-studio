"use client";

import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { DesignSpec, Person, ThemeColors, Theme, LayoutElement } from "../types";
import { renderPreview, patchSpec, refineSpec, uploadAsset } from "../lib/api";
import { sanitizeSpecForBackend } from "../lib/specSanitizer";

interface VisualSpecEditorProps {
  initialSpec: DesignSpec;
  attendees?: Person[];
  onApplySpec?: (updatedSpec: DesignSpec) => void;
  onChangeSpec?: (updatedSpec: DesignSpec) => void;
  onClose?: () => void;
}

// Default personas representing each role
const DEFAULT_PERSONAS: Person[] = [
  {
    name: "Aarav Sharma",
    role: "participant",
    id: "ACM-P-104",
    team: "Neural Knights",
    email: "aarav.sharma@svnit.ac.in",
    photo: "photos/portrait_01.jpg",
  },
  {
    name: "Priya Patel",
    role: "organizer",
    id: "ACM-ORG-002",
    team: "Core Committee",
    email: "priya.p@svnit.ac.in",
    photo: "photos/portrait_02.jpg",
  },
  {
    name: "Dr. Rajesh Mehta",
    role: "mentor",
    id: "ACM-MNT-015",
    team: "Faculty Advisor",
    email: "rmehta@ced.svnit.ac.in",
    photo: "photos/portrait_03.jpg",
  },
  {
    name: "Sneha Rao",
    role: "volunteer",
    id: "ACM-VOL-042",
    team: "Logistics Crew",
    email: "sneha.rao@svnit.ac.in",
    photo: "photos/portrait_04.jpg",
  },
];

// Built-in theme presets
export const THEME_PRESETS: Record<string, { label: string; colors: ThemeColors; role_colors: Record<string, string> }> = {
  clean_light: {
    label: "Clean Light",
    colors: {
      background: "#FFFFFF",
      primary: "#1F6FEB",
      secondary: "#EAF1FD",
      accent: "#38BDF8",
      text: "#0B1220",
    },
    role_colors: {
      participant: "#1F6FEB",
      organizer: "#D9480F",
      mentor: "#2F9E44",
      volunteer: "#8B5CF6",
    },
  },
  dark_tech: {
    label: "Dark Tech",
    colors: {
      background: "#0B1220",
      primary: "#1E293B",
      secondary: "#312E81",
      accent: "#38BDF8",
      text: "#F8FAFC",
    },
    role_colors: {
      participant: "#38BDF8",
      organizer: "#F97316",
      mentor: "#4ADE80",
      volunteer: "#A78BFA",
    },
  },
  bold_event: {
    label: "Bold Event",
    colors: {
      background: "#FFF7ED",
      primary: "#FFE4E6",
      secondary: "#E0E7FF",
      accent: "#E11D48",
      text: "#1C1917",
    },
    role_colors: {
      participant: "#E11D48",
      organizer: "#EA580C",
      mentor: "#4F46E5",
      volunteer: "#7C3AED",
    },
  },
};

// Built-in layout presets
export const LAYOUT_PRESETS: Record<string, { label: string; icon: string; description: string; elements: LayoutElement[] }> = {
  classic: {
    label: "Classic Badge",
    icon: "🏛️",
    description: "Dual institutional crests atop a header band, centered portrait & role pill",
    elements: [
      { id: "bg", type: "rect", x: 0, y: 0, w: 60, h: 92, fill: "background" },
      { id: "banner", type: "rect", x: 0, y: 0, w: 60, h: 24, fill: "primary" },
      { id: "logo_acm", type: "logo", src: "acm_nitsurat", x: 8, y: 4.5, w: 15, h: 15, fit: "contain" },
      { id: "logo_svnit", type: "logo", src: "svnit", x: 37, y: 4.5, w: 15, h: 15, fit: "contain" },
      { id: "photo", type: "photo", field: "photo", x: 16, y: 28, w: 28, h: 34, shape: "rounded", radius: 3 },
      { id: "line", type: "line", x1: 10, y1: 64.5, x2: 50, y2: 64.5, stroke: "accent", stroke_width: 0.4, dash: [2, 1.5] },
      { id: "name", type: "text", field: "name", x: 7, y: 66, w: 46, font: "heading", color: "text", max_font: 14, min_font: 8, max_lines: 2, align: "center", bold: true },
      { id: "role", type: "role_badge", field: "role", x: 15, y: 78, w: 30, h: 6 },
    ],
  },
  minimal: {
    label: "Minimal Tech",
    icon: "⚡",
    description: "Modern asymmetric layout, hairline divider, circle avatar & left-aligned typography",
    elements: [
      { id: "bg", type: "rect", x: 0, y: 0, w: 60, h: 92, fill: "background" },
      { id: "logo_acm", type: "logo", src: "acm_nitsurat", x: 7, y: 5.5, w: 10, h: 10, fit: "contain" },
      { id: "logo_svnit", type: "logo", src: "svnit", x: 43, y: 5.5, w: 10, h: 10, fit: "contain" },
      { id: "line", type: "line", x1: 7, y1: 18, x2: 53, y2: 18, stroke: "secondary", stroke_width: 0.3 },
      { id: "photo", type: "photo", field: "photo", x: 7, y: 22, w: 20, h: 20, shape: "circle" },
      { id: "role", type: "role_badge", field: "role", x: 30, y: 28, w: 23, h: 6 },
      { id: "name", type: "text", field: "name", x: 7, y: 46, w: 46, font: "heading", color: "text", max_font: 16, min_font: 10, max_lines: 2, align: "left", bold: true },
      { id: "team", type: "text", field: "team", x: 7, y: 60, w: 46, font: "body", color: "accent", max_font: 9, min_font: 7, max_lines: 1, align: "left" },
      { id: "id", type: "text", field: "id", x: 7, y: 66, w: 46, font: "body", color: "text", max_font: 8, min_font: 6, max_lines: 1, align: "left" },
      { id: "qr", type: "qr", field: "qr_url", x: 7, y: 72, w: 14, h: 14 },
    ],
  },
  split: {
    label: "Split Column",
    icon: "🌓",
    description: "Two-tone vertical sidebar with prominent ACM badge & dedicated SVNIT metadata column",
    elements: [
      { id: "bg", type: "rect", x: 0, y: 0, w: 60, h: 92, fill: "background" },
      { id: "pillar", type: "rect", x: 0, y: 0, w: 20, h: 92, fill: "primary" },
      { id: "logo_acm", type: "logo", src: "acm_nitsurat", x: 4, y: 6, w: 12, h: 12, fit: "contain" },
      { id: "photo", type: "photo", field: "photo", x: 3, y: 24, w: 14, h: 18, shape: "rounded", radius: 2 },
      { id: "role", type: "role_badge", field: "role", x: 3, y: 46, w: 14, h: 6 },
      { id: "logo_svnit", type: "logo", src: "svnit", x: 34, y: 6, w: 12, h: 12, fit: "contain" },
      { id: "line", type: "line", x1: 24, y1: 20, x2: 52, y2: 20, stroke: "secondary", stroke_width: 0.4 },
      { id: "name", type: "text", field: "name", x: 24, y: 26, w: 28, font: "heading", color: "text", max_font: 13, min_font: 8, max_lines: 2, align: "left", bold: true },
      { id: "team", type: "text", field: "team", x: 24, y: 44, w: 28, font: "body", color: "accent", max_font: 9, min_font: 7, max_lines: 1, align: "left" },
      { id: "id", type: "text", field: "id", x: 24, y: 52, w: 28, font: "body", color: "text", max_font: 8, min_font: 6, max_lines: 1, align: "left" },
      { id: "qr", type: "qr", field: "qr_url", x: 24, y: 64, w: 16, h: 16 },
    ],
  },
};

const FONT_OPTIONS = [
  "Inter",
  "Poppins",
  "Rajdhani",
  "Chakra Petch",
  "Space Grotesk",
  "Bebas Neue",
];

const THEME_TOKENS = ["background", "primary", "secondary", "accent", "text", "none"] as const;

// WCAG relative luminance & contrast calculation
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const num = parseInt(clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function relativeLuminance(r: number, g: number, b: number): number {
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function calculateContrast(hex1: string, hex2: string): number {
  try {
    const l1 = relativeLuminance(...hexToRgb(hex1));
    const l2 = relativeLuminance(...hexToRgb(hex2));
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  } catch {
    return 1;
  }
}

// Helper to calculate standard bounding box for any element
function getElementBounds(el: LayoutElement): { x: number; y: number; w: number; h: number } {
  if (el.type === "circle") {
    const r = el.r || 5;
    return { x: (el.cx || 0) - r, y: (el.cy || 0) - r, w: 2 * r, h: 2 * r };
  }
  if (el.type === "line") {
    const x = Math.min(el.x1 ?? 0, el.x2 ?? 0);
    const y = Math.min(el.y1 ?? 0, el.y2 ?? 0);
    const w = Math.max(Math.abs((el.x2 ?? 0) - (el.x1 ?? 0)), 2);
    const h = Math.max(Math.abs((el.y2 ?? 0) - (el.y1 ?? 0)), 2);
    return { x, y, w, h };
  }
  const x = el.x ?? 0;
  const y = el.y ?? 0;
  const w = el.w ?? 20;
  let h = el.h;
  if (h === undefined || h === null) {
    if (el.type === "logo") h = w;
    else if (el.type === "text") {
      const maxLines = el.max_lines || 1;
      const pt = el.max_font || 12;
      h = Math.max(4, pt * 0.352778 * maxLines * 1.3);
    } else {
      h = 10;
    }
  }
  return { x, y, w, h };
}

// Preset background patterns and art available for cards
export const BACKGROUND_PRESETS = [
  {
    id: "bg_tech_grid",
    label: "Tech Cyber Grid",
    icon: "🌐",
    relativeRepoPath: "frontend/public/art/bg_tech_grid.svg",
    publicPath: "/art/bg_tech_grid.svg",
    description: "Futuristic digital matrix with circuit nodes",
    defaultOpacity: 0.35,
  },
  {
    id: "bg_geometric_mesh",
    label: "Geometric Mesh",
    icon: "📐",
    relativeRepoPath: "frontend/public/art/bg_geometric_mesh.svg",
    publicPath: "/art/bg_geometric_mesh.svg",
    description: "Low-poly faceted polygons with sleek gradient tones",
    defaultOpacity: 0.3,
  },
  {
    id: "bg_svnit_watermark",
    label: "SVNIT Crest Emblem",
    icon: "🏛️",
    relativeRepoPath: "frontend/public/art/bg_svnit_watermark.svg",
    publicPath: "/art/bg_svnit_watermark.svg",
    description: "Official institutional watermark centered with radiant glow",
    defaultOpacity: 0.25,
  },
  {
    id: "bg_circuit_lines",
    label: "Circuit Board",
    icon: "⚡",
    relativeRepoPath: "frontend/public/art/bg_circuit_lines.svg",
    publicPath: "/art/bg_circuit_lines.svg",
    description: "Motherboard micro-traces and neon interconnects",
    defaultOpacity: 0.3,
  },
  {
    id: "bg_acm_watermark",
    label: "ACM Diamond Pattern",
    icon: "💎",
    relativeRepoPath: "frontend/public/logos/acm_nitsurat.svg",
    publicPath: "/logos/acm_nitsurat.svg",
    description: "ACM NIT Surat chapter emblem watermark",
    defaultOpacity: 0.15,
  },
];

// Preset decals & graphic elements for placing anywhere on cards
export const DECAL_PRESETS = [
  {
    id: "decal_star",
    label: "VIP Star",
    icon: "🌟",
    relativeRepoPath: "frontend/public/art/decal_star.svg",
    publicPath: "/art/decal_star.svg",
    defaultW: 14,
    defaultH: 14,
  },
  {
    id: "decal_terminal",
    label: "Code Terminal",
    icon: "💻",
    relativeRepoPath: "frontend/public/art/decal_terminal.svg",
    publicPath: "/art/decal_terminal.svg",
    defaultW: 16,
    defaultH: 16,
  },
  {
    id: "decal_shield",
    label: "Verified Shield",
    icon: "🛡️",
    relativeRepoPath: "frontend/public/art/decal_shield.svg",
    publicPath: "/art/decal_shield.svg",
    defaultW: 14,
    defaultH: 14,
  },
  {
    id: "decal_chip",
    label: "Hardware Chip",
    icon: "⚡",
    relativeRepoPath: "frontend/public/art/decal_chip.svg",
    publicPath: "/art/decal_chip.svg",
    defaultW: 14,
    defaultH: 14,
  },
  {
    id: "logo_acm_decal",
    label: "ACM Crest",
    icon: "🏛️",
    relativeRepoPath: "frontend/public/logos/acm_nitsurat.svg",
    publicPath: "/logos/acm_nitsurat.svg",
    defaultW: 14,
    defaultH: 14,
  },
  {
    id: "logo_svnit_decal",
    label: "SVNIT Seal",
    icon: "🏫",
    relativeRepoPath: "frontend/public/logos/svnit.svg",
    publicPath: "/logos/svnit.svg",
    defaultW: 14,
    defaultH: 14,
  },
];

// Helper to resolve the usable image src/href for an element
function getElementImageSrc(el: LayoutElement, spec: DesignSpec): string {
  if (el.dataUrl && typeof el.dataUrl === "string") return el.dataUrl;
  if (el.src && typeof el.src === "string") {
    // If it's a key in brand.logos
    const brandPath = spec.brand?.logos?.[el.src];
    if (brandPath) {
      if (brandPath.startsWith("frontend/public/")) {
        return brandPath.replace("frontend/public", "");
      }
      if (brandPath.startsWith("assets/logos/")) {
        return "/" + brandPath.replace("assets/", "");
      }
      return brandPath;
    }
    // If it's a direct public or relative path
    if (el.src.startsWith("/")) return el.src;
    if (el.src.startsWith("art/")) return "/" + el.src;
    if (el.src.startsWith("frontend/public/")) return el.src.replace("frontend/public", "");
    return el.src;
  }
  return "/art/bg_tech_grid.svg";
}

// sanitizeSpecForBackend is imported from ../lib/specSanitizer to guarantee 100% parity across editor, preview, and batch export


// Ensure every layout element has a distinct, non-empty ID to prevent shared selection bugs
function normalizeSpec(rawSpec: DesignSpec): DesignSpec {
  if (!rawSpec) return rawSpec;
  const cloned: DesignSpec = JSON.parse(JSON.stringify(rawSpec));
  const counts: Record<string, number> = {};
  cloned.elements = (cloned.elements || []).map((el, idx) => {
    const baseType = el.type || "element";
    counts[baseType] = (counts[baseType] || 0) + 1;
    const assignedId = el.id && el.id.trim() ? el.id.trim() : `${baseType}_${counts[baseType]}`;
    return { ...el, id: assignedId };
  });
  return cloned;
}

// Enrich SVG with client-side elements (background image and custom image decals)
function enrichSvgWithClientElements(svgString: string, spec: DesignSpec): string {
  if (!svgString) return "";
  let enriched = svgString;

  const rawBg = (spec.theme?.colors?.background || "").toLowerCase();
  const isTrans =
    rawBg === "none" ||
    rawBg === "transparent" ||
    rawBg === "#00000000" ||
    rawBg === "#ffffff00" ||
    spec.elements.some((el) => (el.id === "bg" || el.id === "background") && (el.fill === "none" || el.opacity === 0));

  const bgFillColor = isTrans ? "none" : (spec.theme?.colors?.background || "#0B1220");
  const canvasW = spec.page.width_mm + 2 * spec.page.bleed_mm;
  const canvasH = spec.page.height_mm + 2 * spec.page.bleed_mm;

  // 1. Ensure the base canvas background rect reflects the active background color / transparency
  if (/<rect\b[^>]*\bid=["'](?:bg|background)["']/i.test(enriched)) {
    enriched = enriched.replace(
      /(<rect\b[^>]*\bid=["'](?:bg|background)["'][^>]*\bfill=")[^"]*(")/i,
      `$1${bgFillColor}$2`
    );
  } else if (/<svg\b[^>]*>/i.test(enriched)) {
    const baseRectTag = `<rect id="bg" x="0" y="0" width="${canvasW}" height="${canvasH}" fill="${bgFillColor}" stroke="none" />`;
    enriched = enriched.replace(/(<svg\b[^>]*>)/i, `$1\n  ${baseRectTag}`);
  }

  // 2. Inject Card Background Image if present in elements and not already rendered by backend
  const bgImageEl = spec.elements.find((el) => el.id === "bg_image" || el.is_background);
  const hasBgAlready = /<image\b[^>]*\bid=["']bg_image["']/i.test(enriched) || /data-logo-name=["']bg_image["']/i.test(enriched);
  if (bgImageEl && !hasBgAlready) {
    const src = getElementImageSrc(bgImageEl, spec);
    const opacity = bgImageEl.opacity !== undefined ? bgImageEl.opacity : 0.35;
    const fit = bgImageEl.fit || "cover";
    const par = fit === "contain" ? "xMidYMid meet" : fit === "fill" ? "none" : "xMidYMid slice";
    const x = bgImageEl.x ?? 0;
    const y = bgImageEl.y ?? 0;
    const w = bgImageEl.w ?? canvasW;
    const h = bgImageEl.h ?? canvasH;
    const bgImgTag = `<image id="bg_image" href="${src}" x="${x}" y="${y}" width="${w}" height="${h}" opacity="${opacity}" preserveAspectRatio="${par}" style="pointer-events: none;" />`;

    // Place immediately after the background rect (id="bg" or id="background"), or right inside <svg ...>
    if (/<rect\b[^>]*\bid=["'](?:bg|background)["'][^>]*\/>/i.test(enriched)) {
      enriched = enriched.replace(
        /(<rect\b[^>]*\bid=["'](?:bg|background)["'][^>]*\/>)/i,
        `$1\n  ${bgImgTag}`
      );
    } else if (/<svg\b[^>]*>/i.test(enriched)) {
      enriched = enriched.replace(/(<svg\b[^>]*>)/i, `$1\n  ${bgImgTag}`);
    }
  }

  // 2. Inject any custom decals / images placed anywhere on the card if not already rendered
  const customImages = spec.elements.filter(
    (el) =>
      (el.type === "image" || el.type === "svg_asset") &&
      el.id !== "bg_image" &&
      !el.is_background &&
      !new RegExp(`<image\\b[^>]*\\bid=["']${el.id}["']`, "i").test(enriched)
  );

  if (customImages.length > 0) {
    const customImgTags = customImages
      .map((el) => {
        const src = getElementImageSrc(el, spec);
        const opacity = el.opacity !== undefined ? el.opacity : 1;
        const fit = el.fit || "contain";
        const par = fit === "cover" ? "xMidYMid slice" : fit === "fill" ? "none" : "xMidYMid meet";
        const bounds = getElementBounds(el);
        return `<image id="${el.id}" href="${src}" x="${bounds.x}" y="${bounds.y}" width="${bounds.w}" height="${bounds.h}" opacity="${opacity}" preserveAspectRatio="${par}" style="pointer-events: none;" />`;
      })
      .join("\n  ");

    if (/<g id="debug-guides"/i.test(enriched)) {
      enriched = enriched.replace(/(<g id="debug-guides")/i, `${customImgTags}\n  $1`);
    } else {
      enriched = enriched.replace(/<\/svg>/i, `  ${customImgTags}\n</svg>`);
    }
  }

  return enriched;
}

export default function VisualSpecEditor({
  initialSpec,
  attendees = [],
  onApplySpec,
  onChangeSpec,
  onClose,
}: VisualSpecEditorProps) {
  // Working specification with guaranteed unique element IDs
  const [spec, setSpec] = useState<DesignSpec>(() => normalizeSpec(initialSpec));
  const [designName, setDesignName] = useState<string>("Custom Event ID Card");

  // Undo / Redo history stacks
  const [undoStack, setUndoStack] = useState<DesignSpec[]>([]);
  const [redoStack, setRedoStack] = useState<DesignSpec[]>([]);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<"saved" | "unsaved" | "saving">("saved");

  // Selection state - strictly null on start so nothing is auto-selected
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);

  // Left sidebar navigation & collapsible state (Canva/Figma inspired)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [sidebarTab, setSidebarTab] = useState<"layers" | "add" | "assets" | "presets" | "refine" | "json">("layers");
  const [layerSearch, setLayerSearch] = useState<string>("");

  // Modals for Custom Theme / Layout creation
  const [showThemeModal, setShowThemeModal] = useState<boolean>(false);
  const [newThemeName, setNewThemeName] = useState<string>("");
  const [showLayoutModal, setShowLayoutModal] = useState<boolean>(false);
  const [newLayoutName, setNewLayoutName] = useState<string>("");
  const [showSavedModal, setShowSavedModal] = useState<boolean>(false);
  const [savedDesigns, setSavedDesigns] = useState<Array<{ id: string; name: string; date: string; spec: DesignSpec }>>([]);

  // Active persona
  const personas = useMemo(() => {
    return attendees.length > 0 ? attendees.slice(0, 8) : DEFAULT_PERSONAS;
  }, [attendees]);
  const [selectedPersonaIndex, setSelectedPersonaIndex] = useState<number>(0);
  const currentPersona = personas[selectedPersonaIndex] || DEFAULT_PERSONAS[0];

  // SVG Preview & Canvas Controls (Print Guides default to FALSE for a clean, uncluttered card)
  const [svgContent, setSvgContent] = useState<string>("");
  const [loadingSvg, setLoadingSvg] = useState<boolean>(false);
  const [showDebugGuides, setShowDebugGuides] = useState<boolean>(false);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Active card background image helper
  const activeBg = useMemo(() => {
    return spec.elements.find((el) => el.id === "bg_image" || el.is_background) || null;
  }, [spec.elements]);

  // Active card background transparency helper
  const isTransparentBackground = useMemo(() => {
    const bg = (spec.theme?.colors?.background || "").toLowerCase();
    if (bg === "none" || bg === "transparent" || bg === "#00000000" || bg === "#ffffff00") return true;
    const bgRect = spec.elements.find((el) => el.id === "bg" || el.id === "background");
    if (bgRect && (bgRect.fill === "none" || bgRect.opacity === 0)) return true;
    return false;
  }, [spec.theme?.colors?.background, spec.elements]);

  // Hidden file input refs and upload status
  const bgUploadInputRef = useRef<HTMLInputElement | null>(null);
  const decalUploadInputRef = useRef<HTMLInputElement | null>(null);
  const replaceImageInputRef = useRef<HTMLInputElement | null>(null);
  const [isUploadingAsset, setIsUploadingAsset] = useState<boolean>(false);

  // Responsive SVG markup ensuring 100% width and height so card aligns exactly with overlay
  const responsiveSvg = useMemo(() => {
    if (!svgContent) return "";
    const enriched = enrichSvgWithClientElements(svgContent, spec);
    return enriched.replace(
      /<svg\b([^>]*)\bwidth="[^"]*"\s*height="[^"]*"/i,
      '<svg$1width="100%" height="100%"'
    );
  }, [svgContent, spec]);

  // Drag and Resize State
  const [interactionState, setInteractionState] = useState<{
    type: "none" | "drag" | "resize";
    elementId: string;
    handle?: string; // 'nw' | 'ne' | 'se' | 'sw' | 'n' | 's' | 'e' | 'w'
    startSvgX?: number;
    startSvgY?: number;
    initialBounds?: { x: number; y: number; w: number; h: number };
  }>({ type: "none", elementId: "" });

  const [snapLines, setSnapLines] = useState<{ x?: number; y?: number }>({});

  // Natural Language Refinement
  const [nlPrompt, setNlPrompt] = useState<string>("");
  const [nlLoading, setNlLoading] = useState<boolean>(false);
  const [nlMessage, setNlMessage] = useState<{ type: "success" | "error"; text: string; ops?: any[] } | null>(null);

  // JSON editor
  const [jsonInput, setJsonInput] = useState<string>(() => JSON.stringify(spec, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Ref to canvas SVG container and drag tracking
  const canvasSvgRef = useRef<SVGSVGElement | null>(null);
  const renderTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pointerDownPosRef = useRef<{ clientX: number; clientY: number; id: string; action: "drag" | "resize" } | null>(null);
  const hasMovedRef = useRef<boolean>(false);
  const lastEmittedSpecRef = useRef<string>("");

  // Normalize when initialSpec changes from the outside
  useEffect(() => {
    if (initialSpec) {
      const specStr = JSON.stringify(initialSpec);
      // If initialSpec changed because of an internal edit we just emitted to the parent, don't reset selection
      if (lastEmittedSpecRef.current && specStr === lastEmittedSpecRef.current) {
        return;
      }
      setSpec(normalizeSpec(initialSpec));
      // Only deselect if the currently selected element no longer exists in the incoming spec
      setSelectedElementId((prev) => {
        if (!prev) return null;
        const exists = (initialSpec.elements || []).some((el) => el.id === prev);
        return exists ? prev : null;
      });
    }
  }, [initialSpec]);

  // Push state to undo stack
  const recordChange = useCallback(
    (newSpec: DesignSpec) => {
      const normalized = normalizeSpec(newSpec);
      lastEmittedSpecRef.current = JSON.stringify(normalized);
      setUndoStack((prev) => [...prev.slice(-30), JSON.parse(JSON.stringify(spec))]);
      setRedoStack([]);
      setSpec(normalized);
      setIsDirty(true);
      setSaveStatus("unsaved");
      if (onChangeSpec) {
        onChangeSpec(normalized);
      }
    },
    [spec, onChangeSpec]
  );

  // Load custom saved designs from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("card_studio_saved_designs");
      if (stored) {
        setSavedDesigns(JSON.parse(stored));
      }
    } catch {
      // storage unavailable
    }
  }, []);

  // Sync JSON text when spec changes
  useEffect(() => {
    setJsonInput(JSON.stringify(spec, null, 2));
    setJsonError(null);
  }, [spec]);

  // Debounced SVG renderer on spec or persona change (sanitized to avoid backend 422 errors)
  useEffect(() => {
    if (renderTimeoutRef.current) clearTimeout(renderTimeoutRef.current);
    renderTimeoutRef.current = setTimeout(async () => {
      setLoadingSvg(true);
      try {
        const sanitized = sanitizeSpecForBackend(spec);
        const res = await renderPreview(sanitized, currentPersona, showDebugGuides);
        setSvgContent(res.svg);
      } catch (err: any) {
        console.error("Failed to render preview SVG:", err);
      } finally {
        setLoadingSvg(false);
      }
    }, 120);

    return () => {
      if (renderTimeoutRef.current) clearTimeout(renderTimeoutRef.current);
    };
  }, [spec, currentPersona, showDebugGuides]);

  // Warn on window close if unsaved changes exist
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // Selected element helper
  const selectedElement = useMemo(() => {
    if (!selectedElementId) return null;
    return spec.elements.find((el) => el.id === selectedElementId) || null;
  }, [spec.elements, selectedElementId]);

  // Undo / Redo actions
  const handleUndo = useCallback(() => {
    if (undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    setUndoStack((prev) => prev.slice(0, -1));
    setRedoStack((prev) => [JSON.parse(JSON.stringify(spec)), ...prev]);
    setSpec(previous);
    setIsDirty(true);
  }, [undoStack, spec]);

  const handleRedo = useCallback(() => {
    if (redoStack.length === 0) return;
    const next = redoStack[0];
    setRedoStack((prev) => prev.slice(1));
    setUndoStack((prev) => [...prev, JSON.parse(JSON.stringify(spec))]);
    setSpec(next);
    setIsDirty(true);
  }, [redoStack, spec]);

  // Keyboard shortcut listener (Ctrl+Z, Ctrl+Y, Arrow keys, Delete)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't intercept when user is typing in input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        if (e.shiftKey) {
          e.preventDefault();
          handleRedo();
        } else {
          e.preventDefault();
          handleUndo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        handleRedo();
      } else if ((e.key === "Delete" || e.key === "Backspace") && selectedElementId) {
        // Prevent deleting mandatory institutional logos
        const isMandatoryLogo =
          (selectedElement?.type === "logo" &&
            (selectedElement.src === "acm_nitsurat" || selectedElement.src === "svnit")) ||
          selectedElement?.id === "logo_acm" ||
          selectedElement?.id === "logo_svnit";
        if (isMandatoryLogo) {
          alert("Institutional logos (ACM NIT Surat & SVNIT) are mandatory per project specification.");
          return;
        }
        e.preventDefault();
        deleteElement(selectedElementId);
      } else if (selectedElement && ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
        e.preventDefault();
        const step = e.shiftKey ? 2 : 0.5;
        const dx = e.key === "ArrowLeft" ? -step : e.key === "ArrowRight" ? step : 0;
        const dy = e.key === "ArrowUp" ? -step : e.key === "ArrowDown" ? step : 0;
        nudgeElement(selectedElement.id, dx, dy);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleUndo, handleRedo, selectedElementId, selectedElement]);


  // --- Element Mutation Functions ---

  function updateElement(id: string, updates: Partial<LayoutElement>) {
    const updatedElements = spec.elements.map((el) => (el.id === id ? { ...el, ...updates } : el));
    recordChange({ ...spec, elements: updatedElements });
  }

  function nudgeElement(id: string, dx: number, dy: number) {
    const updatedElements = spec.elements.map((el) => {
      if (el.id !== id) return el;
      if (el.type === "circle") {
        return { ...el, cx: Math.round(((el.cx || 0) + dx) * 10) / 10, cy: Math.round(((el.cy || 0) + dy) * 10) / 10 };
      }
      if (el.type === "line") {
        return {
          ...el,
          x1: Math.round(((el.x1 || 0) + dx) * 10) / 10,
          y1: Math.round(((el.y1 || 0) + dy) * 10) / 10,
          x2: Math.round(((el.x2 || 0) + dx) * 10) / 10,
          y2: Math.round(((el.y2 || 0) + dy) * 10) / 10,
        };
      }
      return {
        ...el,
        x: Math.round(((el.x || 0) + dx) * 10) / 10,
        y: Math.round(((el.y || 0) + dy) * 10) / 10,
      };
    });
    recordChange({ ...spec, elements: updatedElements });
  }

  function deleteElement(id: string) {
    const target = spec.elements.find((el) => el.id === id);
    if (!target) return;
    const isMandatoryLogo =
      (target.type === "logo" && (target.src === "acm_nitsurat" || target.src === "svnit")) ||
      target.id === "logo_acm" ||
      target.id === "logo_svnit";
    if (isMandatoryLogo) {
      alert("Institutional logos (ACM NIT Surat & SVNIT) are mandatory and cannot be removed.");
      return;
    }
    const updatedElements = spec.elements.filter((el) => el.id !== id);
    recordChange({ ...spec, elements: updatedElements });
    if (selectedElementId === id) setSelectedElementId(null);
  }

  function duplicateElement(id: string) {
    const target = spec.elements.find((el) => el.id === id);
    if (!target) return;
    const newId = `${target.type}_${Date.now().toString(36).slice(-4)}`;
    const cloned = JSON.parse(JSON.stringify(target));
    cloned.id = newId;
    if (cloned.x !== undefined) cloned.x += 3;
    if (cloned.y !== undefined) cloned.y += 3;
    if (cloned.cx !== undefined) cloned.cx += 3;
    if (cloned.cy !== undefined) cloned.cy += 3;
    if (cloned.x1 !== undefined) {
      cloned.x1 += 3;
      cloned.x2 += 3;
      cloned.y1 += 3;
      cloned.y2 += 3;
    }
    recordChange({ ...spec, elements: [...spec.elements, cloned] });
    setSelectedElementId(newId);
  }

  function reorderElement(id: string, direction: "up" | "down" | "top" | "bottom") {
    const idx = spec.elements.findIndex((el) => el.id === id);
    if (idx === -1) return;
    const elements = [...spec.elements];
    const [item] = elements.splice(idx, 1);
    if (direction === "up") {
      elements.splice(Math.min(elements.length, idx + 1), 0, item);
    } else if (direction === "down") {
      elements.splice(Math.max(0, idx - 1), 0, item);
    } else if (direction === "top") {
      elements.push(item);
    } else if (direction === "bottom") {
      elements.unshift(item);
    }
    recordChange({ ...spec, elements });
  }

  function addElement(type: string, defaults: Partial<LayoutElement>) {
    const id = `${type}_${Date.now().toString(36).slice(-4)}`;
    const newEl: LayoutElement = { id, type, ...defaults };
    recordChange({ ...spec, elements: [...spec.elements, newEl] });
    setSelectedElementId(id);
  }

  // --- Background Image Management ---

  function applyBackgroundPreset(presetId: string) {
    const preset = BACKGROUND_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;

    const totalW = spec.page.width_mm + 2 * spec.page.bleed_mm;
    const totalH = spec.page.height_mm + 2 * spec.page.bleed_mm;

    const existingIdx = spec.elements.findIndex((el) => el.id === "bg_image" || el.is_background);
    const bgElement: LayoutElement = {
      id: "bg_image",
      type: "image",
      src: preset.publicPath,
      x: 0,
      y: 0,
      w: totalW,
      h: totalH,
      opacity: preset.defaultOpacity,
      fit: "cover",
      is_background: true,
    };

    const newElements = [...spec.elements];
    if (existingIdx !== -1) {
      newElements[existingIdx] = bgElement;
    } else {
      const bgRectIdx = newElements.findIndex((el) => el.id === "bg" || el.type === "rect");
      if (bgRectIdx !== -1) {
        newElements.splice(bgRectIdx + 1, 0, bgElement);
      } else {
        newElements.unshift(bgElement);
      }
    }

    const updatedBrand = {
      ...spec.brand,
      logos: {
        ...(spec.brand?.logos || {}),
        [preset.id]: preset.relativeRepoPath,
      },
    };

    recordChange({
      ...spec,
      brand: updatedBrand,
      elements: newElements,
    });
  }

  async function handleUploadBackground(file: File) {
    try {
      setIsUploadingAsset(true);
      const res = await uploadAsset(file);

      const totalW = spec.page.width_mm + 2 * spec.page.bleed_mm;
      const totalH = spec.page.height_mm + 2 * spec.page.bleed_mm;

      const existingIdx = spec.elements.findIndex((el) => el.id === "bg_image" || el.is_background);
      const bgElement: LayoutElement = {
        id: "bg_image",
        type: "image",
        src: res.publicPath,
        dataUrl: res.dataUrl,
        x: 0,
        y: 0,
        w: totalW,
        h: totalH,
        opacity: 0.75,
        fit: "cover",
        is_background: true,
      };

      const newElements = [...spec.elements];
      if (existingIdx !== -1) {
        newElements[existingIdx] = bgElement;
      } else {
        const bgRectIdx = newElements.findIndex((el) => el.id === "bg" || el.type === "rect");
        if (bgRectIdx !== -1) {
          newElements.splice(bgRectIdx + 1, 0, bgElement);
        } else {
          newElements.unshift(bgElement);
        }
      }

      const updatedBrand = {
        ...spec.brand,
        logos: {
          ...(spec.brand?.logos || {}),
          bg_custom: res.relativeRepoPath,
        },
      };

      recordChange({
        ...spec,
        brand: updatedBrand,
        elements: newElements,
      });
      setSelectedElementId("bg_image");
    } catch (err: any) {
      alert("Failed to upload background image: " + (err?.message || "Unknown error"));
    } finally {
      setIsUploadingAsset(false);
    }
  }

  function removeBackgroundImage() {
    const newElements = spec.elements.filter((el) => el.id !== "bg_image" && !el.is_background);
    recordChange({ ...spec, elements: newElements });
    if (selectedElementId === "bg_image") {
      setSelectedElementId(null);
    }
  }

  function updateBackgroundOpacity(opacity: number) {
    const target = spec.elements.find((el) => el.id === "bg_image" || el.is_background);
    if (!target) return;
    updateElement(target.id, { opacity: Math.max(0.05, Math.min(1, opacity)) });
  }

  function setBackgroundFitMode(fit: "cover" | "contain" | "fill") {
    const target = spec.elements.find((el) => el.id === "bg_image" || el.is_background);
    if (!target) return;
    updateElement(target.id, { fit });
  }

  // --- Decal & Graphic Element Management ---

  function addDecalPreset(presetId: string) {
    const preset = DECAL_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;

    const id = `decal_${Date.now().toString(36).slice(-4)}`;
    const newEl: LayoutElement = {
      id,
      type: "image",
      src: preset.publicPath,
      x: 22, // centered in safe area
      y: 35, // middle of card
      w: preset.defaultW,
      h: preset.defaultH,
      opacity: 1,
      fit: "contain",
    };

    const updatedBrand = {
      ...spec.brand,
      logos: {
        ...(spec.brand?.logos || {}),
        [preset.id]: preset.relativeRepoPath,
      },
    };

    recordChange({
      ...spec,
      brand: updatedBrand,
      elements: [...spec.elements, newEl],
    });
    setSelectedElementId(id);
  }

  async function handleUploadDecal(file: File) {
    try {
      setIsUploadingAsset(true);
      const res = await uploadAsset(file);
      const id = `img_${Date.now().toString(36).slice(-4)}`;
      const newEl: LayoutElement = {
        id,
        type: "image",
        src: res.publicPath,
        dataUrl: res.dataUrl,
        x: 20,
        y: 34,
        w: 16,
        h: 16,
        opacity: 1,
        fit: "contain",
      };

      const updatedBrand = {
        ...spec.brand,
        logos: {
          ...(spec.brand?.logos || {}),
          [id]: res.relativeRepoPath,
        },
      };

      recordChange({
        ...spec,
        brand: updatedBrand,
        elements: [...spec.elements, newEl],
      });
      setSelectedElementId(id);
    } catch (err: any) {
      alert("Failed to upload image: " + (err?.message || "Unknown error"));
    } finally {
      setIsUploadingAsset(false);
    }
  }

  async function handleReplaceImage(file: File, elementId: string) {
    try {
      setIsUploadingAsset(true);
      const res = await uploadAsset(file);
      updateElement(elementId, {
        src: res.publicPath,
        dataUrl: res.dataUrl,
      });
    } catch (err: any) {
      alert("Failed to replace image: " + (err?.message || "Unknown error"));
    } finally {
      setIsUploadingAsset(false);
    }
  }

  // --- Theme & Background Color Management ---

  function setCardBackgroundColor(color: string) {
    const isTrans = color === "transparent" || color === "none" || color === "#00000000";
    const totalW = spec.page.width_mm + 2 * spec.page.bleed_mm;
    const totalH = spec.page.height_mm + 2 * spec.page.bleed_mm;

    // 1. Update theme background color
    const updatedTheme: Theme = {
      ...spec.theme,
      colors: {
        ...spec.theme.colors,
        background: isTrans ? "#00000000" : color.toUpperCase(),
      },
    };

    // 2. Guarantee base background rectangle exists in elements with accurate fill
    const elements = [...spec.elements];
    const existingBgIdx = elements.findIndex(
      (el) =>
        el.type === "rect" &&
        (el.id === "bg" ||
          el.id === "background" ||
          (el.x === 0 && el.y === 0 && (el.w || 0) >= totalW - 1 && (el.h || 0) >= totalH - 1))
    );

    const bgRect: LayoutElement = {
      id: "bg",
      type: "rect",
      x: 0,
      y: 0,
      w: totalW,
      h: totalH,
      fill: isTrans ? "none" : "background",
      stroke: "none",
      stroke_width: 0,
      opacity: 1,
    };

    if (existingBgIdx !== -1) {
      elements[existingBgIdx] = {
        ...elements[existingBgIdx],
        ...bgRect,
        radius: elements[existingBgIdx].radius || 0,
      };
    } else {
      elements.unshift(bgRect);
    }

    recordChange({
      ...spec,
      theme: updatedTheme,
      elements,
    });
  }

  function updateThemeToken(token: keyof ThemeColors, hex: string) {
    if (token === "background") {
      setCardBackgroundColor(hex);
      return;
    }
    const updatedTheme: Theme = {
      ...spec.theme,
      colors: {
        ...spec.theme.colors,
        [token]: hex.toUpperCase(),
      },
    };
    recordChange({ ...spec, theme: updatedTheme });
  }

  function updateRoleColor(role: string, hex: string) {
    const updatedTheme: Theme = {
      ...spec.theme,
      role_colors: {
        ...spec.theme.role_colors,
        [role]: hex.toUpperCase(),
      },
    };
    recordChange({ ...spec, theme: updatedTheme });
  }

  function applyThemePreset(presetKey: string) {
    const preset = THEME_PRESETS[presetKey];
    if (!preset) return;
    recordChange({
      ...spec,
      theme_name: presetKey,
      theme: {
        ...spec.theme,
        name: presetKey,
        colors: { ...preset.colors },
        role_colors: { ...preset.role_colors },
      },
    });
  }

  function saveCustomTheme() {
    if (!newThemeName.trim()) return;
    const cleanName = newThemeName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "_");
    const updatedTheme: Theme = {
      ...spec.theme,
      name: cleanName,
    };
    recordChange({
      ...spec,
      theme_name: cleanName,
      theme: updatedTheme,
    });
    setShowThemeModal(false);
    setNewThemeName("");
  }

  // --- Layout Management ---

  function applyLayoutPreset(layoutKey: string) {
    const preset = LAYOUT_PRESETS[layoutKey];
    if (!preset) return;
    const newSpec = normalizeSpec({
      ...spec,
      layout_name: layoutKey,
      elements: JSON.parse(JSON.stringify(preset.elements)),
    });
    recordChange(newSpec);
    setSelectedElementId(null);
  }

  function saveCustomLayout() {
    if (!newLayoutName.trim()) return;
    const cleanName = newLayoutName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "_");
    recordChange({
      ...spec,
      layout_name: cleanName,
    });
    setShowLayoutModal(false);
    setNewLayoutName("");
  }

  // --- Complete Design Persistence ---

  function handleSaveDesign() {
    setSaveStatus("saving");
    try {
      const designEntry = {
        id: `design_${Date.now()}`,
        name: designName || "Custom Event Card",
        date: new Date().toLocaleString(),
        spec: JSON.parse(JSON.stringify(spec)),
      };
      const updated = [designEntry, ...savedDesigns.filter((d) => d.name !== designEntry.name)];
      setSavedDesigns(updated);
      localStorage.setItem("card_studio_saved_designs", JSON.stringify(updated));
      localStorage.setItem("card_studio_active_spec", JSON.stringify(spec));
      setIsDirty(false);
      setSaveStatus("saved");
      if (onApplySpec) onApplySpec(spec);
    } catch (err) {
      console.error("Save failed:", err);
      setSaveStatus("unsaved");
    }
  }

  function handleLoadDesign(savedSpec: DesignSpec, name: string) {
    recordChange(JSON.parse(JSON.stringify(savedSpec)));
    setDesignName(name);
    setShowSavedModal(false);
    setSelectedElementId(null);
  }

  function handleDeleteSavedDesign(id: string) {
    const updated = savedDesigns.filter((d) => d.id !== id);
    setSavedDesigns(updated);
    try {
      localStorage.setItem("card_studio_saved_designs", JSON.stringify(updated));
    } catch {}
  }

  // --- Canvas Coordinate Conversion (SVG getScreenCTM) ---

  const getSvgCoordinates = useCallback((clientX: number, clientY: number): { x: number; y: number } | null => {
    if (!canvasSvgRef.current) return null;
    const svg = canvasSvgRef.current;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const svgPt = pt.matrixTransform(ctm.inverse());
    return { x: svgPt.x, y: svgPt.y };
  }, []);

  // --- Interactive Drag and Resize Handlers ---

  const handlePointerDown = (
    e: React.PointerEvent,
    id: string,
    action: "drag" | "resize",
    handle?: string
  ) => {
    e.stopPropagation();
    const coords = getSvgCoordinates(e.clientX, e.clientY);
    if (!coords) return;

    const target = spec.elements.find((el) => el.id === id);
    if (!target) return;

    const bounds = getElementBounds(target);

    pointerDownPosRef.current = { clientX: e.clientX, clientY: e.clientY, id, action };
    hasMovedRef.current = false;

    setInteractionState({
      type: action,
      elementId: id,
      handle,
      startSvgX: coords.x,
      startSvgY: coords.y,
      initialBounds: bounds,
    });

    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (
      interactionState.type === "none" ||
      !interactionState.initialBounds ||
      interactionState.startSvgX === undefined ||
      interactionState.startSvgY === undefined
    ) {
      return;
    }

    // Check pixel displacement threshold to separate intentional drag from a static click
    if (pointerDownPosRef.current && !hasMovedRef.current) {
      const screenDx = e.clientX - pointerDownPosRef.current.clientX;
      const screenDy = e.clientY - pointerDownPosRef.current.clientY;
      if (Math.hypot(screenDx, screenDy) > 3) {
        hasMovedRef.current = true;
        setSelectedElementId(interactionState.elementId);
      } else {
        return;
      }
    }

    const coords = getSvgCoordinates(e.clientX, e.clientY);
    if (!coords) return;

    const dx = coords.x - interactionState.startSvgX;
    const dy = coords.y - interactionState.startSvgY;
    const target = spec.elements.find((el) => el.id === interactionState.elementId);
    if (!target) return;

    const init = interactionState.initialBounds;

    if (interactionState.type === "drag") {
      let nextX = init.x + dx;
      let nextY = init.y + dy;

      // Magnetic Snapping (0.8 mm threshold)
      const snapThreshold = 0.8;
      const snapTarget: { x?: number; y?: number } = {};

      // Horizontal snaps
      if (Math.abs(nextX - 7) < snapThreshold) {
        nextX = 7;
        snapTarget.x = 7;
      } else if (Math.abs(nextX + init.w - 53) < snapThreshold) {
        nextX = 53 - init.w;
        snapTarget.x = 53;
      } else if (Math.abs(nextX + init.w / 2 - 30) < snapThreshold) {
        nextX = 30 - init.w / 2;
        snapTarget.x = 30;
      }

      // Vertical snaps
      if (Math.abs(nextY - 7) < snapThreshold) {
        nextY = 7;
        snapTarget.y = 7;
      } else if (Math.abs(nextY + init.h - 85) < snapThreshold) {
        nextY = 85 - init.h;
        snapTarget.y = 85;
      } else if (Math.abs(nextY + init.h / 2 - 46) < snapThreshold) {
        nextY = 46 - init.h / 2;
        snapTarget.y = 46;
      }

      setSnapLines(snapTarget);

      // Clamp inside canvas (0..60 mm, 0..92 mm)
      nextX = Math.max(-10, Math.min(70, nextX));
      nextY = Math.max(-10, Math.min(100, nextY));

      const roundedX = Math.round(nextX * 10) / 10;
      const roundedY = Math.round(nextY * 10) / 10;

      // Update state without polluting undo stack until pointer up
      setSpec((prev) => ({
        ...prev,
        elements: prev.elements.map((el) => {
          if (el.id !== target.id) return el;
          if (el.type === "circle") {
            return { ...el, cx: roundedX + (el.r || 5), cy: roundedY + (el.r || 5) };
          }
          if (el.type === "line") {
            const width = Math.abs((el.x2 || 0) - (el.x1 || 0));
            const height = Math.abs((el.y2 || 0) - (el.y1 || 0));
            return { ...el, x1: roundedX, y1: roundedY, x2: roundedX + width, y2: roundedY + height };
          }
          return { ...el, x: roundedX, y: roundedY };
        }),
      }));
    } else if (interactionState.type === "resize") {
      const handle = interactionState.handle || "se";
      let newW = init.w;
      let newH = init.h;
      let newX = init.x;
      let newY = init.y;

      if (handle.includes("e")) newW = Math.max(4, init.w + dx);
      if (handle.includes("s")) newH = Math.max(3, init.h + dy);
      if (handle.includes("w")) {
        const potentialW = init.w - dx;
        if (potentialW >= 4) {
          newW = potentialW;
          newX = init.x + dx;
        }
      }
      if (handle.includes("n")) {
        const potentialH = init.h - dy;
        if (potentialH >= 3) {
          newH = potentialH;
          newY = init.y + dy;
        }
      }

      const roundedW = Math.round(newW * 10) / 10;
      const roundedH = Math.round(newH * 10) / 10;
      const roundedX = Math.round(newX * 10) / 10;
      const roundedY = Math.round(newY * 10) / 10;

      setSpec((prev) => ({
        ...prev,
        elements: prev.elements.map((el) => {
          if (el.id !== target.id) return el;
          if (el.type === "circle") {
            const newRadius = Math.max(2, Math.round((roundedW / 2) * 10) / 10);
            return { ...el, r: newRadius, cx: roundedX + newRadius, cy: roundedY + newRadius };
          }
          if (el.type === "qr") {
            // Keep QR square
            const side = Math.max(8, roundedW);
            return { ...el, x: roundedX, y: roundedY, w: side, h: side };
          }
          return { ...el, x: roundedX, y: roundedY, w: roundedW, h: roundedH };
        }),
      }));
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    e.stopPropagation();
    if (interactionState.type !== "none") {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {}

      const elementId = interactionState.elementId;
      const actionType = interactionState.type;
      const moved = hasMovedRef.current;

      setInteractionState({ type: "none", elementId: "" });
      setSnapLines({});
      pointerDownPosRef.current = null;
      hasMovedRef.current = false;

      if (!moved) {
        // Static click without dragging: Toggle selection!
        // Click once to select and see options; click again to deselect!
        if (actionType === "drag") {
          setSelectedElementId((prev) => (prev === elementId ? null : elementId));
        }
      } else {
        // Drag or resize completed: keep selected and record change
        setSelectedElementId(elementId);
        recordChange(JSON.parse(JSON.stringify(spec)));
      }
    }
  };

  // --- Natural Language Refine Handler ---

  async function handleNlRefine(e?: React.FormEvent, customPrompt?: string) {
    if (e) e.preventDefault();
    const promptToUse = customPrompt || nlPrompt;
    if (!promptToUse.trim()) return;

    setNlLoading(true);
    setNlMessage(null);
    try {
      const res = await refineSpec(spec, promptToUse);
      recordChange(res.spec);
      setNlMessage({
        type: "success",
        text: res.summary || `Applied ${res.ops.length} visual refinement(s)!`,
        ops: res.ops,
      });
      if (onApplySpec) onApplySpec(res.spec);
    } catch (err: any) {
      setNlMessage({
        type: "error",
        text: err.detail || err.message || "Failed to refine spec.",
      });
    } finally {
      setNlLoading(false);
    }
  }

  // --- Downloads and Exports (Strictly clean without debug guides or clutter) ---

  async function handleDownloadSvg() {
    try {
      // Clean SVG export strictly without debug guides
      const sanitized = sanitizeSpecForBackend(spec);
      const res = await renderPreview(sanitized, currentPersona, false);
      let cleanSvg = (res.svg || svgContent).replace(/<g id="debug-guides"[\s\S]*?<\/g>/gi, "");
      cleanSvg = enrichSvgWithClientElements(cleanSvg, spec);

      const blob = new Blob([cleanSvg], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${designName.toLowerCase().replace(/\s+/g, "_")}_badge.svg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      if (!svgContent) return;
      let cleanFallback = svgContent.replace(/<g id="debug-guides"[\s\S]*?<\/g>/gi, "");
      cleanFallback = enrichSvgWithClientElements(cleanFallback, spec);
      const blob = new Blob([cleanFallback], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${designName.toLowerCase().replace(/\s+/g, "_")}_badge.svg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  }

  function handleDownloadJson() {
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${designName.toLowerCase().replace(/\s+/g, "_")}_spec.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // Contrast scores
  const textContrast = useMemo(() => {
    const textCol = spec.theme?.colors?.text || "#0B1220";
    const bgCol = spec.theme?.colors?.background || "#FFFFFF";
    return calculateContrast(textCol, bgCol);
  }, [spec.theme?.colors?.text, spec.theme?.colors?.background]);

  const roleContrast = useMemo(() => {
    const role = (currentPersona.role || "participant").toLowerCase();
    const roleCol = spec.theme?.role_colors?.[role] || spec.theme?.colors?.primary || "#1F6FEB";
    const bgCol = spec.theme?.colors?.background || "#FFFFFF";
    return calculateContrast(roleCol, bgCol);
  }, [spec.theme?.role_colors, spec.theme?.colors?.primary, spec.theme?.colors?.background, currentPersona.role]);

  return (
    <div className="bg-[#121214] text-[#FAFAFA] rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col h-[900px] w-full font-sans select-none">
      {/* ============================================================== */}
      {/* 1. TOP MINIMAL TOOLBAR                                        */}
      {/* ============================================================== */}
      <header className="bg-[#0E0E10] border-b border-white/10 px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 z-20">
        {/* Left: Hamburger Sidebar Toggle, Branding & Editable Title */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setSidebarCollapsed((prev) => !prev)}
            className={`p-1.5 rounded-lg border transition flex items-center justify-center ${
              sidebarCollapsed
                ? "bg-cyan-500/15 border-cyan-400 text-cyan-400 hover:bg-cyan-500/25 shadow-sm"
                : "bg-white/5 border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
            }`}
            title={sidebarCollapsed ? "Expand Tools Sidebar (Layers, Add, Assets)" : "Collapse Sidebar (Maximum Canvas Area)"}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/15 p-1 flex items-center justify-center shrink-0">
            <img src="/logos/acm_nitsurat.svg" alt="ACM NIT Surat" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={designName}
                onChange={(e) => {
                  setDesignName(e.target.value);
                  setIsDirty(true);
                }}
                className="text-sm font-bold text-white bg-transparent border-b border-transparent hover:border-white/20 focus:border-cyan-400 focus:outline-none transition w-56"
                placeholder="Design Name"
              />
              <span className="text-[10px] font-mono bg-white/5 border border-white/10 text-[#A1A1AA] px-2 py-0.5 rounded-full">
                54 × 86 mm (ID-1)
              </span>
            </div>
            <p className="text-[10px] text-[#A1A1AA]">
              Layout: <span className="font-semibold text-white capitalize">{spec.layout_name}</span> • Theme:{" "}
              <span className="font-semibold text-white capitalize">{spec.theme_name}</span>
            </p>
          </div>
        </div>

        {/* Center: Layout & Theme Switchers, Undo/Redo, Zoom */}
        <div className="flex items-center space-x-2">
          {/* Layout Selector */}
          <div className="relative group">
            <button className="px-3 py-1.5 rounded-lg border border-white/10 bg-[#1A1A1D] hover:bg-white/10 text-xs font-semibold text-white flex items-center space-x-1.5 transition">
              <span>📐</span>
              <span className="capitalize">{spec.layout_name}</span>
              <span className="text-[10px] text-[#A1A1AA]">▼</span>
            </button>
            <div className="absolute top-full left-0 mt-1 w-48 bg-[#18181A] border border-white/15 rounded-xl shadow-2xl p-1.5 hidden group-hover:block z-50">
              <div className="text-[10px] font-bold uppercase text-[#A1A1AA] px-2 py-1">Layout Presets</div>
              {Object.keys(LAYOUT_PRESETS).map((key) => (
                <button
                  key={key}
                  onClick={() => applyLayoutPreset(key)}
                  className={`w-full text-left px-2 py-1.5 rounded-lg text-xs flex items-center justify-between transition ${
                    spec.layout_name === key ? "bg-white/15 text-white font-bold" : "text-[#A1A1AA] hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <span>{LAYOUT_PRESETS[key].label}</span>
                  <span>{LAYOUT_PRESETS[key].icon}</span>
                </button>
              ))}
              <div className="border-t border-white/10 my-1" />
              <button
                onClick={() => setShowLayoutModal(true)}
                className="w-full text-left px-2 py-1.5 rounded-lg text-xs text-cyan-400 hover:bg-cyan-950/40 font-semibold"
              >
                + New Blank Layout
              </button>
            </div>
          </div>

          {/* Theme Selector */}
          <div className="relative group">
            <button className="px-3 py-1.5 rounded-lg border border-white/10 bg-[#1A1A1D] hover:bg-white/10 text-xs font-semibold text-white flex items-center space-x-1.5 transition">
              <span>🎨</span>
              <span className="capitalize">{spec.theme_name}</span>
              <span className="text-[10px] text-[#A1A1AA]">▼</span>
            </button>
            <div className="absolute top-full left-0 mt-1 w-48 bg-[#18181A] border border-white/15 rounded-xl shadow-2xl p-1.5 hidden group-hover:block z-50">
              <div className="text-[10px] font-bold uppercase text-[#A1A1AA] px-2 py-1">Theme Presets</div>
              {Object.keys(THEME_PRESETS).map((key) => (
                <button
                  key={key}
                  onClick={() => applyThemePreset(key)}
                  className={`w-full text-left px-2 py-1.5 rounded-lg text-xs flex items-center space-x-2 transition ${
                    spec.theme_name === key ? "bg-white/15 text-white font-bold" : "text-[#A1A1AA] hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <span
                    className="w-3 h-3 rounded-full border border-white/20"
                    style={{ backgroundColor: THEME_PRESETS[key].colors.primary }}
                  />
                  <span>{THEME_PRESETS[key].label}</span>
                </button>
              ))}
              <div className="border-t border-white/10 my-1" />
              <button
                onClick={() => setShowThemeModal(true)}
                className="w-full text-left px-2 py-1.5 rounded-lg text-xs text-cyan-400 hover:bg-cyan-950/40 font-semibold"
              >
                + Create Custom Theme
              </button>
            </div>
          </div>

          <div className="h-4 w-px bg-white/10 mx-1" />

          {/* Undo & Redo */}
          <button
            onClick={handleUndo}
            disabled={undoStack.length === 0}
            className="p-1.5 rounded-lg border border-white/10 bg-[#1A1A1D] hover:bg-white/10 text-xs text-white transition disabled:opacity-30 disabled:hover:bg-transparent"
            title="Undo (Ctrl+Z)"
          >
            ↩
          </button>
          <button
            onClick={handleRedo}
            disabled={redoStack.length === 0}
            className="p-1.5 rounded-lg border border-white/10 bg-[#1A1A1D] hover:bg-white/10 text-xs text-white transition disabled:opacity-30 disabled:hover:bg-transparent"
            title="Redo (Ctrl+Y)"
          >
            ↪
          </button>

          <div className="h-4 w-px bg-white/10 mx-1" />

          {/* Zoom controls */}
          <div className="flex items-center space-x-1 border border-white/10 rounded-lg px-2 py-1 bg-[#1A1A1D]">
            <button
              onClick={() => setZoomLevel((z) => Math.max(60, z - 10))}
              className="text-[#A1A1AA] hover:text-white font-bold text-xs"
            >
              -
            </button>
            <span className="text-[10px] font-mono w-9 text-center text-white">{zoomLevel}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(180, z + 10))}
              className="text-[#A1A1AA] hover:text-white font-bold text-xs"
            >
              +
            </button>
          </div>
        </div>

        {/* Right: Save Status, Actions, Export */}
        <div className="flex items-center space-x-2">
          {/* Save Status indicator */}
          <div className="flex items-center space-x-1.5 text-[11px] font-mono mr-1">
            <span
              className={`w-2 h-2 rounded-full ${
                saveStatus === "saved"
                  ? "bg-emerald-400"
                  : saveStatus === "saving"
                  ? "bg-sky-400 animate-ping"
                  : "bg-amber-400"
              }`}
            />
            <span className="text-[#A1A1AA]">
              {saveStatus === "saved" ? "Saved" : saveStatus === "saving" ? "Saving..." : "Unsaved"}
            </span>
          </div>

          <button
            onClick={handleSaveDesign}
            className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-black font-semibold text-xs transition shadow-sm"
          >
            💾 Save Design
          </button>

          <button
            onClick={() => setShowSavedModal(true)}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-white transition"
          >
            📂 Open...
          </button>

          <button
            onClick={handleDownloadSvg}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-white transition"
            title="Download crisp vector SVG"
          >
            🖼️ SVG
          </button>

          {onApplySpec && (
            <button
              onClick={() => onApplySpec(spec)}
              className="px-3.5 py-1.5 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-black font-bold text-xs transition shadow-md"
            >
              ✓ Use in Studio
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 text-[#A1A1AA] hover:text-white transition"
              title="Close Editor"
            >
              ✕
            </button>
          )}
        </div>
      </header>

      {/* ============================================================== */}
      {/* 2. MAIN 3-PANE SPLIT: Left Sidebar, Canvas Stage, Right Panel */}
      {/* ============================================================== */}
      <div className="flex flex-1 overflow-hidden">
        {/* ============================================================ */}
        {/* A. LEFT SIDEBAR (Layers, Add, Assets, Presets)               */}
        {/* ============================================================ */}
        {sidebarCollapsed ? (
          /* SLIM VERTICAL ICON DOCK (Canva / Figma inspired) */
          <aside className="w-14 bg-[#111113] border-r border-white/10 flex flex-col items-center py-3 space-y-2 shrink-0 z-10 transition-all duration-200">
            <button
              onClick={() => setSidebarCollapsed(false)}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-cyan-400 hover:text-white transition mb-2"
              title="Expand Tools Sidebar"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              </svg>
            </button>

            {[
              { key: "layers", label: "Layers", icon: "📑" },
              { key: "add", label: "Add", icon: "➕" },
              { key: "assets", label: "Assets", icon: "🖼️" },
              { key: "presets", label: "Combos", icon: "✨" },
              { key: "refine", label: "AI", icon: "🪄" },
              { key: "json", label: "JSON", icon: "{ }" },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => {
                  setSidebarTab(tab.key as any);
                  setSidebarCollapsed(false);
                }}
                className={`w-10 h-10 rounded-xl flex flex-col items-center justify-center transition group relative ${
                  sidebarTab === tab.key
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                    : "text-[#A1A1AA] hover:bg-white/10 hover:text-white"
                }`}
                title={tab.label}
              >
                <span className="text-base">{tab.icon}</span>
                <span className="text-[9px] font-medium scale-90 -mt-0.5">{tab.label.slice(0, 4)}</span>
              </button>
            ))}
          </aside>
        ) : (
          /* FULL EXPANDED SIDEBAR */
          <aside className="w-80 bg-[#161618] border-r border-white/10 flex flex-col h-full overflow-hidden shrink-0 transition-all duration-200">
            {/* Sidebar Tabs */}
            <nav className="flex items-center border-b border-white/10 bg-[#0E0E10] text-[11px] font-semibold shrink-0">
              <div className="flex flex-1">
                {[
                  { key: "layers", label: "Layers", icon: "📑" },
                  { key: "add", label: "Add", icon: "➕" },
                  { key: "assets", label: "Assets", icon: "🖼️" },
                  { key: "presets", label: "Combos", icon: "✨" },
                  { key: "refine", label: "AI", icon: "🪄" },
                  { key: "json", label: "JSON", icon: "{ }" },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setSidebarTab(tab.key as any)}
                    className={`flex-1 py-2.5 text-center transition border-b-2 font-medium flex items-center justify-center space-x-1 ${
                      sidebarTab === tab.key
                        ? "border-cyan-400 text-white bg-white/5 font-bold"
                        : "border-transparent text-[#A1A1AA] hover:text-white"
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span className="hidden sm:inline">{tab.label}</span>
                  </button>
                ))}
              </div>
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="px-2.5 py-2 text-[#696970] hover:text-white hover:bg-white/5 transition"
                title="Collapse Sidebar"
              >
                ◀
              </button>
            </nav>

            {/* Tab 1: LAYERS PANEL */}
            {sidebarTab === "layers" && (
              <div className="flex-1 overflow-y-auto p-3 flex flex-col space-y-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA]">
                    Elements ({spec.elements.length})
                  </span>
                  {selectedElementId ? (
                    <button
                      onClick={() => setSelectedElementId(null)}
                      className="text-[10px] text-cyan-400 hover:underline font-semibold"
                    >
                      Deselect (Esc)
                    </button>
                  ) : (
                    <span className="text-[10px] text-[#696970]">Top to bottom</span>
                  )}
                </div>

                <input
                  type="text"
                  placeholder="Search layers..."
                  value={layerSearch}
                  onChange={(e) => setLayerSearch(e.target.value)}
                  className="w-full bg-[#1A1A1D] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-[#696970] focus:outline-none focus:border-cyan-400 mb-2"
                />

                <div className="space-y-1.5 flex-1 overflow-y-auto">
                  {[...spec.elements]
                    .reverse()
                    .filter((el) => {
                      if (!layerSearch.trim()) return true;
                      const q = layerSearch.toLowerCase();
                      return (
                        (el.id && el.id.toLowerCase().includes(q)) ||
                        (el.type && el.type.toLowerCase().includes(q)) ||
                        (el.field && el.field.toLowerCase().includes(q))
                      );
                    })
                    .map((el) => {
                      const isSelected = Boolean(selectedElementId && el.id && selectedElementId === el.id);
                    const isBg = el.id === "bg_image" || el.is_background;
                    const isDecal = el.type === "image" || el.type === "svg_asset";
                    const isMandatoryLogo =
                      (el.type === "logo" && (el.src === "acm_nitsurat" || el.src === "svnit")) ||
                      el.id === "logo_acm" ||
                      el.id === "logo_svnit";

                    const typeIcon =
                      isBg
                        ? "🌌"
                        : isDecal
                        ? "🎨"
                        : el.type === "text"
                        ? "🔤"
                        : el.type === "photo"
                        ? "🖼️"
                        : el.type === "logo"
                        ? "🏷️"
                        : el.type === "rect"
                        ? "⬛"
                        : el.type === "circle"
                        ? "🔘"
                        : el.type === "line"
                        ? "➖"
                        : el.type === "role_badge"
                        ? "🪪"
                        : el.type === "qr"
                        ? "📱"
                        : "📦";

                    const displayName = isBg
                      ? "Card Background Image"
                      : isDecal
                      ? (el.id.startsWith("decal_") ? `Decal: ${el.src?.split("/").pop()?.replace(/\.[^/.]+$/, "") || el.id}` : el.id)
                      : el.id;

                    const displaySub = isBg
                      ? `Opacity: ${Math.round((el.opacity ?? 0.35) * 100)}% • Full Card`
                      : isDecal
                      ? `Decal Graphic • ${Math.round(el.w || 14)}×${Math.round(el.h || 14)}mm`
                      : `${el.type} ${el.field ? `• {{${el.field}}}` : el.value ? `• "${el.value.slice(0, 14)}"` : ""}`;

                    return (
                      <div
                        key={el.id}
                        onClick={() => setSelectedElementId((prev) => (prev === el.id ? null : el.id))}
                        className={`group px-2.5 py-2 rounded-xl border text-xs flex items-center justify-between cursor-pointer transition ${
                          isSelected
                            ? "bg-cyan-950/40 border-cyan-400 text-white shadow-sm"
                            : "bg-[#1C1C1F] border-white/5 text-[#A1A1AA] hover:border-white/20 hover:text-white"
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <span className="text-sm">{typeIcon}</span>
                          <div className="truncate">
                            <span className="font-semibold text-white block truncate">{displayName}</span>
                            <span className="text-[10px] text-[#A1A1AA] truncate block">{displaySub}</span>
                          </div>
                        </div>

                        {/* Layer Actions */}
                        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              reorderElement(el.id, "up");
                            }}
                            className="p-1 hover:bg-white/10 rounded text-[#A1A1AA] hover:text-white text-[10px]"
                            title="Bring forward"
                          >
                            ▲
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              reorderElement(el.id, "down");
                            }}
                            className="p-1 hover:bg-white/10 rounded text-[#A1A1AA] hover:text-white text-[10px]"
                            title="Send backward"
                          >
                            ▼
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              duplicateElement(el.id);
                            }}
                            className="p-1 hover:bg-white/10 rounded text-[#A1A1AA] hover:text-white text-[10px]"
                            title="Duplicate"
                          >
                            ⧉
                          </button>
                          {!isMandatoryLogo && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteElement(el.id);
                              }}
                              className="p-1 hover:bg-rose-900/50 rounded text-rose-400 text-[10px]"
                              title="Delete"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Tab 2: ADD ELEMENTS PANEL */}
          {sidebarTab === "add" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Typography & Data Fields
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() =>
                      addElement("text", {
                        field: "name",
                        x: 7,
                        y: 45,
                        w: 46,
                        font: "heading",
                        color: "text",
                        max_font: 14,
                        min_font: 8,
                        max_lines: 2,
                        align: "center",
                        bold: true,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">🔤</span>
                    <span className="font-semibold text-xs text-white block mt-1">Attendee Name</span>
                    <span className="text-[10px] text-[#A1A1AA] block font-mono">{"{{name}}"}</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("text", {
                        field: "team",
                        x: 7,
                        y: 55,
                        w: 46,
                        font: "body",
                        color: "accent",
                        max_font: 9,
                        min_font: 7,
                        max_lines: 1,
                        align: "center",
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">👥</span>
                    <span className="font-semibold text-xs text-white block mt-1">Team Name</span>
                    <span className="text-[10px] text-[#A1A1AA] block font-mono">{"{{team}}"}</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("text", {
                        field: "id",
                        x: 7,
                        y: 62,
                        w: 46,
                        font: "body",
                        color: "text",
                        max_font: 8,
                        min_font: 6,
                        max_lines: 1,
                        align: "center",
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">🏷️</span>
                    <span className="font-semibold text-xs text-white block mt-1">Attendee ID</span>
                    <span className="text-[10px] text-[#A1A1AA] block font-mono">{"{{id}}"}</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("text", {
                        value: "CUSTOM TITLE",
                        x: 7,
                        y: 12,
                        w: 46,
                        font: "heading",
                        color: "text",
                        max_font: 11,
                        min_font: 7,
                        max_lines: 1,
                        align: "center",
                        bold: true,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">✍️</span>
                    <span className="font-semibold text-xs text-white block mt-1">Static Text</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Fixed label</span>
                  </button>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Badges & Credentials
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() =>
                      addElement("role_badge", {
                        field: "role",
                        x: 15,
                        y: 76,
                        w: 30,
                        h: 6,
                        text_color: "background",
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">🪪</span>
                    <span className="font-semibold text-xs text-white block mt-1">Role Badge</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Color-blind cue</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("qr", {
                        field: "qr_url",
                        x: 23,
                        y: 70,
                        w: 14,
                        h: 14,
                        fg: "text",
                        bg: "background",
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">📱</span>
                    <span className="font-semibold text-xs text-white block mt-1">QR Code</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Vector check-in</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("photo", {
                        field: "photo",
                        x: 16,
                        y: 28,
                        w: 28,
                        h: 32,
                        shape: "rounded",
                        radius: 3,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">🖼️</span>
                    <span className="font-semibold text-xs text-white block mt-1">Photo Frame</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Face crop clip</span>
                  </button>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Geometric Primitives
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() =>
                      addElement("rect", {
                        x: 0,
                        y: 0,
                        w: 60,
                        h: 22,
                        fill: "primary",
                        stroke: "none",
                        stroke_width: 0,
                        radius: 0,
                        opacity: 1,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">⬛</span>
                    <span className="font-semibold text-xs text-white block mt-1">Header Banner</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Rect block</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("line", {
                        x1: 7,
                        y1: 50,
                        x2: 53,
                        y2: 50,
                        stroke: "accent",
                        stroke_width: 0.4,
                        opacity: 1,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">➖</span>
                    <span className="font-semibold text-xs text-white block mt-1">Divider Line</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Hairline rule</span>
                  </button>

                  <button
                    onClick={() =>
                      addElement("circle", {
                        cx: 30,
                        cy: 35,
                        r: 10,
                        fill: "secondary",
                        stroke: "accent",
                        stroke_width: 0.5,
                        opacity: 1,
                      })
                    }
                    className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                  >
                    <span className="text-sm block">🔘</span>
                    <span className="font-semibold text-xs text-white block mt-1">Circle Accent</span>
                    <span className="text-[10px] text-[#A1A1AA] block">Vector circle</span>
                  </button>
                </div>
              </div>

              {/* Images, Decals & Custom Graphics */}
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Images, Decals & Graphics
                </span>

                {/* Upload Custom Image Button */}
                <button
                  onClick={() => decalUploadInputRef.current?.click()}
                  disabled={isUploadingAsset}
                  className="w-full mb-2 p-3 rounded-xl border border-dashed border-cyan-500/40 bg-cyan-950/10 hover:bg-cyan-950/20 hover:border-cyan-400 text-left transition group flex items-center space-x-3"
                >
                  <span className="text-xl group-hover:scale-110 transition-transform">📤</span>
                  <div>
                    <span className="font-semibold text-xs text-white block group-hover:text-cyan-300 transition">
                      Upload Custom Image / Decal
                    </span>
                    <span className="text-[10px] text-[#A1A1AA] block">
                      Insert photo, sponsor logo, or sticker anywhere on card
                    </span>
                  </div>
                </button>

                {/* Preset Decals Grid */}
                <div className="grid grid-cols-2 gap-2">
                  {DECAL_PRESETS.map((decal) => (
                    <button
                      key={decal.id}
                      onClick={() => addDecalPreset(decal.id)}
                      className="p-2.5 rounded-xl border border-white/10 bg-[#1C1C1F] hover:border-cyan-400 hover:bg-cyan-950/20 text-left transition"
                    >
                      <span className="text-sm block">{decal.icon}</span>
                      <span className="font-semibold text-xs text-white block mt-1">
                        {decal.label}
                      </span>
                      <span className="text-[10px] text-[#A1A1AA] block">
                        {decal.defaultW}×{decal.defaultH}mm decal
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: ASSETS & BACKGROUND */}
          {sidebarTab === "assets" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-5">
              {/* Card Background Image Section */}
              <div className="space-y-3 bg-[#1C1C1F] p-3.5 rounded-xl border border-white/10">
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-base">🌌</span>
                    <span className="text-xs font-bold uppercase tracking-wider text-white">
                      Card Background Image
                    </span>
                  </div>
                  {activeBg ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                      <span>Active</span>
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/5 text-[#A1A1AA]">
                      Solid Color Only
                    </span>
                  )}
                </div>

                {/* Upload or Active Background Control Card */}
                {activeBg ? (
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3 p-2.5 rounded-lg bg-[#121214] border border-white/10">
                      <div className="w-12 h-16 rounded bg-[#1C1C1F] border border-white/10 overflow-hidden relative shrink-0">
                        <img
                          src={getElementImageSrc(activeBg, spec)}
                          alt="Background"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-bold text-white block truncate">
                          {activeBg.src?.split("/").pop() || "Custom Image"}
                        </span>
                        <span className="text-[10px] text-cyan-400 font-mono block">
                          Opacity: {Math.round((activeBg.opacity ?? 0.35) * 100)}%
                        </span>
                        <div className="flex items-center space-x-2 mt-2">
                          <button
                            onClick={() => bgUploadInputRef.current?.click()}
                            className="px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-white text-[10px] font-medium transition"
                          >
                            Replace
                          </button>
                          <button
                            onClick={removeBackgroundImage}
                            className="px-2 py-1 rounded bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 text-[10px] font-medium transition"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Opacity Slider */}
                    <div>
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="text-[#A1A1AA]">Background Opacity</span>
                        <span className="font-mono text-cyan-400 font-bold">
                          {Math.round((activeBg.opacity ?? 0.35) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="5"
                        max="100"
                        value={Math.round((activeBg.opacity ?? 0.35) * 100)}
                        onChange={(e) => updateBackgroundOpacity(parseInt(e.target.value, 10) / 100)}
                        className="w-full accent-cyan-400"
                      />
                    </div>

                    {/* Fit Mode */}
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => setBackgroundFitMode("cover")}
                        className={`py-1 text-[11px] rounded font-medium border ${
                          activeBg.fit !== "contain"
                            ? "bg-cyan-950/40 text-cyan-300 border-cyan-500/40"
                            : "bg-[#121214] text-[#A1A1AA] border-white/5"
                        }`}
                      >
                        Cover (Bleed)
                      </button>
                      <button
                        onClick={() => setBackgroundFitMode("contain")}
                        className={`py-1 text-[11px] rounded font-medium border ${
                          activeBg.fit === "contain"
                            ? "bg-cyan-950/40 text-cyan-300 border-cyan-500/40"
                            : "bg-[#121214] text-[#A1A1AA] border-white/5"
                        }`}
                      >
                        Contain
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => bgUploadInputRef.current?.click()}
                    disabled={isUploadingAsset}
                    className="w-full p-4 rounded-xl border border-dashed border-cyan-500/40 bg-cyan-950/10 hover:bg-cyan-950/20 hover:border-cyan-400 text-center transition group flex flex-col items-center justify-center space-y-1.5"
                  >
                    <span className="text-2xl group-hover:scale-110 transition-transform">📤</span>
                    <span className="text-xs font-bold text-white group-hover:text-cyan-300 transition">
                      {isUploadingAsset ? "Uploading..." : "Upload Background Image"}
                    </span>
                    <span className="text-[10px] text-[#A1A1AA]">
                      PNG, JPG, SVG or WebP • Full card bleed
                    </span>
                  </button>
                )}

                {/* Preset Pattern Cards Grid */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2 mt-3">
                    Curated Background Patterns
                  </span>
                  <div className="grid grid-cols-1 gap-2">
                    {BACKGROUND_PRESETS.map((preset) => (
                      <div
                        key={preset.id}
                        onClick={() => applyBackgroundPreset(preset.id)}
                        className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                          activeBg && activeBg.src?.includes(preset.id)
                            ? "bg-cyan-950/40 border-cyan-400 text-white"
                            : "bg-[#121214] border-white/5 text-[#A1A1AA] hover:border-white/20 hover:text-white"
                        }`}
                      >
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <span className="text-lg">{preset.icon}</span>
                          <div className="min-w-0">
                            <span className="text-xs font-semibold text-white block truncate">
                              {preset.label}
                            </span>
                            <span className="text-[10px] text-[#A1A1AA] block truncate">
                              {preset.description}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            applyBackgroundPreset(preset.id);
                          }}
                          className="px-2 py-1 rounded bg-white/10 hover:bg-cyan-500 hover:text-black text-white text-[10px] font-semibold transition shrink-0 ml-2"
                        >
                          Apply
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Institutional Crests (Required)
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 bg-[#1C1C1F] border border-white/10 rounded-xl flex flex-col items-center space-y-2">
                    <img src="/logos/acm_nitsurat.svg" alt="ACM" className="w-10 h-10 object-contain" />
                    <span className="text-[11px] font-semibold text-white">ACM NIT Surat</span>
                    <span className="text-[9px] text-emerald-400 font-mono">Present on card</span>
                  </div>
                  <div className="p-3 bg-[#1C1C1F] border border-white/10 rounded-xl flex flex-col items-center space-y-2">
                    <img src="/logos/svnit.svg" alt="SVNIT" className="w-10 h-10 object-contain" />
                    <span className="text-[11px] font-semibold text-white">SVNIT Crest</span>
                    <span className="text-[9px] text-emerald-400 font-mono">Present on card</span>
                  </div>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2 flex items-center justify-between">
                  <span>Card Background Color</span>
                  <span className="text-[9px] font-mono text-cyan-400">
                    {isTransparentBackground ? "Transparent" : spec.theme.colors.background}
                  </span>
                </span>
                <div className="p-3 bg-[#1C1C1F] border border-white/10 rounded-xl space-y-3">
                  {/* Mode switcher: Solid Color vs Transparent */}
                  <div className="grid grid-cols-2 gap-1.5 p-1 bg-[#121214] rounded-lg border border-white/5">
                    <button
                      type="button"
                      onClick={() => {
                        const fallback =
                          spec.theme.colors.background &&
                          spec.theme.colors.background !== "none" &&
                          spec.theme.colors.background !== "transparent" &&
                          spec.theme.colors.background !== "#00000000"
                            ? spec.theme.colors.background
                            : "#0B1220";
                        setCardBackgroundColor(fallback);
                      }}
                      className={`py-1 text-xs font-medium rounded-md transition ${
                        !isTransparentBackground
                          ? "bg-cyan-500 text-black shadow-sm font-semibold"
                          : "text-[#A1A1AA] hover:text-white"
                      }`}
                    >
                      🎨 Solid Color
                    </button>
                    <button
                      type="button"
                      onClick={() => setCardBackgroundColor("transparent")}
                      className={`py-1 text-xs font-medium rounded-md transition ${
                        isTransparentBackground
                          ? "bg-cyan-500 text-black shadow-sm font-semibold"
                          : "text-[#A1A1AA] hover:text-white"
                      }`}
                    >
                      🏁 Transparent
                    </button>
                  </div>

                  {!isTransparentBackground ? (
                    <>
                      {/* Color Picker & Hex Input */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[#A1A1AA]">Background Color:</span>
                        <div className="flex items-center space-x-2">
                          <input
                            type="color"
                            value={
                              spec.theme.colors.background.startsWith("#") && spec.theme.colors.background.length === 7
                                ? spec.theme.colors.background
                                : "#0B1220"
                            }
                            onChange={(e) => setCardBackgroundColor(e.target.value)}
                            className="w-7 h-7 rounded border border-white/20 bg-transparent cursor-pointer"
                          />
                          <input
                            type="text"
                            value={spec.theme.colors.background}
                            onChange={(e) => setCardBackgroundColor(e.target.value)}
                            className="w-20 font-mono text-xs bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                          />
                        </div>
                      </div>

                      {/* Quick Color Swatches */}
                      <div>
                        <span className="text-[10px] text-[#71717A] block mb-1.5">Quick Swatches</span>
                        <div className="grid grid-cols-6 gap-1.5">
                          {[
                            { name: "Dark Tech", hex: "#0B1220" },
                            { name: "Slate", hex: "#1E293B" },
                            { name: "Crimson", hex: "#731717" },
                            { name: "Midnight", hex: "#0F172A" },
                            { name: "Indigo", hex: "#312E81" },
                            { name: "White", hex: "#FFFFFF" },
                          ].map((swatch) => (
                            <button
                              key={swatch.hex}
                              type="button"
                              title={swatch.name}
                              onClick={() => setCardBackgroundColor(swatch.hex)}
                              className={`w-full h-6 rounded-md border transition ${
                                spec.theme.colors.background.toUpperCase() === swatch.hex.toUpperCase()
                                  ? "border-cyan-400 scale-105 shadow-md"
                                  : "border-white/10 hover:border-white/40"
                              }`}
                              style={{ backgroundColor: swatch.hex }}
                            />
                          ))}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="p-2.5 rounded-lg border border-dashed border-white/15 bg-white/[0.02] text-center">
                      <p className="text-[11px] text-[#A1A1AA]">
                        Card has a transparent base. Any decals or background patterns will sit on an alpha background.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block mb-2">
                  Sample Attendee Photos
                </span>
                <div className="grid grid-cols-4 gap-2">
                  {DEFAULT_PERSONAS.map((p, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedPersonaIndex(idx)}
                      className={`p-1.5 rounded-xl border text-center cursor-pointer transition ${
                        selectedPersonaIndex === idx ? "border-cyan-400 bg-cyan-950/30" : "border-white/10 bg-[#1C1C1F]"
                      }`}
                    >
                      <div className="w-full aspect-square rounded-lg bg-white/10 overflow-hidden mb-1">
                        <img src={`/${p.photo}`} alt={p.name} className="w-full h-full object-cover" />
                      </div>
                      <span className="text-[9px] truncate block text-[#A1A1AA]">{p.name.split(" ")[0]}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: 9 COMBOS MATRIX */}
          {sidebarTab === "presets" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                9 Layout × Theme Combinations
              </span>
              <p className="text-[11px] text-[#A1A1AA]">
                Click any cell to immediately switch layout architecture and color scheme simultaneously.
              </p>

              <div className="space-y-3">
                {Object.keys(LAYOUT_PRESETS).map((lKey) => {
                  const layout = LAYOUT_PRESETS[lKey];
                  return (
                    <div key={lKey} className="bg-[#1C1C1F] border border-white/10 rounded-xl p-3 space-y-2">
                      <div className="flex items-center justify-between border-b border-white/10 pb-1.5">
                        <span className="font-bold text-xs text-white flex items-center space-x-1.5">
                          <span>{layout.icon}</span>
                          <span>{layout.label}</span>
                        </span>
                        <span className="text-[10px] font-mono text-[#A1A1AA] capitalize">{lKey}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5">
                        {Object.keys(THEME_PRESETS).map((tKey) => {
                          const theme = THEME_PRESETS[tKey];
                          const isActive = spec.layout_name === lKey && spec.theme_name === tKey;
                          return (
                            <button
                              key={tKey}
                              onClick={() => {
                                recordChange({
                                  ...spec,
                                  layout_name: lKey,
                                  theme_name: tKey,
                                  elements: JSON.parse(JSON.stringify(layout.elements)),
                                  theme: {
                                    ...spec.theme,
                                    name: tKey,
                                    colors: { ...theme.colors },
                                    role_colors: { ...theme.role_colors },
                                  },
                                });
                              }}
                              className={`p-2 rounded-lg border text-center transition flex flex-col items-center justify-center space-y-1 ${
                                isActive
                                  ? "bg-cyan-950/60 border-cyan-400 text-white ring-1 ring-cyan-400"
                                  : "bg-[#141416] border-white/5 text-[#A1A1AA] hover:border-white/20 hover:text-white"
                              }`}
                            >
                              <div className="flex items-center space-x-1">
                                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: theme.colors.primary }} />
                                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: theme.colors.accent }} />
                              </div>
                              <span className="text-[10px] font-medium truncate">{theme.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 5: AI REFINE */}
          {sidebarTab === "refine" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                Natural Language Refinement
              </span>
              <p className="text-[11px] text-[#A1A1AA]">
                Type plain English instructions to adjust typography, colors, or positioning via validated JSON patches.
              </p>

              <div className="space-y-1.5">
                <span className="text-[10px] font-semibold text-[#A1A1AA] uppercase">Quick Suggestions</span>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    "Make photo circular",
                    "Center the attendee name",
                    "Make name bigger",
                    "Switch to Dark Tech theme",
                    "Set accent color to #F59E0B",
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setNlPrompt(prompt);
                        handleNlRefine(undefined, prompt);
                      }}
                      className="px-2 py-1 text-[11px] rounded-lg border border-white/10 bg-[#1C1C1F] hover:bg-white/10 text-white transition"
                    >
                      + {prompt}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleNlRefine} className="space-y-3">
                <textarea
                  rows={3}
                  value={nlPrompt}
                  onChange={(e) => setNlPrompt(e.target.value)}
                  placeholder="e.g. Move QR code to bottom-right, make name bold and 15pt..."
                  className="w-full bg-[#1A1A1D] border border-white/15 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-cyan-400 placeholder-[#696970] resize-none"
                />
                <button
                  type="submit"
                  disabled={nlLoading || !nlPrompt.trim()}
                  className="w-full py-2 bg-white hover:bg-slate-100 text-black font-semibold rounded-lg text-xs transition disabled:opacity-40"
                >
                  {nlLoading ? "Refining Design..." : "✨ Apply AI Refinement"}
                </button>
              </form>

              {nlMessage && (
                <div
                  className={`p-3 rounded-xl border text-xs ${
                    nlMessage.type === "success"
                      ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
                      : "bg-rose-950/40 border-rose-500/30 text-rose-300"
                  }`}
                >
                  {nlMessage.text}
                </div>
              )}
            </div>
          )}

          {/* Tab 6: JSON SPEC */}
          {sidebarTab === "json" && (
            <div className="flex-1 overflow-y-auto p-4 flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-[#A1A1AA]">DesignSpec v1.0 JSON</span>
                <button onClick={handleDownloadJson} className="text-[10px] text-cyan-400 hover:underline">
                  Download .json
                </button>
              </div>
              <textarea
                value={jsonInput}
                onChange={(e) => {
                  setJsonInput(e.target.value);
                  try {
                    const parsed = JSON.parse(e.target.value);
                    recordChange(parsed);
                    setJsonError(null);
                  } catch (err: any) {
                    setJsonError(err.message);
                  }
                }}
                className="w-full flex-1 min-h-[400px] bg-[#0E0E10] font-mono text-[11px] text-cyan-300 p-3 rounded-xl border border-white/10 focus:outline-none focus:border-cyan-400 resize-none leading-relaxed"
                spellCheck={false}
              />
              {jsonError ? (
                <p className="text-[10px] text-rose-400 font-mono">⚠️ Invalid: {jsonError}</p>
              ) : (
                <p className="text-[10px] text-emerald-400 font-mono">✓ Valid DesignSpec schema</p>
              )}
            </div>
          )}
        </aside>
        )}

        {/* ============================================================ */}
        {/* B. CENTER ARTBOARD & INTERACTIVE CANVAS - Flex Auto-fit      */}
        {/* ============================================================ */}
        <main className="flex-1 min-w-0 bg-[#0B0B0D] flex flex-col h-full overflow-hidden relative">
          {/* Top Persona Switcher Bar */}
          <div className="bg-[#0E0E10] border-b border-white/10 px-4 py-2 flex items-center justify-between gap-2 shrink-0 z-10">
            <div className="flex items-center space-x-1.5 overflow-x-auto py-0.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] mr-1">Role:</span>
              {personas.map((p, idx) => {
                const isActive = selectedPersonaIndex === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedPersonaIndex(idx)}
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition flex items-center space-x-1.5 ${
                      isActive
                        ? "bg-white text-black shadow-sm"
                        : "bg-white/5 text-[#A1A1AA] hover:text-white border border-white/10"
                    }`}
                  >
                    <span>{p.name.split(" ")[0]}</span>
                    <span
                      className={`text-[9px] uppercase px-1 rounded font-mono ${
                        p.role === "organizer"
                          ? "bg-amber-950/40 text-amber-300"
                          : p.role === "mentor"
                          ? "bg-emerald-950/40 text-emerald-300"
                          : "bg-sky-950/40 text-sky-300"
                      }`}
                    >
                      {p.role || "part"}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center space-x-2 text-xs">
              <label className="flex items-center space-x-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showDebugGuides}
                  onChange={(e) => setShowDebugGuides(e.target.checked)}
                  className="rounded border-white/20 bg-[#121214] text-cyan-400 focus:ring-0 cursor-pointer"
                />
                <span className="text-[11px] font-medium text-[#A1A1AA]">Print Guides</span>
              </label>
            </div>
          </div>

          {/* Canvas Viewport Stage */}
          <div
            className="flex-1 overflow-auto p-6 flex items-center justify-center relative bg-[#09090B]"
            onClick={() => setSelectedElementId(null)}
          >
            {loadingSvg && !svgContent ? (
              <div className="text-center space-y-3">
                <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs text-[#A1A1AA] font-mono">Compiling card SVG...</p>
              </div>
            ) : (
              <div
                className="relative transition-transform duration-100 shadow-[0_25px_60px_rgba(0,0,0,0.95)] rounded-sm overflow-hidden select-none"
                style={{
                  width: `${(spec.page.width_mm + 2 * spec.page.bleed_mm) * 6}px`,
                  height: `${(spec.page.height_mm + 2 * spec.page.bleed_mm) * 6}px`,
                  transform: `scale(${zoomLevel / 100})`,
                  transformOrigin: "center center",
                  backgroundImage: isTransparentBackground
                    ? "linear-gradient(45deg, #18181b 25%, transparent 25%), linear-gradient(-45deg, #18181b 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #18181b 75%), linear-gradient(-45deg, transparent 75%, #18181b 75%)"
                    : undefined,
                  backgroundSize: isTransparentBackground ? "16px 16px" : undefined,
                  backgroundPosition: isTransparentBackground ? "0 0, 0 8px, 8px -8px, -8px 0px" : undefined,
                  backgroundColor: isTransparentBackground ? "#27272a" : undefined,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* 1. Underlying Real Vector SVG from Backend - scaled to 100% of container */}
                <div
                  className="w-full h-full pointer-events-none [&>svg]:w-full [&>svg]:h-full [&>svg]:block"
                  dangerouslySetInnerHTML={{ __html: responsiveSvg }}
                />

                {/* 2. Interactive SVG Overlay for Selection, Drag & Resize */}
                <svg
                  ref={canvasSvgRef}
                  viewBox={`0 0 ${spec.page.width_mm + 2 * spec.page.bleed_mm} ${
                    spec.page.height_mm + 2 * spec.page.bleed_mm
                  }`}
                  className="absolute inset-0 w-full h-full overflow-visible"
                  onPointerMove={handlePointerMove}
                  onPointerUp={handlePointerUp}
                >
                  {/* Magnetic snap lines visualization */}
                  {snapLines.x !== undefined && (
                    <line
                      x1={snapLines.x}
                      y1={0}
                      x2={snapLines.x}
                      y2={spec.page.height_mm + 2 * spec.page.bleed_mm}
                      stroke="#22D3EE"
                      strokeWidth={0.3}
                      strokeDasharray="1 1"
                    />
                  )}
                  {snapLines.y !== undefined && (
                    <line
                      x1={0}
                      y1={snapLines.y}
                      x2={spec.page.width_mm + 2 * spec.page.bleed_mm}
                      y2={snapLines.y}
                      stroke="#22D3EE"
                      strokeWidth={0.3}
                      strokeDasharray="1 1"
                    />
                  )}

                  {/* Interactive element hitboxes & outlines */}
                  {spec.elements.map((el) => {
                    const bounds = getElementBounds(el);
                    const isSelected = Boolean(selectedElementId && el.id && selectedElementId === el.id);

                    return (
                      <g key={el.id} className="cursor-move">
                        {/* Invisible hover hitbox */}
                        <rect
                          x={bounds.x}
                          y={bounds.y}
                          width={bounds.w}
                          height={bounds.h}
                          fill="transparent"
                          className="hover:stroke-cyan-400/50 hover:stroke-[0.35]"
                          onPointerDown={(e) => handlePointerDown(e, el.id, "drag")}
                        />

                        {/* Active Selection Bounding Box - ONLY for the single selected element */}
                        {isSelected && (
                          <g>
                            <rect
                              x={bounds.x}
                              y={bounds.y}
                              width={bounds.w}
                              height={bounds.h}
                              fill="rgba(6, 182, 212, 0.08)"
                              stroke="#06B6D4"
                              strokeWidth={0.4}
                              strokeDasharray="1.2 0.8"
                              className="pointer-events-none"
                            />

                            {/* Coordinate HUD Pill */}
                            <g className="pointer-events-none select-none">
                              <rect
                                x={bounds.x}
                                y={Math.max(0.5, bounds.y - 3.4)}
                                width={Math.min(Math.max(bounds.w, 24), 38)}
                                height={2.8}
                                rx={0.6}
                                fill="#06B6D4"
                              />
                              <text
                                x={bounds.x + 1.2}
                                y={Math.max(2.4, bounds.y - 1.4)}
                                fontSize="1.8"
                                fill="#000000"
                                fontFamily="monospace"
                                fontWeight="bold"
                              >
                                {bounds.x.toFixed(1)}, {bounds.y.toFixed(1)} mm ({bounds.w.toFixed(1)}×{bounds.h.toFixed(1)})
                              </text>
                            </g>

                            {/* 4 Corner Resize Handles */}
                            {[
                              { id: "nw", x: bounds.x, y: bounds.y, cursor: "nwse-resize" },
                              { id: "ne", x: bounds.x + bounds.w, y: bounds.y, cursor: "nesw-resize" },
                              { id: "se", x: bounds.x + bounds.w, y: bounds.y + bounds.h, cursor: "nwse-resize" },
                              { id: "sw", x: bounds.x, y: bounds.y + bounds.h, cursor: "nesw-resize" },
                              { id: "e", x: bounds.x + bounds.w, y: bounds.y + bounds.h / 2, cursor: "ew-resize" },
                              { id: "s", x: bounds.x + bounds.w / 2, y: bounds.y + bounds.h, cursor: "ns-resize" },
                            ].map((h) => (
                              <rect
                                key={h.id}
                                x={h.x - 0.9}
                                y={h.y - 0.9}
                                width={1.8}
                                height={1.8}
                                fill="#FFFFFF"
                                stroke="#06B6D4"
                                strokeWidth={0.3}
                                style={{ cursor: h.cursor }}
                                onPointerDown={(e) => handlePointerDown(e, el.id, "resize", h.id)}
                              />
                            ))}
                          </g>
                        )}
                      </g>
                    );
                  })}
                </svg>
              </div>
            )}
          </div>

          {/* Bottom Diagnostics Strip */}
          <footer className="bg-[#0E0E10] border-t border-white/10 px-5 py-2 flex items-center justify-between text-[11px] text-[#A1A1AA] font-mono shrink-0">
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                <span>Bleed: 3mm</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                <span>Trim: 54×86mm</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                <span>Safe: 4mm</span>
              </span>
            </div>

            <div className="text-[#696970]">
              DPI: 300 • Deterministic Vector SVG Engine
            </div>
          </footer>
        </main>

        {/* ============================================================ */}
        {/* C. RIGHT CONTEXTUAL PROPERTIES PANEL - Dedicated Inspector   */}
        {/* ============================================================ */}
        <aside className="w-80 bg-[#161618] border-l border-white/10 flex flex-col h-full overflow-hidden shrink-0">
          <div className="bg-[#0E0E10] border-b border-white/10 px-4 py-2.5 flex items-center justify-between shrink-0">
            <span className="text-xs font-bold uppercase tracking-wider text-white">
              {selectedElement ? `Element Properties` : `Artboard & Theme`}
            </span>
            {selectedElement && (
              <button
                onClick={() => setSelectedElementId(null)}
                className="text-[10px] text-cyan-400 hover:underline"
              >
                Deselect
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs text-[#A1A1AA]">
            {selectedElement ? (
              /* ELEMENT PROPERTIES */
              <div className="space-y-4">
                {/* Header card with ID & duplicate/delete */}
                <div className="bg-[#1C1C1F] p-3 rounded-xl border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">{selectedElement.id}</span>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-white/10 text-cyan-400">
                      {selectedElement.type}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 pt-1 border-t border-white/10">
                    <button
                      onClick={() => duplicateElement(selectedElement.id)}
                      className="flex-1 py-1 rounded bg-white/5 hover:bg-white/10 text-white text-[11px] font-medium transition"
                    >
                      ⧉ Duplicate
                    </button>
                    {(!["logo_acm", "logo_svnit"].includes(selectedElement.id) &&
                      !(selectedElement.type === "logo" && ["acm_nitsurat", "svnit"].includes(selectedElement.src))) && (
                      <button
                        onClick={() => deleteElement(selectedElement.id)}
                        className="py-1 px-3 rounded bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 text-[11px] font-medium transition"
                      >
                        🗑️ Delete
                      </button>
                    )}
                  </div>
                </div>

                {/* Geometry Section */}
                <div className="space-y-3 bg-[#1C1C1F] p-3 rounded-xl border border-white/10">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                    Position & Dimensions (mm)
                  </span>
                  <div className="grid grid-cols-2 gap-2">
                    {selectedElement.x !== undefined && (
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">X Position</label>
                        <input
                          type="number"
                          step="0.5"
                          value={selectedElement.x}
                          onChange={(e) => updateElement(selectedElement.id, { x: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white font-mono"
                        />
                      </div>
                    )}
                    {selectedElement.y !== undefined && (
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Y Position</label>
                        <input
                          type="number"
                          step="0.5"
                          value={selectedElement.y}
                          onChange={(e) => updateElement(selectedElement.id, { y: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white font-mono"
                        />
                      </div>
                    )}
                    {selectedElement.w !== undefined && (
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Width (W)</label>
                        <input
                          type="number"
                          step="0.5"
                          min="2"
                          value={selectedElement.w}
                          onChange={(e) => updateElement(selectedElement.id, { w: parseFloat(e.target.value) || 2 })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white font-mono"
                        />
                      </div>
                    )}
                    {selectedElement.h !== undefined && (
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Height (H)</label>
                        <input
                          type="number"
                          step="0.5"
                          min="2"
                          value={selectedElement.h}
                          onChange={(e) => updateElement(selectedElement.id, { h: parseFloat(e.target.value) || 2 })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white font-mono"
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Specific Element Type Controls */}
                {selectedElement.type === "text" && (
                  <div className="space-y-3 bg-[#1C1C1F] p-3 rounded-xl border border-white/10">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                      Typography & Data Binding
                    </span>

                    {/* Content: Field or Value */}
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] block mb-1">Text Source</label>
                      <div className="grid grid-cols-2 gap-1 mb-2">
                        <button
                          onClick={() => updateElement(selectedElement.id, { field: "name", value: undefined })}
                          className={`py-1 text-[11px] rounded font-semibold ${
                            selectedElement.field ? "bg-cyan-950 text-cyan-300 border border-cyan-800" : "bg-white/5 text-[#A1A1AA]"
                          }`}
                        >
                          Dynamic Field
                        </button>
                        <button
                          onClick={() => updateElement(selectedElement.id, { field: undefined, value: "Sample Text" })}
                          className={`py-1 text-[11px] rounded font-semibold ${
                            selectedElement.value !== undefined ? "bg-cyan-950 text-cyan-300 border border-cyan-800" : "bg-white/5 text-[#A1A1AA]"
                          }`}
                        >
                          Static Text
                        </button>
                      </div>

                      {selectedElement.field ? (
                        <select
                          value={selectedElement.field}
                          onChange={(e) => updateElement(selectedElement.id, { field: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                        >
                          <option value="name">name (Full Attendee Name)</option>
                          <option value="role">role (Attendee Role)</option>
                          <option value="team">team (Hackathon Team)</option>
                          <option value="id">id (Card Identifier)</option>
                          <option value="email">email (Contact Email)</option>
                          <option value="event_name">event_name (Event Title)</option>
                          <option value="tagline">tagline (Event Tagline)</option>
                          <option value="venue">venue (Venue Location)</option>
                          <option value="dates">dates (Event Dates)</option>
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={selectedElement.value || ""}
                          onChange={(e) => updateElement(selectedElement.id, { value: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                        />
                      )}
                    </div>

                    {/* Font & Weight */}
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Font Role</label>
                        <select
                          value={selectedElement.font || "body"}
                          onChange={(e) => updateElement(selectedElement.id, { font: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white capitalize"
                        >
                          <option value="heading">heading ({spec.theme.fonts.heading})</option>
                          <option value="body">body ({spec.theme.fonts.body})</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Alignment</label>
                        <select
                          value={selectedElement.align || "center"}
                          onChange={(e) => updateElement(selectedElement.id, { align: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white capitalize"
                        >
                          <option value="left">Left</option>
                          <option value="center">Center</option>
                          <option value="right">Right</option>
                        </select>
                      </div>
                    </div>

                    {/* Font Size & Lines */}
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Max Size ({selectedElement.max_font || 14} pt)</label>
                        <input
                          type="range"
                          min="8"
                          max="24"
                          value={selectedElement.max_font || 14}
                          onChange={(e) => updateElement(selectedElement.id, { max_font: parseFloat(e.target.value) })}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Color Token</label>
                        <select
                          value={selectedElement.color || "text"}
                          onChange={(e) => updateElement(selectedElement.id, { color: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white capitalize"
                        >
                          {THEME_TOKENS.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 pt-1">
                      <label className="flex items-center space-x-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={!!selectedElement.bold}
                          onChange={(e) => updateElement(selectedElement.id, { bold: e.target.checked })}
                          className="rounded text-cyan-400"
                        />
                        <span className="text-[11px] text-white">Bold Weight</span>
                      </label>
                      <label className="flex items-center space-x-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={!!selectedElement.uppercase}
                          onChange={(e) => updateElement(selectedElement.id, { uppercase: e.target.checked })}
                          className="rounded text-cyan-400"
                        />
                        <span className="text-[11px] text-white">UPPERCASE</span>
                      </label>
                    </div>
                  </div>
                )}

                {selectedElement.type === "photo" && (
                  <div className="space-y-3 bg-[#1C1C1F] p-3 rounded-xl border border-white/10">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                      Photo Frame & Clipping
                    </span>
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] block mb-1">Frame Shape</label>
                      <select
                        value={selectedElement.shape || "rounded"}
                        onChange={(e) => updateElement(selectedElement.id, { shape: e.target.value })}
                        className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                      >
                        <option value="rounded">Rounded Rectangle</option>
                        <option value="circle">Circular Clip</option>
                        <option value="rect">Sharp Rectangle</option>
                      </select>
                    </div>
                    {selectedElement.shape === "rounded" && (
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">
                          Corner Radius: {selectedElement.radius || 3} mm
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="12"
                          value={selectedElement.radius || 3}
                          onChange={(e) => updateElement(selectedElement.id, { radius: parseFloat(e.target.value) })}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    )}
                  </div>
                )}

                {selectedElement.type === "rect" && (
                  <div className="space-y-3 bg-[#1C1C1F] p-3 rounded-xl border border-white/10">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                      Rectangle Styling
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Fill Token</label>
                        <select
                          value={typeof selectedElement.fill === "string" ? selectedElement.fill : "primary"}
                          onChange={(e) => updateElement(selectedElement.id, { fill: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white capitalize"
                        >
                          {THEME_TOKENS.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-[#A1A1AA] block mb-1">Stroke Token</label>
                        <select
                          value={selectedElement.stroke || "none"}
                          onChange={(e) => updateElement(selectedElement.id, { stroke: e.target.value })}
                          className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white capitalize"
                        >
                          {THEME_TOKENS.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] block mb-1">
                        Corner Radius: {selectedElement.radius || 0} mm
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="15"
                        value={selectedElement.radius || 0}
                        onChange={(e) => updateElement(selectedElement.id, { radius: parseFloat(e.target.value) })}
                        className="w-full accent-cyan-400"
                      />
                    </div>
                  </div>
                )}

                {(selectedElement.type === "image" ||
                  selectedElement.type === "logo" ||
                  selectedElement.type === "svg_asset" ||
                  selectedElement.id === "bg_image") && (
                  <div className="space-y-3 bg-[#1C1C1F] p-3 rounded-xl border border-white/10">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                      Image & Decal Properties
                    </span>

                    {/* Thumbnail preview & Replace button */}
                    <div className="flex items-center space-x-3 p-2 rounded-lg bg-[#121214] border border-white/10">
                      <div className="w-12 h-12 rounded bg-black/40 border border-white/10 overflow-hidden flex items-center justify-center shrink-0">
                        <img
                          src={getElementImageSrc(selectedElement, spec)}
                          alt="Thumbnail"
                          className="w-full h-full object-contain"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-[11px] font-semibold text-white block truncate">
                          {selectedElement.src?.split("/").pop() || "Image Graphic"}
                        </span>
                        <button
                          onClick={() => replaceImageInputRef.current?.click()}
                          className="mt-1 px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-white text-[10px] font-medium transition"
                        >
                          Replace Image
                        </button>
                      </div>
                    </div>

                    {/* Opacity Slider */}
                    <div>
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="text-[#A1A1AA]">Opacity</span>
                        <span className="font-mono text-cyan-400 font-bold">
                          {Math.round((selectedElement.opacity ?? 1) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="5"
                        max="100"
                        value={Math.round((selectedElement.opacity ?? 1) * 100)}
                        onChange={(e) =>
                          updateElement(selectedElement.id, {
                            opacity: parseInt(e.target.value, 10) / 100,
                          })
                        }
                        className="w-full accent-cyan-400"
                      />
                    </div>

                    {/* Fit Mode */}
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] block mb-1">Fit Mode</label>
                      <select
                        value={selectedElement.fit || "contain"}
                        onChange={(e) =>
                          updateElement(selectedElement.id, { fit: e.target.value })
                        }
                        className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                      >
                        <option value="contain">Contain (Preserve Aspect Ratio)</option>
                        <option value="cover">Cover (Fill & Crop Bounds)</option>
                        <option value="fill">Fill (Stretch to W/H)</option>
                      </select>
                    </div>

                    {/* Layer Ordering */}
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] block mb-1">Layer Ordering</label>
                      <div className="grid grid-cols-2 gap-1.5">
                        <button
                          onClick={() => reorderElement(selectedElement.id, "top")}
                          className="py-1 px-2 rounded bg-white/5 hover:bg-white/10 text-white text-[10px] font-medium transition"
                        >
                          Bring to Front
                        </button>
                        <button
                          onClick={() => reorderElement(selectedElement.id, "bottom")}
                          className="py-1 px-2 rounded bg-white/5 hover:bg-white/10 text-white text-[10px] font-medium transition"
                        >
                          Send to Back
                        </button>
                        <button
                          onClick={() => reorderElement(selectedElement.id, "up")}
                          className="py-1 px-2 rounded bg-white/5 hover:bg-white/10 text-white text-[10px] font-medium transition"
                        >
                          Step Up ▲
                        </button>
                        <button
                          onClick={() => reorderElement(selectedElement.id, "down")}
                          className="py-1 px-2 rounded bg-white/5 hover:bg-white/10 text-white text-[10px] font-medium transition"
                        >
                          Step Down ▼
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* ARTBOARD & THEME LEVEL PROPERTIES */
              <div className="space-y-5">
                {/* Theme Palette */}
                <div className="space-y-3 bg-[#1C1C1F] p-3.5 rounded-xl border border-white/10">
                  <div className="flex items-center justify-between border-b border-white/10 pb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white">
                      Theme Tokens ({spec.theme_name})
                    </span>
                    <button
                      onClick={() => setShowThemeModal(true)}
                      className="text-[10px] text-cyan-400 hover:underline"
                    >
                      + Save As New Theme
                    </button>
                  </div>

                  {(
                    [
                      { key: "background", label: "Background" },
                      { key: "primary", label: "Primary Accent" },
                      { key: "secondary", label: "Secondary Tint" },
                      { key: "accent", label: "Highlight Accent" },
                      { key: "text", label: "Main Text & Names" },
                    ] as const
                  ).map(({ key, label }) => {
                    const val = spec.theme.colors[key];
                    return (
                      <div key={key} className="flex items-center justify-between gap-2">
                        <span className="text-xs text-white">{label}</span>
                        <div className="flex items-center space-x-1.5">
                          <input
                            type="color"
                            value={val && val.startsWith("#") && val.length === 7 ? val : "#0B1220"}
                            onChange={(e) => updateThemeToken(key, e.target.value)}
                            className="w-6 h-6 rounded border border-white/20 bg-transparent cursor-pointer"
                          />
                          <input
                            type="text"
                            value={val}
                            onChange={(e) => updateThemeToken(key, e.target.value)}
                            className="w-16 font-mono text-[11px] bg-[#121214] border border-white/10 rounded px-1.5 py-0.5 text-white"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Role Colors */}
                <div className="space-y-3 bg-[#1C1C1F] p-3.5 rounded-xl border border-white/10">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-white block border-b border-white/10 pb-2">
                    Role Colors & Cues
                  </span>
                  {(
                    [
                      { role: "participant", label: "Participant", cue: "● Circle" },
                      { role: "organizer", label: "Organizer", cue: "■ Square" },
                      { role: "mentor", label: "Mentor", cue: "▲ Triangle" },
                      { role: "volunteer", label: "Volunteer", cue: "◆ Diamond" },
                    ] as const
                  ).map(({ role, label, cue }) => {
                    const val = spec.theme.role_colors[role] || "#1F6FEB";
                    return (
                      <div key={role} className="flex items-center justify-between gap-2">
                        <div>
                          <span className="text-xs text-white block">{label}</span>
                          <span className="text-[9px] text-[#A1A1AA] font-mono">{cue}</span>
                        </div>
                        <div className="flex items-center space-x-1.5">
                          <input
                            type="color"
                            value={val}
                            onChange={(e) => updateRoleColor(role, e.target.value)}
                            className="w-6 h-6 rounded border border-white/20 bg-transparent cursor-pointer"
                          />
                          <input
                            type="text"
                            value={val}
                            onChange={(e) => updateRoleColor(role, e.target.value)}
                            className="w-16 font-mono text-[11px] bg-[#121214] border border-white/10 rounded px-1.5 py-0.5 text-white"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* WCAG Contrast Diagnostics */}
                <div className="bg-[#1C1C1F] border border-white/10 rounded-xl p-3 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#A1A1AA] block">
                    WCAG 2.1 Contrast Ratios
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white">Text on Background:</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded text-[10px] ${
                        textContrast >= 4.5
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                          : "bg-rose-950 text-rose-300 border border-rose-700/60"
                      }`}
                    >
                      {textContrast.toFixed(1)}:1 {textContrast >= 7.0 ? "AAA" : textContrast >= 4.5 ? "AA" : "FAIL"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white">Role Badge Contrast:</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded text-[10px] ${
                        roleContrast >= 4.5
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                          : "bg-amber-950 text-amber-300 border border-amber-700/60"
                      }`}
                    >
                      {roleContrast.toFixed(1)}:1 {roleContrast >= 4.5 ? "PASS" : "LOW"}
                    </span>
                  </div>
                </div>

                {/* Typography Defaults */}
                <div className="space-y-3 bg-[#1C1C1F] p-3.5 rounded-xl border border-white/10">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-white block border-b border-white/10 pb-2">
                    Default Fonts
                  </span>
                  <div>
                    <label className="text-[10px] text-[#A1A1AA] block mb-1">Heading Font</label>
                    <select
                      value={spec.theme.fonts.heading}
                      onChange={(e) =>
                        recordChange({
                          ...spec,
                          theme: {
                            ...spec.theme,
                            fonts: { ...spec.theme.fonts, heading: e.target.value },
                          },
                        })
                      }
                      className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                    >
                      {FONT_OPTIONS.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-[#A1A1AA] block mb-1">Body Font</label>
                    <select
                      value={spec.theme.fonts.body}
                      onChange={(e) =>
                        recordChange({
                          ...spec,
                          theme: {
                            ...spec.theme,
                            fonts: { ...spec.theme.fonts, body: e.target.value },
                          },
                        })
                      }
                      className="w-full bg-[#121214] border border-white/10 rounded px-2 py-1 text-white"
                    >
                      {FONT_OPTIONS.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* ============================================================== */}
      {/* 3. MODALS: New Theme, New Layout, Saved Designs Drawer        */}
      {/* ============================================================== */}

      {/* New Theme Modal */}
      {showThemeModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-[#18181A] border border-white/15 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Create Custom Theme</h3>
            <p className="text-xs text-[#A1A1AA]">
              Save current color palette and typography as an independent, reusable theme.
            </p>
            <div>
              <label className="text-[10px] font-semibold text-[#A1A1AA] uppercase block mb-1">Theme Name</label>
              <input
                type="text"
                value={newThemeName}
                onChange={(e) => setNewThemeName(e.target.value)}
                placeholder="e.g. midnight_aurora"
                className="w-full bg-[#121214] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowThemeModal(false)}
                className="px-4 py-2 rounded-lg text-xs text-[#A1A1AA] hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={saveCustomTheme}
                disabled={!newThemeName.trim()}
                className="px-4 py-2 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-black font-semibold text-xs transition disabled:opacity-40"
              >
                Save Theme
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Layout Modal */}
      {showLayoutModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-[#18181A] border border-white/15 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Create Custom Layout</h3>
            <p className="text-xs text-[#A1A1AA]">
              Save current card structure and element placement as an independent layout.
            </p>
            <div>
              <label className="text-[10px] font-semibold text-[#A1A1AA] uppercase block mb-1">Layout Name</label>
              <input
                type="text"
                value={newLayoutName}
                onChange={(e) => setNewLayoutName(e.target.value)}
                placeholder="e.g. dual_column_modern"
                className="w-full bg-[#121214] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowLayoutModal(false)}
                className="px-4 py-2 rounded-lg text-xs text-[#A1A1AA] hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={saveCustomLayout}
                disabled={!newLayoutName.trim()}
                className="px-4 py-2 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-black font-semibold text-xs transition disabled:opacity-40"
              >
                Save Layout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Saved Designs Drawer */}
      {showSavedModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-[#18181A] border border-white/15 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">Saved Card Designs</h3>
                <p className="text-xs text-[#A1A1AA]">Reopen and edit previously saved ID card designs</p>
              </div>
              <button onClick={() => setShowSavedModal(false)} className="text-[#A1A1AA] hover:text-white">
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              {savedDesigns.length === 0 ? (
                <div className="text-center py-8 text-xs text-[#696970]">
                  No saved designs yet. Click &quot;💾 Save Design&quot; to save your work.
                </div>
              ) : (
                savedDesigns.map((d) => (
                  <div
                    key={d.id}
                    className="p-3 bg-[#1C1C1F] border border-white/10 rounded-xl flex items-center justify-between hover:border-cyan-400/40 transition"
                  >
                    <div>
                      <h4 className="font-bold text-xs text-white">{d.name}</h4>
                      <p className="text-[10px] text-[#A1A1AA]">
                        Saved: {d.date} • Layout: {d.spec.layout_name} • Theme: {d.spec.theme_name}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleLoadDesign(d.spec, d.name)}
                        className="px-3 py-1.5 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-black font-semibold text-xs transition"
                      >
                        Open
                      </button>
                      <button
                        onClick={() => handleDeleteSavedDesign(d.id)}
                        className="p-1.5 rounded-lg hover:bg-rose-950/40 text-rose-400 text-xs transition"
                        title="Delete"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Hidden File Inputs for Background, Decal and Image Replacement */}
      <input
        ref={bgUploadInputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUploadBackground(file);
          e.target.value = "";
        }}
      />
      <input
        ref={decalUploadInputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUploadDecal(file);
          e.target.value = "";
        }}
      />
      <input
        ref={replaceImageInputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && selectedElementId) handleReplaceImage(file, selectedElementId);
          e.target.value = "";
        }}
      />
    </div>
  );
}
