"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import VisualSpecEditor from "../../components/VisualSpecEditor";
import { DesignSpec, Person, EventBrief } from "../../types";
import { generateDrafts } from "../../lib/api";

const FALLBACK_SPEC: DesignSpec = {
  schema_version: "1.0",
  layout_name: "classic",
  theme_name: "clean_light",
  page: { width_mm: 54, height_mm: 86, bleed_mm: 3, safe_mm: 4 },
  event: {
    event_name: "SVNIT ACM Hackathon 2026",
    dates: "Oct 18, 2026",
    venue: "SVNIT Campus, Surat",
  },
  brand: {
    logos: {
      svnit: "assets/logos/svnit.svg",
      acm_nitsurat: "assets/logos/acm_nitsurat.svg",
    },
  },
  theme: {
    name: "clean_light",
    colors: {
      background: "#FFFFFF",
      primary: "#1F6FEB",
      secondary: "#EAF1FD",
      accent: "#38BDF8",
      text: "#0B1220",
    },
    fonts: { heading: "Poppins", body: "Inter" },
    role_colors: {
      participant: "#1F6FEB",
      organizer: "#D9480F",
      mentor: "#2F9E44",
      volunteer: "#8B5CF6",
    },
  },
  elements: [
    { id: "bg", type: "rect", x: 0, y: 0, w: 60, h: 92, fill: "background" },
    { id: "banner", type: "rect", x: 0, y: 0, w: 60, h: 24, fill: "primary" },
    { id: "logo_acm", type: "logo", src: "acm_nitsurat", x: 8, y: 4.5, w: 15, h: 15, fit: "contain" },
    { id: "logo_svnit", type: "logo", src: "svnit", x: 37, y: 4.5, w: 15, h: 15, fit: "contain" },
    { id: "photo", type: "photo", field: "photo", x: 16, y: 28, w: 28, h: 34, shape: "rounded", radius: 3 },
    { id: "line", type: "line", x1: 10, y1: 64.5, x2: 50, y2: 64.5, stroke: "accent", stroke_width: 0.4 },
    { id: "name", type: "text", field: "name", x: 7, y: 66, w: 46, max_lines: 2, min_font: 8, max_font: 14, align: "center", bold: true },
    { id: "role", type: "role_badge", field: "role", x: 15, y: 78, w: 30, h: 6 },
  ],
};

export default function StandaloneEditorPage() {
  const [currentSpec, setCurrentSpec] = useState<DesignSpec>(FALLBACK_SPEC);
  const [saveBanner, setSaveBanner] = useState<string | null>(null);

  // Attempt to load from localStorage or backend if available
  useEffect(() => {
    try {
      const saved = localStorage.getItem("card_studio_active_spec");
      if (saved) {
        setCurrentSpec(JSON.parse(saved));
      } else {
        const briefPayload: EventBrief = {
          design_type: "id_card",
          event_name: "SVNIT ACM Hackathon 2026",
          tagline: "Code the Future",
          dates: "Oct 18, 2026",
          venue: "SVNIT Campus, Surat",
          roles: ["participant", "organizer", "mentor"],
          counts: null,
          fields_to_show: ["name", "role", "photo", "id", "team"],
          card_size: "54x86",
          orientation: "portrait",
          style_hint: null,
          lanyard_hole: null,
        };
        generateDrafts(briefPayload, 1)
          .then((res) => {
            if (res.drafts && res.drafts.length > 0) {
              setCurrentSpec(res.drafts[0]);
            }
          })
          .catch(() => {
            // Keep fallback
          });
      }
    } catch {
      // Fallback
    }
  }, []);

  function handleApplySpec(updatedSpec: DesignSpec) {
    setCurrentSpec(updatedSpec);
    try {
      localStorage.setItem("card_studio_active_spec", JSON.stringify(updatedSpec));
      setSaveBanner("Design Spec successfully saved! It will be used in the 5-step studio pipeline.");
      setTimeout(() => setSaveBanner(null), 5000);
    } catch {
      // ignore storage failure
    }
  }

  return (
    <div className="min-h-screen bg-[#232324] text-[#FAFAFA] flex flex-col p-4 sm:p-6 lg:p-8">
      {/* Top Breadcrumb & Return Nav */}
      <div className="max-w-7xl mx-auto w-full mb-4 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center space-x-2 text-xs font-semibold text-[#A1A1AA] hover:text-white px-3.5 py-1.5 rounded-full border border-white/10 bg-[#0E0E10] transition"
        >
          <span>←</span>
          <span>Back to ACM ID Card Studio</span>
        </Link>

        <span className="text-xs font-mono text-[#696970]">
          Design Studio • Visual Layout & Theme Editor
        </span>
      </div>

      {saveBanner && (
        <div className="max-w-7xl mx-auto w-full mb-4 bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs px-4 py-2.5 rounded-xl flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span>✓</span>
            <span className="font-semibold">{saveBanner}</span>
          </div>
          <button onClick={() => setSaveBanner(null)} className="text-emerald-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Editor Main Canvas */}
      <div className="max-w-7xl mx-auto w-full flex-1">
        <VisualSpecEditor initialSpec={currentSpec} onApplySpec={handleApplySpec} />
      </div>
    </div>
  );
}
