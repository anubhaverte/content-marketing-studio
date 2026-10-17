"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { DesignSpec, Person, ThemeColors } from "../types";
import { renderPreview, patchSpec, refineSpec } from "../lib/api";

interface VisualSpecEditorProps {
  initialSpec: DesignSpec;
  attendees?: Person[];
  onApplySpec?: (updatedSpec: DesignSpec) => void;
  onClose?: () => void;
}

// Default personas for testing all roles
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

const THEME_PRESETS: Record<string, { colors: ThemeColors; role_colors: Record<string, string> }> = {
  clean_light: {
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

export const LAYOUT_PRESETS: Record<string, { label: string; icon: string; description: string; elements: any[] }> = {
  classic: {
    label: "Classic Badge",
    icon: "🏛️",
    description: "Traditional centered header band with dual SVNIT & ACM logos, portrait & role pill",
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

// WCAG relative luminance & contrast calculation
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const num = parseInt(clean.length === 3 ? clean.split("").map(c => c + c).join("") : clean, 16);
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

export default function VisualSpecEditor({
  initialSpec,
  attendees = [],
  onApplySpec,
  onClose,
}: VisualSpecEditorProps) {
  // Working copy of spec
  const [spec, setSpec] = useState<DesignSpec>(() => JSON.parse(JSON.stringify(initialSpec)));
  const [activeTab, setActiveTab] = useState<"combos" | "layout" | "logos" | "theme" | "typography" | "ai_refine" | "json">("combos");
  const [selectedLogoSrc, setSelectedLogoSrc] = useState<"acm_nitsurat" | "svnit">("acm_nitsurat");

  // Active persona
  const personas = useMemo(() => {
    return attendees.length > 0 ? attendees.slice(0, 8) : DEFAULT_PERSONAS;
  }, [attendees]);
  const [selectedPersonaIndex, setSelectedPersonaIndex] = useState<number>(0);
  const currentPersona = personas[selectedPersonaIndex] || DEFAULT_PERSONAS[0];

  // SVG Preview & Guides
  const [svgContent, setSvgContent] = useState<string>("");
  const [loadingSvg, setLoadingSvg] = useState<boolean>(false);
  const [showDebugGuides, setShowDebugGuides] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Natural Language Refinement & Patch History
  const [nlPrompt, setNlPrompt] = useState<string>("");
  const [nlLoading, setNlLoading] = useState<boolean>(false);
  const [nlMessage, setNlMessage] = useState<{ type: "success" | "error"; text: string; ops?: any[] } | null>(null);
  const [history, setHistory] = useState<DesignSpec[]>([]);

  // JSON editor text & validation
  const [jsonInput, setJsonInput] = useState<string>(() => JSON.stringify(spec, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Debounced SVG renderer on spec or persona change
  const renderTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (renderTimeoutRef.current) clearTimeout(renderTimeoutRef.current);
    renderTimeoutRef.current = setTimeout(async () => {
      setLoadingSvg(true);
      try {
        const res = await renderPreview(spec, currentPersona, showDebugGuides);
        setSvgContent(res.svg);
      } catch (err: any) {
        console.error("Failed to render preview SVG:", err);
      } finally {
        setLoadingSvg(false);
      }
    }, 180);

    return () => {
      if (renderTimeoutRef.current) clearTimeout(renderTimeoutRef.current);
    };
  }, [spec, currentPersona, showDebugGuides]);

  // Keep JSON string in sync when spec changes outside JSON tab
  useEffect(() => {
    setJsonInput(JSON.stringify(spec, null, 2));
    setJsonError(null);
  }, [spec]);

  // Contrast diagnostics
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

  // --- Handlers for Theme Updates ---
  function updateThemeColor(key: keyof ThemeColors, value: string) {
    setSpec((prev) => ({
      ...prev,
      theme: {
        ...prev.theme,
        colors: {
          ...prev.theme.colors,
          [key]: value,
        },
      },
    }));
  }

  function updateRoleColor(role: string, value: string) {
    setSpec((prev) => ({
      ...prev,
      theme: {
        ...prev.theme,
        role_colors: {
          ...prev.theme.role_colors,
          [role]: value,
        },
      },
    }));
  }

  function applyPreset(presetKey: string) {
    const preset = THEME_PRESETS[presetKey];
    if (!preset) return;
    setSpec((prev) => ({
      ...prev,
      theme_name: presetKey,
      theme: {
        ...prev.theme,
        name: presetKey,
        colors: { ...preset.colors },
        role_colors: { ...preset.role_colors },
      },
    }));
  }

  // --- Handlers for Layout & Combo Switching ---
  function applyLayout(layoutKey: string) {
    const layout = LAYOUT_PRESETS[layoutKey];
    if (!layout) return;
    setSpec((prev) => ({
      ...prev,
      layout_name: layoutKey,
      elements: JSON.parse(JSON.stringify(layout.elements)),
    }));
  }

  function applyCombination(layoutKey: string, themeKey: string) {
    const layout = LAYOUT_PRESETS[layoutKey];
    const theme = THEME_PRESETS[themeKey];
    if (!layout || !theme) return;
    setSpec((prev) => ({
      ...prev,
      layout_name: layoutKey,
      theme_name: themeKey,
      elements: JSON.parse(JSON.stringify(layout.elements)),
      theme: {
        ...prev.theme,
        name: themeKey,
        colors: { ...theme.colors },
        role_colors: { ...theme.role_colors },
      },
    }));
  }

  // --- Handlers for Logo Positioning & Alignment ---
  function updateLogoProp(logoSrc: string, fieldKey: string, value: any) {
    setSpec((prev) => {
      const elements = prev.elements.map((el) => {
        if (el.type === "logo" && (el.src === logoSrc || el.id?.includes(logoSrc))) {
          return { ...el, [fieldKey]: value };
        }
        return el;
      });
      return { ...prev, elements };
    });
  }

  function autoAlignLogos(targetY?: number) {
    setSpec((prev) => {
      const banner = prev.elements.find(
        (el) => el.type === "rect" && el.y === 0 && (el.fill === "primary" || el.id === "banner" || (el.w === 60 && el.h <= 30))
      );
      const bannerH = banner ? banner.h : 24;
      const logoH = 15;
      const y = targetY !== undefined ? targetY : Math.max(2, (bannerH - logoH) / 2);

      const elements = prev.elements.map((el) => {
        if (el.type === "logo") {
          if (el.src === "acm_nitsurat" || el.id?.includes("acm")) {
            return { ...el, x: 8, y, w: 15, h: 15 };
          }
          if (el.src === "svnit" || el.id?.includes("svnit")) {
            return { ...el, x: 37, y, w: 15, h: 15 };
          }
        }
        return el;
      });
      return { ...prev, elements };
    });
  }

  // --- Handlers for Layout Geometry Updates ---
  function updateElementProp(elementType: string, fieldKey: string, value: any) {
    setSpec((prev) => {
      const elements = prev.elements.map((el) => {
        if (el.type === elementType) {
          return { ...el, [fieldKey]: value };
        }
        return el;
      });
      return { ...prev, elements };
    });
  }

  function getElement(elementType: string) {
    return spec.elements?.find((el) => el.type === elementType);
  }

  // Element helpers
  const nameElement = getElement("text");
  const photoElement = getElement("photo");
  const roleElement = getElement("role_badge");
  const qrElement = getElement("qr");
  const acmLogo = spec.elements?.find((el) => el.type === "logo" && (el.src === "acm_nitsurat" || el.id?.includes("acm")));
  const svnitLogo = spec.elements?.find((el) => el.type === "logo" && (el.src === "svnit" || el.id?.includes("svnit")));
  const bannerRect = spec.elements?.find((el) => el.type === "rect" && el.y === 0 && (el.fill === "primary" || el.id === "banner" || (el.w === 60 && el.h <= 30)));

  // --- Natural Language Patch Handler ---
  async function handleNlPatch(e?: React.FormEvent, customPrompt?: string) {
    if (e) e.preventDefault();
    const promptToUse = customPrompt || nlPrompt;
    if (!promptToUse.trim()) return;

    setNlLoading(true);
    setNlMessage(null);

    try {
      // Save current state for undo
      setHistory((prev) => [...prev, JSON.parse(JSON.stringify(spec))]);

      const res = await refineSpec(spec, promptToUse);
      setSpec(res.spec);
      setNlMessage({
        type: "success",
        text: res.summary || `Applied ${res.ops.length} visual refinement(s)!`,
        ops: res.ops,
      });
      if (onApplySpec) {
        onApplySpec(res.spec);
      }
    } catch (err: any) {
      setNlMessage({
        type: "error",
        text: err.detail || err.message || "Failed to refine spec via API.",
      });
    } finally {
      setNlLoading(false);
    }
  }

  function handleUndoRefine() {
    if (history.length === 0) return;
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setSpec(prev);
    if (onApplySpec) {
      onApplySpec(prev);
    }
    setNlMessage({ type: "success", text: "Reverted to previous design state." });
  }

  // --- JSON Editor Sync ---
  function handleJsonChange(text: string) {
    setJsonInput(text);
    try {
      const parsed = JSON.parse(text);
      setSpec(parsed);
      setJsonError(null);
    } catch (err: any) {
      setJsonError(err.message);
    }
  }

  function handleDownloadSvg() {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${currentPersona.name.toLowerCase().replace(/\s+/g, "_")}_badge.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function handleDownloadJson() {
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `design_spec_${spec.layout_name}_${spec.theme_name}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function handleCopyJson() {
    navigator.clipboard.writeText(JSON.stringify(spec, null, 2));
    alert("Design Spec JSON copied to clipboard!");
  }

  return (
    <div className="bg-[#1E1E20] text-[#FAFAFA] rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col h-[850px] w-full font-sans">
      {/* Top Studio Bar */}
      <div className="bg-[#0E0E10] border-b border-white/10 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/15 p-1 flex items-center justify-center shrink-0">
            <img src="/logos/acm_nitsurat.svg" alt="ACM NIT Surat" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-[#FAFAFA] tracking-tight">
                Visual Spec & Theme Editor
              </h2>
              <span className="text-[10px] font-mono bg-white/5 border border-white/10 text-[#FAFAFA] px-2 py-0.5 rounded-full">
                54 × 86 mm (ID-1)
              </span>
            </div>
            <p className="text-[11px] text-[#A1A1AA]">
              Interactive layout geometry, theme tokens & live vector SVG preview
            </p>
          </div>
        </div>

        {/* Global Editor Actions */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setSpec(JSON.parse(JSON.stringify(initialSpec)))}
            className="px-3.5 py-1.5 rounded-full border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-[#FAFAFA] transition"
            title="Reset to draft defaults"
          >
            ↺ Reset
          </button>
          <button
            onClick={handleCopyJson}
            className="px-3.5 py-1.5 rounded-full border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-[#FAFAFA] transition"
            title="Copy current spec JSON"
          >
            📋 Copy JSON
          </button>
          <button
            onClick={handleDownloadSvg}
            className="px-3.5 py-1.5 rounded-full border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-[#FAFAFA] transition"
            title="Export crisp vector SVG"
          >
            🖼️ SVG
          </button>
          {onApplySpec && (
            <button
              onClick={() => onApplySpec(spec)}
              className="px-4 py-1.5 rounded-full bg-white hover:bg-slate-100 text-black font-semibold text-xs shadow-md transition"
            >
              ✓ Apply to Active Draft
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="px-2.5 py-1.5 rounded-full hover:bg-white/10 text-[#A1A1AA] hover:text-white transition"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Main Split Layout: Controls (Left) vs Canvas (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden">
        {/* LEFT: Tabbed Controls Panel (5 Cols) */}
        <div className="lg:col-span-5 bg-[#181818] border-r border-white/10 flex flex-col h-full overflow-hidden">
          {/* Tabs Navigation */}
          <div className="flex border-b border-white/10 bg-[#0E0E10] text-xs font-semibold">
            <button
              onClick={() => setActiveTab("combos")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "combos"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              ✨ 9 Combos
            </button>
            <button
              onClick={() => setActiveTab("layout")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "layout"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              📐 Layouts
            </button>
            <button
              onClick={() => setActiveTab("logos")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "logos"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              🏷️ Logo Tool
            </button>
            <button
              onClick={() => setActiveTab("theme")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "theme"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              🎨 Themes
            </button>
            <button
              onClick={() => setActiveTab("typography")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "typography"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              🔤 Typography
            </button>
            <button
              onClick={() => setActiveTab("ai_refine")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "ai_refine"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              ✨ AI Refine
            </button>
            <button
              onClick={() => setActiveTab("json")}
              className={`flex-1 py-3 px-2 text-center transition border-b-2 font-semibold ${
                activeTab === "json"
                  ? "border-white text-white bg-white/5"
                  : "border-transparent text-[#A1A1AA] hover:text-white"
              }`}
            >
              {"{ }"} JSON
            </button>
          </div>

          {/* Tab Panes (Scrollable) */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs text-slate-300">
            {/* TAB 0: 9 COMBINATIONS MATRIX (3 Layouts × 3 Themes) */}
            {activeTab === "combos" && (
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                      9 Layout & Theme Combinations
                    </h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-300">
                      3 Layouts × 3 Themes = 9 Combos
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mb-4">
                    Click any combination cell below to instantly switch both layout structure and color theme.
                  </p>

                  <div className="grid grid-cols-1 gap-3">
                    {Object.keys(LAYOUT_PRESETS).map((layoutKey) => {
                      const lPreset = LAYOUT_PRESETS[layoutKey];
                      return (
                        <div key={layoutKey} className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 space-y-2">
                          <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                            <span className="font-bold text-slate-200 flex items-center space-x-1.5">
                              <span>{lPreset.icon}</span>
                              <span>{lPreset.label}</span>
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono capitalize">
                              {layoutKey}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-2">
                            {Object.keys(THEME_PRESETS).map((themeKey) => {
                              const tPreset = THEME_PRESETS[themeKey];
                              const isCurrent = spec.layout_name === layoutKey && spec.theme_name === themeKey;
                              return (
                                <button
                                  key={themeKey}
                                  type="button"
                                  onClick={() => applyCombination(layoutKey, themeKey)}
                                  className={`p-2 rounded-lg border text-left transition flex flex-col justify-between ${
                                    isCurrent
                                      ? "bg-cyan-950/60 border-cyan-400 ring-2 ring-cyan-400/50 shadow-md"
                                      : "bg-slate-900/60 border-slate-700/80 hover:border-slate-500"
                                  }`}
                                >
                                  <div>
                                    <div className="flex justify-between items-center mb-1">
                                      <span className="text-[11px] font-bold text-slate-200 capitalize">
                                        {themeKey.replace("_", " ")}
                                      </span>
                                      {isCurrent && (
                                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                                      )}
                                    </div>
                                    <div className="flex space-x-1 my-1">
                                      <span
                                        className="w-3.5 h-3.5 rounded border border-slate-700 shadow-xs"
                                        style={{ backgroundColor: tPreset.colors.background }}
                                        title="Background"
                                      />
                                      <span
                                        className="w-3.5 h-3.5 rounded border border-slate-700 shadow-xs"
                                        style={{ backgroundColor: tPreset.colors.primary }}
                                        title="Primary"
                                      />
                                      <span
                                        className="w-3.5 h-3.5 rounded border border-slate-700 shadow-xs"
                                        style={{ backgroundColor: tPreset.colors.accent }}
                                        title="Accent"
                                      />
                                    </div>
                                  </div>
                                  <span className={`text-[10px] mt-1 font-semibold ${isCurrent ? "text-cyan-300" : "text-slate-400"}`}>
                                    {isCurrent ? "✓ Active" : "Select"}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Quick Style Switchers */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-slate-800 space-y-2">
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Layout Only
                    </label>
                    <select
                      value={spec.layout_name || "classic"}
                      onChange={(e) => applyLayout(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400 capitalize"
                    >
                      {Object.keys(LAYOUT_PRESETS).map((k) => (
                        <option key={k} value={k}>
                          {LAYOUT_PRESETS[k].label} ({k})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-slate-800 space-y-2">
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Theme Only
                    </label>
                    <select
                      value={spec.theme_name || "clean_light"}
                      onChange={(e) => applyPreset(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400 capitalize"
                    >
                      {Object.keys(THEME_PRESETS).map((k) => (
                        <option key={k} value={k}>
                          {k.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: INSTITUTIONAL LOGOS ALIGNMENT TOOL */}
            {activeTab === "logos" && (
              <div className="space-y-6">
                <div className="bg-slate-950/60 p-4 rounded-xl border border-cyan-800/50 space-y-4">
                  <div className="flex justify-between items-start border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="font-bold text-cyan-300 text-xs uppercase tracking-wider">
                        Official Logos Alignment Tool
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Fine-tune position & dimensions for ACM and SVNIT vector logos
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => autoAlignLogos()}
                      className="px-2.5 py-1 bg-cyan-900/60 hover:bg-cyan-800 text-cyan-200 border border-cyan-700/60 rounded text-[11px] font-semibold transition"
                      title="Vertically center both logos within header band"
                    >
                      ⚡ Auto-Center in Header
                    </button>
                  </div>

                  {/* Logo Selector Tabs */}
                  <div className="flex space-x-2">
                    <button
                      type="button"
                      onClick={() => setSelectedLogoSrc("acm_nitsurat")}
                      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-1.5 ${
                        selectedLogoSrc === "acm_nitsurat"
                          ? "bg-blue-600 text-white shadow-sm ring-1 ring-blue-400"
                          : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
                      }`}
                    >
                      <span>🔷</span>
                      <span>ACM NIT Surat</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLogoSrc("svnit")}
                      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-1.5 ${
                        selectedLogoSrc === "svnit"
                          ? "bg-blue-600 text-white shadow-sm ring-1 ring-blue-400"
                          : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
                      }`}
                    >
                      <span>🏛️</span>
                      <span>SVNIT Surat</span>
                    </button>
                  </div>

                  {/* Active Logo Controls */}
                  {(() => {
                    const activeLogo = selectedLogoSrc === "acm_nitsurat" ? acmLogo : svnitLogo;
                    if (!activeLogo) {
                      return (
                        <div className="py-6 text-center text-slate-500">
                          Logo {selectedLogoSrc} not present in active layout.
                        </div>
                      );
                    }

                    const logoX = activeLogo.x ?? 8;
                    const logoY = activeLogo.y ?? 4.5;
                    const logoW = activeLogo.w ?? 15;
                    const logoH = activeLogo.h ?? 15;

                    return (
                      <div className="space-y-4 pt-1">
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-300 font-medium">Horizontal Position (X): {logoX} mm</span>
                            <div className="flex items-center space-x-2">
                              <input
                                type="number"
                                step="0.5"
                                min="0"
                                max="50"
                                value={logoX}
                                onChange={(e) => updateLogoProp(selectedLogoSrc, "x", parseFloat(e.target.value) || 0)}
                                className="w-16 font-mono text-[11px] bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-slate-200"
                              />
                            </div>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="50"
                            step="0.5"
                            value={logoX}
                            onChange={(e) => updateLogoProp(selectedLogoSrc, "x", parseFloat(e.target.value))}
                            className="w-full accent-cyan-400"
                          />
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-300 font-medium">Vertical Position (Y): {logoY} mm</span>
                            <div className="flex items-center space-x-2">
                              <input
                                type="number"
                                step="0.5"
                                min="0"
                                max="80"
                                value={logoY}
                                onChange={(e) => updateLogoProp(selectedLogoSrc, "y", parseFloat(e.target.value) || 0)}
                                className="w-16 font-mono text-[11px] bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-slate-200"
                              />
                            </div>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="50"
                            step="0.5"
                            value={logoY}
                            onChange={(e) => updateLogoProp(selectedLogoSrc, "y", parseFloat(e.target.value))}
                            className="w-full accent-cyan-400"
                          />
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-300 font-medium">Width (W): {logoW} mm</span>
                            <div className="flex items-center space-x-2">
                              <input
                                type="number"
                                step="0.5"
                                min="6"
                                max="35"
                                value={logoW}
                                onChange={(e) => updateLogoProp(selectedLogoSrc, "w", parseFloat(e.target.value) || 15)}
                                className="w-16 font-mono text-[11px] bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-slate-200"
                              />
                            </div>
                          </div>
                          <input
                            type="range"
                            min="6"
                            max="35"
                            step="0.5"
                            value={logoW}
                            onChange={(e) => updateLogoProp(selectedLogoSrc, "w", parseFloat(e.target.value))}
                            className="w-full accent-cyan-400"
                          />
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-300 font-medium">Height (H): {logoH} mm</span>
                            <div className="flex items-center space-x-2">
                              <input
                                type="number"
                                step="0.5"
                                min="6"
                                max="35"
                                value={logoH}
                                onChange={(e) => updateLogoProp(selectedLogoSrc, "h", parseFloat(e.target.value) || 15)}
                                className="w-16 font-mono text-[11px] bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-slate-200"
                              />
                            </div>
                          </div>
                          <input
                            type="range"
                            min="6"
                            max="35"
                            step="0.5"
                            value={logoH}
                            onChange={(e) => updateLogoProp(selectedLogoSrc, "h", parseFloat(e.target.value))}
                            className="w-full accent-cyan-400"
                          />
                        </div>

                        {/* Quick Presets */}
                        <div className="pt-2 border-t border-slate-800">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                            Quick Alignment Presets
                          </span>
                          <div className="grid grid-cols-3 gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                updateLogoProp("acm_nitsurat", "x", 8);
                                updateLogoProp("acm_nitsurat", "y", 4.5);
                                updateLogoProp("acm_nitsurat", "w", 15);
                                updateLogoProp("acm_nitsurat", "h", 15);
                                updateLogoProp("svnit", "x", 37);
                                updateLogoProp("svnit", "y", 4.5);
                                updateLogoProp("svnit", "w", 15);
                                updateLogoProp("svnit", "h", 15);
                              }}
                              className="py-1.5 px-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-[11px] text-slate-200"
                            >
                              Centered Dual (15mm)
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                updateLogoProp("acm_nitsurat", "x", 7);
                                updateLogoProp("acm_nitsurat", "y", 5.5);
                                updateLogoProp("acm_nitsurat", "w", 11);
                                updateLogoProp("acm_nitsurat", "h", 11);
                                updateLogoProp("svnit", "x", 42);
                                updateLogoProp("svnit", "y", 5.5);
                                updateLogoProp("svnit", "w", 11);
                                updateLogoProp("svnit", "h", 11);
                              }}
                              className="py-1.5 px-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-[11px] text-slate-200"
                            >
                              Compact (11mm)
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                updateLogoProp("acm_nitsurat", "x", 8);
                                updateLogoProp("acm_nitsurat", "y", 3.5);
                                updateLogoProp("acm_nitsurat", "w", 17);
                                updateLogoProp("acm_nitsurat", "h", 17);
                                updateLogoProp("svnit", "x", 35);
                                updateLogoProp("svnit", "y", 3.5);
                                updateLogoProp("svnit", "w", 17);
                                updateLogoProp("svnit", "h", 17);
                              }}
                              className="py-1.5 px-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-[11px] text-slate-200"
                            >
                              Prominent (17mm)
                            </button>
                          </div>
                        </div>

                        {/* Banner Band Adjuster if present */}
                        {bannerRect && (
                          <div className="pt-3 border-t border-slate-800 space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-slate-300 font-medium">Header Band Height: {bannerRect.h} mm</span>
                              <input
                                type="number"
                                step="1"
                                min="16"
                                max="40"
                                value={bannerRect.h}
                                onChange={(e) => updateElementProp("rect", "h", parseFloat(e.target.value) || 24)}
                                className="w-16 font-mono text-[11px] bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-slate-200"
                              />
                            </div>
                            <input
                              type="range"
                              min="16"
                              max="40"
                              step="1"
                              value={bannerRect.h}
                              onChange={(e) => updateElementProp("rect", "h", parseFloat(e.target.value))}
                              className="w-full accent-cyan-400"
                            />
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* TAB 1: THEME & COLOR TOKENS */}
            {activeTab === "theme" && (
              <div className="space-y-6">
                {/* Theme Preset Quick-Select */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Theme Preset
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.keys(THEME_PRESETS).map((key) => (
                      <button
                        key={key}
                        onClick={() => applyPreset(key)}
                        className={`py-2 px-2.5 rounded-lg border text-xs font-semibold capitalize transition ${
                          spec.theme_name === key
                            ? "bg-blue-600/20 border-cyan-400 text-cyan-300 ring-1 ring-cyan-400"
                            : "bg-slate-800/60 border-slate-700 text-slate-400 hover:border-slate-500"
                        }`}
                      >
                        {key.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Core Design Tokens */}
                <div className="space-y-3">
                  <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-1.5">
                    Core Color Tokens
                  </h3>

                  {(
                    [
                      { key: "background", label: "Card Background" },
                      { key: "primary", label: "Primary Accent" },
                      { key: "secondary", label: "Secondary Tint" },
                      { key: "accent", label: "Highlight / Badge Accent" },
                      { key: "text", label: "Main Text & Names" },
                    ] as const
                  ).map(({ key, label }) => {
                    const val = spec.theme?.colors?.[key] || "#FFFFFF";
                    return (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span className="font-medium text-slate-300">{label}</span>
                        <div className="flex items-center space-x-2">
                          <input
                            type="color"
                            value={val}
                            onChange={(e) => updateThemeColor(key, e.target.value.toUpperCase())}
                            className="w-7 h-7 rounded border border-slate-700 bg-transparent cursor-pointer"
                          />
                          <input
                            type="text"
                            value={val}
                            onChange={(e) => updateThemeColor(key, e.target.value.toUpperCase())}
                            className="w-20 font-mono text-[11px] bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-400"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Role Specific Badges */}
                <div className="space-y-3 pt-2">
                  <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-1.5">
                    Role Colors (Color-blind & B&W Compatible)
                  </h3>

                  {(
                    [
                      { role: "participant", label: "Participant", cue: "● Circle" },
                      { role: "organizer", label: "Organizer", cue: "■ Square" },
                      { role: "mentor", label: "Mentor", cue: "▲ Triangle" },
                      { role: "volunteer", label: "Volunteer", cue: "◆ Diamond" },
                    ] as const
                  ).map(({ role, label, cue }) => {
                    const val = spec.theme?.role_colors?.[role] || "#1F6FEB";
                    return (
                      <div key={role} className="flex items-center justify-between gap-3">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-slate-300">{label}</span>
                          <span className="text-[10px] text-cyan-400 font-mono">({cue})</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <input
                            type="color"
                            value={val}
                            onChange={(e) => updateRoleColor(role, e.target.value.toUpperCase())}
                            className="w-7 h-7 rounded border border-slate-700 bg-transparent cursor-pointer"
                          />
                          <input
                            type="text"
                            value={val}
                            onChange={(e) => updateRoleColor(role, e.target.value.toUpperCase())}
                            className="w-20 font-mono text-[11px] bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-400"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Real-time WCAG Contrast Scores */}
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    WCAG 2.1 Contrast Diagnostics
                  </span>
                  <div className="flex items-center justify-between">
                    <span>Text on Background:</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                        textContrast >= 4.5
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                          : "bg-rose-950 text-rose-300 border border-rose-700/60"
                      }`}
                    >
                      {textContrast.toFixed(1)}:1 {textContrast >= 7.0 ? "AAA" : textContrast >= 4.5 ? "AA" : "FAIL"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Role Badge Contrast:</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                        roleContrast >= 4.5
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                          : "bg-amber-950 text-amber-300 border border-amber-700/60"
                      }`}
                    >
                      {roleContrast.toFixed(1)}:1 {roleContrast >= 4.5 ? "PASS" : "LOW"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: GEOMETRY & ELEMENT SLIDERS */}
            {activeTab === "layout" && (
              <div className="space-y-6">
                {/* Active Layout Template Switcher */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Active Layout Template
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.keys(LAYOUT_PRESETS).map((key) => {
                      const lPreset = LAYOUT_PRESETS[key];
                      const isSelected = spec.layout_name === key;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => applyLayout(key)}
                          className={`py-2 px-2 rounded-lg border text-xs font-semibold capitalize transition flex flex-col items-center justify-center space-y-1 ${
                            isSelected
                              ? "bg-blue-600/20 border-cyan-400 text-cyan-300 ring-1 ring-cyan-400"
                              : "bg-slate-800/60 border-slate-700 text-slate-400 hover:border-slate-500"
                          }`}
                        >
                          <span className="text-sm">{lPreset.icon}</span>
                          <span>{key}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
                {/* Photo Element Coordinates */}
                {photoElement && (
                  <div className="space-y-3 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800">
                    <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                      <span className="font-bold text-slate-200">Attendee Photo Frame</span>
                      <select
                        value={photoElement.shape || "rounded"}
                        onChange={(e) => updateElementProp("photo", "shape", e.target.value)}
                        className="bg-slate-900 border border-slate-700 text-slate-200 text-[11px] rounded px-2 py-0.5"
                      >
                        <option value="rounded">Rounded Box</option>
                        <option value="circle">Circular Clip</option>
                        <option value="square">Square</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Y Position: {photoElement.y} mm</span>
                        <input
                          type="range"
                          min="15"
                          max="50"
                          value={photoElement.y}
                          onChange={(e) => updateElementProp("photo", "y", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Width: {photoElement.w} mm</span>
                        <input
                          type="range"
                          min="18"
                          max="42"
                          value={photoElement.w}
                          onChange={(e) => updateElementProp("photo", "w", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Height: {photoElement.h} mm</span>
                        <input
                          type="range"
                          min="22"
                          max="48"
                          value={photoElement.h}
                          onChange={(e) => updateElementProp("photo", "h", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Name Typography Coordinates */}
                {nameElement && (
                  <div className="space-y-3 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800">
                    <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                      <span className="font-bold text-slate-200">Attendee Name Block</span>
                      <select
                        value={nameElement.align || "center"}
                        onChange={(e) => updateElementProp("text", "align", e.target.value)}
                        className="bg-slate-900 border border-slate-700 text-slate-200 text-[11px] rounded px-2 py-0.5"
                      >
                        <option value="center">Center</option>
                        <option value="left">Left</option>
                        <option value="right">Right</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Y Position: {nameElement.y} mm</span>
                        <input
                          type="range"
                          min="50"
                          max="80"
                          value={nameElement.y}
                          onChange={(e) => updateElementProp("text", "y", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Max Font: {nameElement.max_font || 16} pt</span>
                        <input
                          type="range"
                          min="10"
                          max="22"
                          value={nameElement.max_font || 16}
                          onChange={(e) => updateElementProp("text", "max_font", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Role Badge Coordinates */}
                {roleElement && (
                  <div className="space-y-3 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800">
                    <span className="font-bold text-slate-200 block border-b border-slate-800 pb-2">
                      Role Badge Position
                    </span>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Y Position: {roleElement.y} mm</span>
                      <input
                        type="range"
                        min="60"
                        max="85"
                        value={roleElement.y}
                        onChange={(e) => updateElementProp("role_badge", "y", parseFloat(e.target.value))}
                        className="w-36 accent-cyan-400"
                      />
                    </div>
                  </div>
                )}

                {/* QR Code Coordinates */}
                {qrElement && (
                  <div className="space-y-3 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800">
                    <span className="font-bold text-slate-200 block border-b border-slate-800 pb-2">
                      Security QR Code (Min 12 × 12 mm)
                    </span>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Size (W & H): {qrElement.w} mm</span>
                        <input
                          type="range"
                          min="12"
                          max="24"
                          value={qrElement.w}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            updateElementProp("qr", "w", val);
                            updateElementProp("qr", "h", val);
                          }}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Y Position: {qrElement.y} mm</span>
                        <input
                          type="range"
                          min="50"
                          max="82"
                          value={qrElement.y}
                          onChange={(e) => updateElementProp("qr", "y", parseFloat(e.target.value))}
                          className="w-36 accent-cyan-400"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: TYPOGRAPHY & BRAND */}
            {activeTab === "typography" && (
              <div className="space-y-6">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Heading Font (Names & Roles)
                  </label>
                  <select
                    value={spec.theme?.fonts?.heading || "Poppins"}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        theme: {
                          ...prev.theme,
                          fonts: { ...prev.theme.fonts, heading: e.target.value },
                        },
                      }))
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Body Font (IDs, Team, Dates)
                  </label>
                  <select
                    value={spec.theme?.fonts?.body || "Inter"}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        theme: {
                          ...prev.theme,
                          fonts: { ...prev.theme.fonts, body: e.target.value },
                        },
                      }))
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="font-bold text-slate-200 block text-[11px] uppercase tracking-wider">
                    Official Institutional Logos
                  </span>
                  <div className="flex items-center space-x-3 text-slate-400 text-xs">
                    <span className="text-emerald-400">✓</span>
                    <span>SVNIT Surat Logo (Vector SVG, Contain Fit)</span>
                  </div>
                  <div className="flex items-center space-x-3 text-slate-400 text-xs">
                    <span className="text-emerald-400">✓</span>
                    <span>ACM NIT Surat Chapter Logo (Vector SVG, Contain Fit)</span>
                  </div>
                </div>

                {/* Natural Language Refinement Form */}
                <form onSubmit={handleNlPatch} className="space-y-3 pt-2">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A1A1AA]">
                    Natural Language Refinement Patch
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="e.g. make theme dark blue, circle photo..."
                      value={nlPrompt}
                      onChange={(e) => setNlPrompt(e.target.value)}
                      className="flex-1 bg-[#121214] border border-white/15 rounded-lg px-3 py-2 text-xs text-[#FAFAFA] focus:outline-none focus:border-white/40"
                    />
                    <button
                      type="submit"
                      disabled={nlLoading || !nlPrompt.trim()}
                      className="px-4 py-2 bg-white hover:bg-slate-100 text-black font-semibold rounded-full text-xs transition disabled:opacity-40"
                    >
                      {nlLoading ? "Applying..." : "Patch"}
                    </button>
                  </div>
                  {nlMessage && (
                    <p
                      className={`text-[11px] ${
                        nlMessage.type === "success" ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      {nlMessage.text}
                    </p>
                  )}
                </form>
              </div>
            )}

            {/* TAB: NATURAL LANGUAGE AI REFINEMENT (PHASE 2) */}
            {activeTab === "ai_refine" && (
              <div className="space-y-5">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#FAFAFA] flex items-center space-x-1.5">
                      <span>✨</span>
                      <span>AI Design Assistant</span>
                    </h3>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-white/10 border border-white/15 text-[#FAFAFA] font-medium">
                      Smart Refine
                    </span>
                  </div>
                  <p className="text-[11px] text-[#A1A1AA]">
                    Enter design instructions in plain English to adjust badge layout, geometry, color palette, or typography in real time.
                  </p>
                </div>

                {/* Security Guarantee Banner */}
                <div className="p-3.5 bg-white/5 border border-white/10 rounded-xl space-y-1.5 text-xs">
                  <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-[11px]">
                    <span>🔒</span>
                    <span>Protected Design Elements</span>
                  </div>
                  <p className="text-[11px] text-[#A1A1AA] leading-relaxed">
                    Attendee credentials and institutional crests are protected from alteration. Refinements strictly adapt layout styling, color schemes, and typographical balance.
                  </p>
                </div>

                {/* Quick Prompts */}
                <div className="space-y-2">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A1A1AA]">
                    Quick Refinement Prompts
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { label: "Make Photo Circle", prompt: "Make attendee photo a circle" },
                      { label: "Prominent Name", prompt: "Make name bigger and prominent" },
                      { label: "Center Name", prompt: "Center the attendee name" },
                      { label: "Dark Tech Theme", prompt: "Switch to dark tech theme" },
                      { label: "Clean Light Theme", prompt: "Switch to clean light theme" },
                      { label: "Poppins Font", prompt: "Use Poppins font for headings" },
                      { label: "Amber Accent", prompt: "Set accent color to #F59E0B" },
                    ].map((item, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setNlPrompt(item.prompt);
                          handleNlPatch(undefined, item.prompt);
                        }}
                        disabled={nlLoading}
                        className="px-2.5 py-1 text-[11px] rounded-lg border border-white/10 bg-[#121214] hover:bg-white/10 text-[#FAFAFA] transition disabled:opacity-40"
                      >
                        + {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Prompt Input Form */}
                <form onSubmit={handleNlPatch} className="space-y-3">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A1A1AA]">
                    Custom Natural Language Prompt
                  </label>
                  <textarea
                    rows={3}
                    value={nlPrompt}
                    onChange={(e) => setNlPrompt(e.target.value)}
                    placeholder="e.g. Make photo circular, increase name size to 16, and use #38BDF8 accent..."
                    className="w-full bg-[#121214] border border-white/15 rounded-xl p-3 text-xs text-[#FAFAFA] focus:outline-none focus:border-white/40 placeholder-[#696970] resize-none"
                  />

                  <div className="flex items-center space-x-2">
                    <button
                      type="submit"
                      disabled={nlLoading || !nlPrompt.trim()}
                      className="flex-1 py-2.5 bg-white hover:bg-slate-100 text-black font-semibold rounded-full text-xs transition disabled:opacity-40 flex items-center justify-center space-x-2"
                    >
                      {nlLoading ? (
                        <>
                          <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                          <span>Refining Spec...</span>
                        </>
                      ) : (
                        <span>✨ Apply AI Refinement</span>
                      )}
                    </button>

                    {history.length > 0 && (
                      <button
                        type="button"
                        onClick={handleUndoRefine}
                        disabled={nlLoading}
                        className="px-4 py-2.5 border border-white/15 bg-white/5 hover:bg-white/10 text-[#FAFAFA] rounded-full text-xs font-semibold transition"
                        title="Revert to prior spec"
                      >
                        ↺ Undo ({history.length})
                      </button>
                    )}
                  </div>
                </form>

                {/* Message / Result Box */}
                {nlMessage && (
                  <div
                    className={`p-4 rounded-xl border text-xs space-y-2 ${
                      nlMessage.type === "success"
                        ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
                        : "bg-rose-950/40 border-rose-500/30 text-rose-300"
                    }`}
                  >
                    <div className="flex items-center space-x-2 font-semibold">
                      <span>{nlMessage.type === "success" ? "✓" : "⚠️"}</span>
                      <span>{nlMessage.text}</span>
                    </div>

                    {nlMessage.ops && nlMessage.ops.length > 0 && (
                      <div className="pt-2 border-t border-emerald-500/20 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-emerald-400 block">
                          Applied Patch Operations:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {nlMessage.ops.map((op: any, i: number) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-black/40 border border-emerald-500/30 text-[10px] font-mono text-[#FAFAFA]"
                            >
                              {op.path}: {String(op.value)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: JSON SPEC EDITOR */}
            {activeTab === "json" && (
              <div className="space-y-3 h-full flex flex-col">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] text-slate-400 font-mono">
                    Editable DesignSpec JSON Schema v1.0
                  </span>
                  <button
                    onClick={handleDownloadJson}
                    className="text-[11px] text-cyan-400 hover:underline"
                  >
                    Download .json
                  </button>
                </div>
                <textarea
                  value={jsonInput}
                  onChange={(e) => handleJsonChange(e.target.value)}
                  className="w-full flex-1 min-h-[380px] bg-slate-950 font-mono text-[11px] text-cyan-300 p-3 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-400 resize-none leading-relaxed"
                  spellCheck={false}
                />
                {jsonError ? (
                  <p className="text-[11px] text-rose-400 font-mono">⚠️ Invalid JSON: {jsonError}</p>
                ) : (
                  <p className="text-[11px] text-emerald-400 font-mono">✓ JSON is valid and synced.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Live Interactive Stage & SVG Viewport (7 Cols) */}
        <div className="lg:col-span-7 bg-[#121214] flex flex-col h-full overflow-hidden relative">
          {/* Top Persona Switcher & Canvas Controls Bar */}
          <div className="bg-[#0E0E10] border-b border-white/10 px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 z-10">
            {/* Persona Switcher Chips */}
            <div className="flex items-center space-x-1.5 overflow-x-auto py-0.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#A1A1AA] mr-1">
                Preview:
              </span>
              {personas.map((p, idx) => {
                const isActive = selectedPersonaIndex === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedPersonaIndex(idx)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition flex items-center space-x-1.5 ${
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

            {/* Print Guides Toggle & Zoom */}
            <div className="flex items-center space-x-3 text-xs text-[#FAFAFA]">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showDebugGuides}
                  onChange={(e) => setShowDebugGuides(e.target.checked)}
                  className="rounded border-white/20 bg-[#121214] text-white focus:ring-0 cursor-pointer"
                />
                <span className="text-[11px] font-medium text-[#A1A1AA]">Guides</span>
              </label>

              <div className="flex items-center space-x-1 border border-white/10 rounded-full px-2 py-0.5 bg-white/5">
                <button
                  onClick={() => setZoomLevel((z) => Math.max(60, z - 10))}
                  className="px-1 text-[#A1A1AA] hover:text-white font-bold"
                >
                  -
                </button>
                <span className="text-[10px] font-mono w-9 text-center text-[#FAFAFA]">
                  {zoomLevel}%
                </span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(180, z + 10))}
                  className="px-1 text-[#A1A1AA] hover:text-white font-bold"
                >
                  +
                </button>
              </div>
            </div>
          </div>

          {/* Canvas Stage */}
          <div className="flex-1 overflow-auto p-8 flex items-center justify-center bg-[#0E0E10]">
            {loadingSvg ? (
              <div className="text-center space-y-3">
                <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs text-[#A1A1AA] font-mono">Compiling vector SVG with font embedding...</p>
              </div>
            ) : svgContent ? (
              <div
                className="transition-transform duration-200 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.85)] rounded-sm bg-white overflow-hidden max-w-sm w-full"
                style={{ transform: `scale(${zoomLevel / 100})` }}
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            ) : (
              <div className="text-center text-[#696970] text-xs font-mono">
                No preview rendered. Click a theme or persona to render.
              </div>
            )}
          </div>

          {/* Bottom Diagnostics Strip */}
          <div className="bg-[#0E0E10] border-t border-white/10 px-5 py-2.5 flex items-center justify-between text-[11px] text-[#A1A1AA] font-mono">
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                <span>Bleed: 3mm</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                <span>Trim: 54×86mm</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                <span>Safe Area: 4mm</span>
              </span>
            </div>

            <div className="text-[#696970]">
              DPI: 300 • Vector Output • Deterministic Code
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
