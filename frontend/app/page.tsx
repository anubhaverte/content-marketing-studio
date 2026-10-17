"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import VisualSpecEditor from "../components/VisualSpecEditor";
import {
  checkBackendHealth,
  submitBrief,
  uploadAttendeeCsv,
  generateDrafts,
  renderPreview,
  renderBatch,
  renderPrintSheet,
  ApiError,
} from "../lib/api";
import { parseCsvText } from "../lib/csv";
import {
  BriefResponse,
  DataSummary,
  DesignSpec,
  EventBrief,
  Person,
  QAIssue,
} from "../types";

const FALLBACK_DEFAULT_SPEC: DesignSpec = {
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

export default function CardStudioApp() {
  // Navigation
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Backend status
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [backendVersion, setBackendVersion] = useState<string>("");
  const [globalError, setGlobalError] = useState<string | null>(null);

  // Step 1: Brief State
  const [briefText, setBriefText] = useState<string>(
    "SVNIT ACM Hackathon 2026. Dates: Oct 10-12, 2026. Venue: SVNIT Campus, Surat. Tagline: Code the Future. Roles: Participant, Organizer, Mentor."
  );
  const [briefLoading, setBriefLoading] = useState<boolean>(false);
  const [briefResponse, setBriefResponse] = useState<BriefResponse | null>(null);
  const [questionAnswers, setQuestionAnswers] = useState<Record<string, string>>({});

  // Step 2: Attendee Data State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvUploading, setCsvUploading] = useState<boolean>(false);
  const [dataSummary, setDataSummary] = useState<DataSummary | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [skippedRows, setSkippedRows] = useState<Record<string, any>[]>([]);

  // Step 3: Drafts State
  const [draftsLoading, setDraftsLoading] = useState<boolean>(false);
  const [drafts, setDrafts] = useState<DesignSpec[]>([]);
  const [selectedDraftIndex, setSelectedDraftIndex] = useState<number>(0);
  const [draftsMock, setDraftsMock] = useState<boolean>(false);
  const [draftLayoutFilter, setDraftLayoutFilter] = useState<string>("all");
  const [draftThemeFilter, setDraftThemeFilter] = useState<string>("all");
  const [step3ViewMode, setStep3ViewMode] = useState<"matrix" | "grid">("matrix");

  // Step 4: Preview & Visual Spec Editor State
  const [step4ViewMode, setStep4ViewMode] = useState<"editor" | "preview">("editor");
  const [specCustomizedBanner, setSpecCustomizedBanner] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewSvg, setPreviewSvg] = useState<string>("");
  const [previewIssues, setPreviewIssues] = useState<QAIssue[]>([]);
  const [currentPersonIndex, setCurrentPersonIndex] = useState<number>(0);
  const [showDebugGuides, setShowDebugGuides] = useState<boolean>(false);

  // Step 5: Export State
  const [exportMode, setExportMode] = useState<"batch" | "print_sheet">("batch");
  const [exportFormat, setExportFormat] = useState<"pdf" | "png" | "svg">("pdf");
  const [exportOrientation, setExportOrientation] = useState<"portrait" | "landscape">("portrait");
  const [collatePdf, setCollatePdf] = useState<boolean>(false);
  const [exportDpi, setExportDpi] = useState<number>(300);
  const [exportBleed, setExportBleed] = useState<boolean>(true);
  const [printSheetPage, setPrintSheetPage] = useState<"A4" | "A3">("A4");
  const [printSheetCropMarks, setPrintSheetCropMarks] = useState<boolean>(true);
  const [exportLoading, setExportLoading] = useState<boolean>(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  // Check health on mount
  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    setBackendStatus("checking");
    setGlobalError(null);
    try {
      const res = await checkBackendHealth();
      setBackendStatus("online");
      setBackendVersion(res.version || "0.0.1");
    } catch (err: any) {
      setBackendStatus("offline");
      setGlobalError(
        "Unable to connect to the Card Studio rendering engine at http://localhost:8000. Please ensure backend services are started."
      );
    }
  }

  // --- Handlers ---

  async function handleBriefSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!briefText.trim()) return;

    setBriefLoading(true);
    setGlobalError(null);
    try {
      const res = await submitBrief(briefText);
      setBriefResponse(res);
      // Auto-populate initial question defaults
      const defaults: Record<string, string> = {};
      res.questions.forEach((q) => {
        if (q.default !== null && q.default !== undefined) {
          defaults[q.field] = String(q.default);
        }
      });
      setQuestionAnswers(defaults);

      // Automatically query /drafts with count=9 so all 9 combos are ranked by NLP brief score
      await handleFetchDrafts(res.brief, 9);
    } catch (err: any) {
      setGlobalError(`Brief extraction failed: ${err.detail || err.message}`);
    } finally {
      setBriefLoading(false);
    }
  }

  function handleAnswerChange(field: string, val: string) {
    setQuestionAnswers((prev) => ({ ...prev, [field]: val }));
    if (briefResponse) {
      setBriefResponse({
        ...briefResponse,
        brief: {
          ...briefResponse.brief,
          [field]: val,
        },
      });
    }
  }

  async function handleCsvSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    setGlobalError(null);
    setCsvUploading(true);

    try {
      // 1. Backend validation upload
      const summary = await uploadAttendeeCsv(file);
      setDataSummary(summary);

      // 2. Client-side parse for preview navigation & batch input
      const text = await file.text();
      const parsed = parseCsvText(text, summary.column_mapping);
      setPeople(parsed.people);
      setSkippedRows(parsed.skippedRows);
    } catch (err: any) {
      setGlobalError(`CSV upload failed: ${err.detail || err.message}`);
    } finally {
      setCsvUploading(false);
    }
  }

  function loadSampleData() {
    // Provide a sample roster if user doesn't have a CSV handy
    const samplePeople: Person[] = [
      { name: "Aarav Sharma", role: "organizer", id: "ORG-001", team: "Lead Core", email: "aarav@svnit.ac.in", photo: "photos/wide.png" },
      { name: "Diya Patel", role: "participant", id: "PART-101", team: "Binary Beasts", email: "diya@example.com", photo: "photos/tall.png" },
      { name: "Rohan Verma", role: "mentor", id: "MEN-050", team: "AI / ML Track", email: "rohan.v@tech.com" },
      { name: "Ananya Iyer", role: "participant", id: "PART-102", team: "CyberKnights", email: "ananya@example.com" },
    ];
    setPeople(samplePeople);
    setSkippedRows([]);
    setDataSummary({
      people_loaded: samplePeople.length,
      column_mapping: { name: "name", role: "role", id: "id", team: "team", email: "email", photo: "photo" },
      issues: { missing_names: 0, invalid_roles: 0, duplicate_ids: 0 },
      warnings: [],
      mock: false,
    });
  }

  async function handleFetchDrafts(explicitBrief?: EventBrief, count = 9) {
    setDraftsLoading(true);
    setGlobalError(null);

    const brief: EventBrief = explicitBrief || briefResponse?.brief || {
      design_type: "id_card",
      event_name: "SVNIT ACM Hackathon 2026",
      tagline: "Code the Future",
      dates: "Oct 10-12, 2026",
      venue: "SVNIT Campus, Surat",
      roles: ["participant", "organizer", "mentor", "volunteer"],
      counts: null,
      fields_to_show: ["name", "role", "id", "team", "photo", "qr"],
      card_size: "standard",
      orientation: "portrait",
      style_hint: null,
      lanyard_hole: true,
    };

    try {
      const res = await generateDrafts(brief, count);
      setDrafts(res.drafts);
      setDraftsMock(Boolean(res.mock));
      setSelectedDraftIndex(0); // Top NLP auto-selected draft
    } catch (err: any) {
      setGlobalError(`Draft generation failed: ${err.detail || err.message}`);
    } finally {
      setDraftsLoading(false);
    }
  }

  async function handleRenderPreview() {
    if (drafts.length === 0) return;
    const spec = drafts[selectedDraftIndex];
    const person = people[currentPersonIndex] || {
      name: "Alex Mercer",
      role: "participant",
      id: "DEMO-001",
      team: "SVNIT ACM",
      email: "alex@example.com",
    };

    setPreviewLoading(true);
    setGlobalError(null);
    try {
      const res = await renderPreview(spec, person, showDebugGuides);
      setPreviewSvg(res.svg);
      setPreviewIssues(res.qa_issues);
    } catch (err: any) {
      setGlobalError(`Preview rendering failed: ${err.detail || err.message}`);
    } finally {
      setPreviewLoading(false);
    }
  }

  // Trigger preview when draft, attendee, or guides toggle changes
  useEffect(() => {
    if (currentStep === 4 && drafts.length > 0) {
      handleRenderPreview();
    }
  }, [currentStep, selectedDraftIndex, currentPersonIndex, showDebugGuides]);

  async function handleBatchExport() {
    if (drafts.length === 0) {
      setGlobalError("Please select a design draft first.");
      return;
    }

    const spec = drafts[selectedDraftIndex];
    const exportPeople = people.length > 0 ? people : [
      { name: "Alex Mercer", role: "participant", id: "DEMO-001", team: "SVNIT ACM" }
    ];

    setExportLoading(true);
    setExportSuccess(null);
    setGlobalError(null);

    if (exportMode === "print_sheet") {
      try {
        const result = await renderPrintSheet(
          spec,
          exportPeople,
          printSheetPage,
          printSheetCropMarks
        );

        const url = window.URL.createObjectURL(result.blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        setExportSuccess(
          `Successfully downloaded ${result.filename}! Exported ${result.totalCards} cards across ${result.totalPages} imposed ${printSheetPage} sheet(s) with commercial crop marks.`
        );
      } catch (err: any) {
        setGlobalError(`Print sheet export failed: ${err.detail || err.message}`);
      } finally {
        setExportLoading(false);
      }
      return;
    }

    try {
      const result = await renderBatch({
        spec,
        people: exportPeople,
        settings: {
          format: exportFormat,
          dpi: exportDpi,
          orientation: exportOrientation,
          bleed: exportBleed,
        },
        collate_pdf: collatePdf,
        skipped_rows: skippedRows,
        return_json: false,
      });

      // Trigger native browser download
      const url = window.URL.createObjectURL(result.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setExportSuccess(
        `Successfully downloaded ${result.filename}! Exported: ${result.exportedCount} cards. QA Issues: ${result.qaIssueCount}. Failed: ${result.failedCount}.`
      );
    } catch (err: any) {
      setGlobalError(`Batch export failed: ${err.detail || err.message}`);
    } finally {
      setExportLoading(false);
    }
  }

  const steps = [
    { num: 1, label: "Event Brief" },
    { num: 2, label: "Attendee Data" },
    { num: 3, label: "Design Drafts" },
    { num: 4, label: "Badge Preview" },
    { num: 5, label: "Batch Export" },
  ];

  return (
    <div className="min-h-screen bg-[#232324] text-[#FAFAFA] flex flex-col font-sans selection:bg-white/20">
      {/* Top Navbar */}
      <header className="bg-[#0E0E10] border-b border-white/10 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-[#181818] border border-white/10 flex items-center justify-center p-1 shadow-sm">
              <img
                src="/logos/acm_nitsurat.svg"
                alt="ACM NIT Surat"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-sm font-semibold tracking-tight text-[#FAFAFA] leading-none">
                  ACM ID Card Studio
                </h1>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[#A1A1AA]">
                  Console
                </span>
              </div>
              <p className="text-xs text-[#696970] font-medium mt-0.5">
                ACM NIT Surat Creative & Print-Production Workspace
              </p>
            </div>
          </div>

          {/* Actions & Backend Status indicator */}
          <div className="flex items-center space-x-3">
            <Link
              href="/editor"
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-[#FAFAFA] text-xs font-medium transition"
              title="Open full-screen Design Studio"
            >
              <span>🎨</span>
              <span className="hidden sm:inline">Design Studio</span>
            </Link>

            <div className="inline-flex items-center space-x-2 text-xs font-medium px-3.5 py-1.5 rounded-full border border-white/15 bg-white/5 text-[#FAFAFA]">
              <span
                className={`w-2 h-2 rounded-full ${
                  backendStatus === "online"
                    ? "bg-emerald-400 animate-pulse"
                    : backendStatus === "checking"
                    ? "bg-amber-400"
                    : "bg-rose-500"
                }`}
              />
              <span className="text-[#FAFAFA]">
                {backendStatus === "online"
                  ? `Live v${backendVersion}`
                  : backendStatus === "checking"
                  ? "Checking..."
                  : "Offline (:8000)"}
              </span>
            </div>
            {backendStatus === "offline" && (
              <button
                onClick={checkHealth}
                className="text-xs border border-white/15 hover:bg-white/10 text-[#FAFAFA] px-3 py-1 rounded-full transition font-medium"
              >
                Retry
              </button>
            )}
          </div>
        </div>
        {/* Subtle Langbase Aurora gradient accent line */}
        <div className="h-[2px] w-full aurora-accent opacity-85" />
      </header>

      {/* Global Error Banner */}
      {globalError && (
        <div className="bg-rose-950/60 border-b border-rose-800/40 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-rose-300 font-mono">
            <div className="flex items-center space-x-2">
              <span className="font-bold">Notice:</span>
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => setGlobalError(null)}
              className="text-rose-400 hover:text-white font-bold ml-4"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col w-full">
        {/* Step Wizard Bar */}
        <nav aria-label="Progress" className="mb-8">
          <ol className="flex items-center justify-between w-full border border-white/10 rounded-full bg-[#0E0E10] p-1.5 shadow-sm">
            {steps.map((step, idx) => {
              const isActive = currentStep === step.num;
              const isPast = currentStep > step.num;
              return (
                <li key={step.num} className="flex-1 relative flex items-center">
                  <button
                    onClick={() => setCurrentStep(step.num)}
                    className="flex items-center justify-center space-x-2.5 w-full group focus:outline-none py-1.5 px-3 rounded-full transition"
                  >
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-mono font-bold transition ${
                        isActive
                          ? "bg-white text-black shadow-sm"
                          : isPast
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          : "bg-[#181818] border border-white/10 text-[#696970] group-hover:text-[#A1A1AA]"
                      }`}
                    >
                      {isPast ? "✓" : step.num}
                    </span>
                    <span
                      className={`text-xs font-medium transition ${
                        isActive
                          ? "text-[#FAFAFA] font-semibold"
                          : isPast
                          ? "text-[#A1A1AA] group-hover:text-white"
                          : "text-[#696970] group-hover:text-[#A1A1AA]"
                      }`}
                    >
                      {step.label}
                    </span>
                  </button>
                  {idx < steps.length - 1 && (
                    <div className="hidden md:block w-4 h-px bg-white/10 mx-1" />
                  )}
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Content Area */}
        <main className="flex-1 bg-[#1E1E20] border border-white/10 rounded-2xl p-6 sm:p-8 shadow-2xl">
          {/* STEP 1: EVENT BRIEF */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-[#FAFAFA]">Step 1: Event Details & Configuration</h2>
                <p className="text-xs text-[#A1A1AA] mt-1">
                  Enter your event overview to automatically tailor badge metadata, brand themes, and role configurations.
                </p>
              </div>

              <form onSubmit={handleBriefSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#A1A1AA] mb-2">
                    Event Overview
                  </label>
                  <textarea
                    rows={4}
                    value={briefText}
                    onChange={(e) => setBriefText(e.target.value)}
                    placeholder="Enter event name, dates, venue, tagline, and attendee roles..."
                    className="w-full rounded-xl border border-white/10 bg-[#181818] p-4 text-sm text-[#FAFAFA] placeholder-[#696970] focus:border-white/30 focus:outline-none transition font-sans"
                  />
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    type="submit"
                    disabled={briefLoading || !briefText.trim()}
                    className="px-5 py-2.5 bg-[#FAFAFA] hover:bg-white text-[#0E0E10] text-xs font-semibold rounded-full shadow-sm transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {briefLoading ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                        <span>Analyzing Event...</span>
                      </>
                    ) : (
                      <span>Analyze & Configure Event</span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setBriefText(
                        "ACM NIT Surat Hackathon 2026. Dates: 10-12 October 2026. Venue: SVNIT Campus, Surat. Tagline: Code Innovate Elevate. Roles: Participant, Organizer, Mentor, Volunteer."
                      );
                    }}
                    className="text-xs text-[#A1A1AA] hover:text-white border border-white/15 hover:bg-white/5 font-medium px-4 py-2 rounded-full transition"
                  >
                    Load Sample Event Details
                  </button>
                </div>
              </form>

              {/* Extraction Results */}
              {briefResponse && (
                <div className="mt-8 border border-white/10 rounded-xl p-5 bg-[#181818] space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-white/10">
                    <h3 className="font-semibold text-[#FAFAFA] text-xs uppercase tracking-wider font-mono">
                      Event Specification Profile
                    </h3>
                    <span
                      className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full ${
                        briefResponse.mock
                          ? "bg-white/10 text-[#FAFAFA] border border-white/15"
                          : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {briefResponse.mock ? "Standard Extraction" : "AI Analyzed"}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="font-mono text-[#696970] block">Event Name</span>
                      <p className="font-medium text-[#FAFAFA] mt-0.5">
                        {briefResponse.brief.event_name || (
                          <span className="text-amber-400 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-mono text-[#696970] block">Dates</span>
                      <p className="font-medium text-[#FAFAFA] mt-0.5">
                        {briefResponse.brief.dates || (
                          <span className="text-amber-400 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-mono text-[#696970] block">Venue</span>
                      <p className="font-medium text-[#FAFAFA] mt-0.5">
                        {briefResponse.brief.venue || (
                          <span className="text-amber-400 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-mono text-[#696970] block">Tagline</span>
                      <p className="font-medium text-[#FAFAFA] mt-0.5">
                        {briefResponse.brief.tagline || (
                          <span className="text-[#696970] italic">None specified</span>
                        )}
                      </p>
                    </div>
                    {briefResponse.brief.style_hint && (
                      <div className="md:col-span-2">
                        <span className="font-mono text-[#696970] block">Aesthetic Style Theme</span>
                        <p className="font-medium text-[#C7B8F5] mt-0.5">
                          ✨ {briefResponse.brief.style_hint}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Recommendation Callout */}
                  {drafts.length > 0 && (
                    <div className="bg-[#0E0E10] border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-base">✨</span>
                          <span className="font-mono text-xs uppercase tracking-wider text-[#FAFAFA]">
                            Recommended Template: Profile #1
                          </span>
                        </div>
                        <p className="text-xs text-[#A1A1AA] mt-1">
                          Automated design intelligence matched layout{" "}
                          <strong className="font-semibold text-white">
                            {drafts[0].layout_name.toUpperCase()}
                          </strong>{" "}
                          with theme{" "}
                          <strong className="font-semibold text-white">
                            {drafts[0].theme_name.replace("_", " ").toUpperCase()}
                          </strong>{" "}
                          as the optimal profile for &ldquo;{briefResponse.brief.event_name}&rdquo;.
                        </p>
                      </div>
                      <div className="flex items-center space-x-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedDraftIndex(0);
                            setCurrentStep(3);
                          }}
                          className="px-4 py-1.5 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-xs transition"
                        >
                          View 9 Combos in Drafts →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Clarification Questions */}
                  {briefResponse.questions.length > 0 && (
                    <div className="pt-4 border-t border-white/10 space-y-3">
                      <h4 className="text-xs font-mono uppercase tracking-wider text-[#A1A1AA]">
                        Missing Information Questions ({briefResponse.questions.length})
                      </h4>
                      <div className="space-y-3">
                        {briefResponse.questions.map((q) => (
                          <div
                            key={q.field}
                            className="bg-[#0E0E10] p-3.5 rounded-lg border border-white/10 text-xs space-y-1.5"
                          >
                            <label className="font-medium text-[#FAFAFA] block">
                              {q.text} {!q.skippable && <span className="text-rose-400">*</span>}
                            </label>
                            <input
                              type="text"
                              value={questionAnswers[q.field] || ""}
                              onChange={(e) => handleAnswerChange(q.field, e.target.value)}
                              placeholder={`Enter ${q.field}...`}
                              className="w-full rounded-md border border-white/10 bg-[#181818] text-[#FAFAFA] px-3 py-1.5 text-xs focus:border-white/30 focus:outline-none"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-3 flex justify-end">
                    <button
                      onClick={() => setCurrentStep(2)}
                      className="px-5 py-2 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-sm transition"
                    >
                      Proceed to Attendee Data →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: ATTENDEE DATA */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-[#FAFAFA]">Step 2: Attendee Directory & Verification</h2>
                <p className="text-xs text-[#A1A1AA] mt-1">
                  Import participant records via CSV or load sample attendees. Column mapping, role classifications, and portrait photos are automatically validated for print compliance.
                </p>
              </div>

              {/* Upload Dropzone */}
              <div className="border-2 border-dashed border-white/15 rounded-2xl p-8 text-center hover:border-white/30 transition bg-[#181818]">
                <input
                  type="file"
                  accept=".csv"
                  id="csv-upload"
                  onChange={handleCsvSelect}
                  className="hidden"
                />
                <label
                  htmlFor="csv-upload"
                  className="cursor-pointer flex flex-col items-center justify-center space-y-2"
                >
                  <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 text-white flex items-center justify-center text-xl font-bold">
                    📄
                  </div>
                  <span className="text-sm font-semibold text-[#FAFAFA]">
                    {csvFile ? csvFile.name : "Click to select attendee CSV file"}
                  </span>
                  <span className="text-xs text-[#696970]">
                    Supports standard UTF-8 CSV, auto column mapping, and roles (Participant, Organizer, Mentor, Volunteer)
                  </span>
                </label>

                <div className="mt-4 flex items-center justify-center space-x-3">
                  <button
                    type="button"
                    onClick={loadSampleData}
                    className="text-xs bg-white/10 border border-white/15 hover:bg-white/15 text-[#FAFAFA] font-medium px-4 py-2 rounded-full shadow-sm transition"
                  >
                    Load Demo Roster (4 Attendees)
                  </button>
                </div>
              </div>

              {/* Validation Summary */}
              {dataSummary && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-[#181818] border border-white/10 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-[#696970] font-mono uppercase">Loaded</span>
                      <p className="text-xl font-bold text-[#FAFAFA] mt-0.5">
                        {dataSummary.people_loaded}
                      </p>
                    </div>
                    <div className="bg-[#181818] border border-white/10 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-[#696970] font-mono uppercase">Missing Names</span>
                      <p className="text-xl font-bold text-rose-400 mt-0.5">
                        {dataSummary.issues.missing_names || 0}
                      </p>
                    </div>
                    <div className="bg-[#181818] border border-white/10 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-[#696970] font-mono uppercase">Invalid Roles</span>
                      <p className="text-xl font-bold text-amber-400 mt-0.5">
                        {dataSummary.issues.unknown_roles ?? dataSummary.issues.invalid_roles ?? 0}
                      </p>
                    </div>
                    <div className="bg-[#181818] border border-white/10 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-[#696970] font-mono uppercase">Duplicate IDs</span>
                      <p className="text-xl font-bold text-[#FAFAFA] mt-0.5">
                        {dataSummary.issues.duplicate_ids || 0}
                      </p>
                    </div>
                  </div>

                  {/* Warnings List */}
                  {dataSummary.warnings.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs space-y-1">
                      <span className="font-semibold text-amber-300 block font-mono">Validation Warnings:</span>
                      <ul className="list-disc list-inside text-amber-200/80 space-y-0.5">
                        {dataSummary.warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Attendee Table Preview */}
                  {people.length > 0 && (
                    <div className="border border-white/10 rounded-xl overflow-hidden bg-[#181818]">
                      <div className="bg-[#121214] px-4 py-3 border-b border-white/10 flex justify-between items-center">
                        <span className="text-xs font-mono text-[#A1A1AA] uppercase tracking-wider">
                          Attendee Records Preview ({people.length})
                        </span>
                        {skippedRows.length > 0 && (
                          <span className="text-xs text-rose-400 font-mono">
                            {skippedRows.length} rows skipped
                          </span>
                        )}
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-[#0E0E10] text-[#A1A1AA] font-mono sticky top-0 border-b border-white/10">
                            <tr>
                              <th className="px-4 py-2">ID</th>
                              <th className="px-4 py-2">Name</th>
                              <th className="px-4 py-2">Role</th>
                              <th className="px-4 py-2">Team</th>
                              <th className="px-4 py-2">Photo Path</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5">
                            {people.slice(0, 10).map((p, idx) => (
                              <tr key={idx} className="hover:bg-white/5 transition">
                                <td className="px-4 py-2 font-mono text-[#696970]">{p.id || "—"}</td>
                                <td className="px-4 py-2 font-medium text-[#FAFAFA]">{p.name}</td>
                                <td className="px-4 py-2">
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-semibold border ${
                                      p.role === "organizer"
                                        ? "bg-orange-500/10 text-orange-400 border-orange-500/30"
                                        : p.role === "mentor"
                                        ? "bg-green-500/10 text-green-400 border-green-500/30"
                                        : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                                    }`}
                                  >
                                    {p.role || "participant"}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-[#A1A1AA]">{p.team || "—"}</td>
                                <td className="px-4 py-2 font-mono text-[#696970] truncate max-w-xs">
                                  {p.photo || "Initials fallback"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-2">
                    <button
                      onClick={() => setCurrentStep(1)}
                      className="px-4 py-2 border border-white/15 hover:bg-white/5 text-[#A1A1AA] hover:text-white text-xs font-semibold rounded-full transition"
                    >
                      ← Back to Brief
                    </button>
                    <button
                      onClick={() => {
                        handleFetchDrafts();
                        setCurrentStep(3);
                      }}
                      className="px-5 py-2 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-sm transition"
                    >
                      Generate Design Drafts →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: DESIGN DRAFTS & 9 COMBINATIONS */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-[#FAFAFA]">Step 3: Design Templates & Styling</h2>
                  <p className="text-xs text-[#A1A1AA] mt-1">
                    Select among curated combinations of structural layouts (Classic, Minimal, Split) and tailored brand palettes.
                  </p>
                </div>
                
                {/* View Switcher: Matrix vs Card Grid */}
                <div className="flex border border-white/10 rounded-full p-1 bg-[#181818]">
                  <button
                    onClick={() => setStep3ViewMode("matrix")}
                    className={`px-3.5 py-1 rounded-full text-xs font-medium transition flex items-center space-x-1.5 ${
                      step3ViewMode === "matrix"
                        ? "bg-white text-black font-semibold shadow-xs"
                        : "text-[#A1A1AA] hover:text-white"
                    }`}
                  >
                    <span>✨</span>
                    <span>3×3 Combos Matrix</span>
                  </button>
                  <button
                    onClick={() => setStep3ViewMode("grid")}
                    className={`px-3.5 py-1 rounded-full text-xs font-medium transition flex items-center space-x-1.5 ${
                      step3ViewMode === "grid"
                        ? "bg-white text-black font-semibold shadow-xs"
                        : "text-[#A1A1AA] hover:text-white"
                    }`}
                  >
                    <span>🗂️</span>
                    <span>Card Grid ({drafts.length})</span>
                  </button>
                </div>
              </div>

              {/* Recommendation Callout Banner */}
              {drafts.length > 0 && (
                <div className="bg-[#0E0E10] border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 text-white flex items-center justify-center text-lg font-bold shadow-xs shrink-0">
                      ✨
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono uppercase tracking-wider text-[#FAFAFA]">
                          Recommended Template: Profile #1
                        </span>
                        <span className="bg-white/10 text-white border border-white/20 text-[10px] font-mono px-2 py-0.5 rounded-full">
                          Featured
                        </span>
                      </div>
                      <p className="text-xs text-[#A1A1AA] mt-0.5">
                        Style intelligence selected <strong className="text-white font-semibold">{drafts[0]?.layout_name.toUpperCase()}</strong> layout with <strong className="text-white font-semibold">{drafts[0]?.theme_name.replace("_", " ").toUpperCase()}</strong> theme as the recommended profile for &ldquo;{briefResponse?.brief.event_name || "Event"}&rdquo;.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedDraftIndex(0)}
                    className={`px-4 py-1.5 rounded-full text-xs font-semibold transition shrink-0 ${
                      selectedDraftIndex === 0
                        ? "bg-white text-black shadow-xs"
                        : "bg-white/5 border border-white/15 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                    }`}
                  >
                    {selectedDraftIndex === 0 ? "✓ Recommended Active" : "Apply Recommendation"}
                  </button>
                </div>
              )}

              {draftsLoading ? (
                <div className="py-16 text-center space-y-3">
                  <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-[#A1A1AA] font-mono">Generating design templates and style variations...</p>
                </div>
              ) : drafts.length === 0 ? (
                <div className="text-center py-12 border border-white/10 rounded-xl bg-[#181818] space-y-3">
                  <p className="text-sm text-[#A1A1AA]">No design drafts loaded yet.</p>
                  <button
                    onClick={() => handleFetchDrafts(undefined, 9)}
                    className="px-5 py-2 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-sm transition"
                  >
                    Generate 9 Combinations Now
                  </button>
                </div>
              ) : step3ViewMode === "matrix" ? (
                /* 3x3 COMBINATIONS MATRIX VIEW */
                <div className="space-y-4">
                  <div className="overflow-x-auto border border-white/10 rounded-2xl bg-[#181818]">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-[#121214] border-b border-white/10">
                          <th className="p-4 text-xs font-mono uppercase tracking-wider text-[#A1A1AA] w-44">
                            Layout \ Theme
                          </th>
                          {[
                            { id: "clean_light", label: "Clean Light", primary: "#1F6FEB" },
                            { id: "dark_tech", label: "Dark Tech", primary: "#58A6FF" },
                            { id: "bold_event", label: "Bold Event", primary: "#D9480F" },
                          ].map((theme) => (
                            <th key={theme.id} className="p-4 border-l border-white/10 text-center">
                              <div className="flex items-center justify-center space-x-2">
                                <span
                                  className="w-3.5 h-3.5 rounded-full border border-white/20 inline-block"
                                  style={{ backgroundColor: theme.primary }}
                                />
                                <span className="text-xs font-semibold text-[#FAFAFA]">{theme.label}</span>
                              </div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/10">
                        {[
                          { id: "classic", label: "Classic", icon: "🏛️", desc: "Top colored header band & centered logos" },
                          { id: "minimal", label: "Minimal", icon: "✨", desc: "Sleek hairline divider & side-by-side logos" },
                          { id: "split", label: "Split", icon: "🌗", desc: "Two-tone split cards with high contrast" },
                        ].map((layout) => (
                          <tr key={layout.id} className="hover:bg-white/5 transition">
                            <td className="p-4 align-top">
                              <div className="flex items-center space-x-2">
                                <span className="text-base">{layout.icon}</span>
                                <span className="text-xs font-semibold text-[#FAFAFA]">{layout.label}</span>
                              </div>
                              <p className="text-[11px] text-[#696970] mt-1">{layout.desc}</p>
                            </td>

                            {["clean_light", "dark_tech", "bold_event"].map((themeId) => {
                              const draftIdx = drafts.findIndex(
                                (d) => d.layout_name === layout.id && d.theme_name === themeId
                              );
                              const isTopNLP = draftIdx === 0;
                              const isSelected = draftIdx !== -1 && selectedDraftIndex === draftIdx;
                              const currentDraft = draftIdx !== -1 ? drafts[draftIdx] : null;
                              const colors = currentDraft?.theme?.colors || {
                                primary: "#1F6FEB",
                                secondary: "#EAF1FD",
                                background: "#FFFFFF",
                                text: "#0B1220",
                              };

                              return (
                                <td
                                  key={themeId}
                                  className={`p-4 border-l border-white/10 text-center transition cursor-pointer ${
                                    isSelected
                                      ? "bg-white/10 ring-1 ring-white/30"
                                      : "hover:bg-white/5"
                                  }`}
                                  onClick={() => {
                                    if (draftIdx !== -1) setSelectedDraftIndex(draftIdx);
                                  }}
                                >
                                  <div className="flex flex-col items-center space-y-2">
                                    <div className="flex items-center space-x-1.5">
                                      {isTopNLP && (
                                        <span className="bg-amber-500/10 text-amber-300 text-[10px] font-mono px-2 py-0.5 rounded-full border border-amber-500/30">
                                          ✨ Recommended
                                        </span>
                                      )}
                                      {isSelected && (
                                        <span className="bg-white text-black text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                                          Active
                                        </span>
                                      )}
                                    </div>

                                    {/* Palette chips */}
                                    <div className="flex space-x-1 p-1 rounded-lg border border-white/10 bg-[#121214]">
                                      <div
                                        className="w-3.5 h-3.5 rounded-xs border border-white/10"
                                        style={{ backgroundColor: colors.background }}
                                        title="Background"
                                      />
                                      <div
                                        className="w-3.5 h-3.5 rounded-xs border border-white/10"
                                        style={{ backgroundColor: colors.primary }}
                                        title="Primary"
                                      />
                                      <div
                                        className="w-3.5 h-3.5 rounded-xs border border-white/10"
                                        style={{ backgroundColor: colors.secondary }}
                                        title="Secondary"
                                      />
                                      <div
                                        className="w-3.5 h-3.5 rounded-xs border border-white/10"
                                        style={{ backgroundColor: colors.text }}
                                        title="Text"
                                      />
                                    </div>

                                    <div className="flex items-center space-x-1.5 pt-1">
                                      <button
                                        type="button"
                                        className={`px-3 py-1 rounded-full text-[11px] font-medium transition ${
                                          isSelected
                                            ? "bg-white text-black font-semibold"
                                            : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                                        }`}
                                      >
                                        {isSelected ? "Selected" : "Select"}
                                      </button>
                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          if (draftIdx !== -1) setSelectedDraftIndex(draftIdx);
                                          setStep4ViewMode("editor");
                                          setCurrentStep(4);
                                        }}
                                        className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-white/5 border border-white/15 text-[#A1A1AA] hover:text-white hover:bg-white/10 transition"
                                        title="Edit this combination in Visual Spec Editor"
                                      >
                                        🎨 Edit
                                      </button>
                                    </div>
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                /* CARD GRID VIEW WITH FILTERS */
                <div className="space-y-4">
                  {/* Filter bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 bg-[#181818] border border-white/10 rounded-xl p-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono uppercase text-[#696970]">Layout:</span>
                      {["all", "classic", "minimal", "split"].map((l) => (
                        <button
                          key={l}
                          onClick={() => setDraftLayoutFilter(l)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition capitalize ${
                            draftLayoutFilter === l
                              ? "bg-white text-black font-semibold shadow-xs"
                              : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                          }`}
                        >
                          {l}
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono uppercase text-[#696970]">Theme:</span>
                      {["all", "clean_light", "dark_tech", "bold_event"].map((t) => (
                        <button
                          key={t}
                          onClick={() => setDraftThemeFilter(t)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                            draftThemeFilter === t
                              ? "bg-white text-black font-semibold shadow-xs"
                              : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                          }`}
                        >
                          {t === "all" ? "All" : t.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {drafts
                      .map((draft, idx) => ({ draft, idx }))
                      .filter(({ draft }) => {
                        if (draftLayoutFilter !== "all" && draft.layout_name !== draftLayoutFilter) return false;
                        if (draftThemeFilter !== "all" && draft.theme_name !== draftThemeFilter) return false;
                        return true;
                      })
                      .map(({ draft, idx }) => {
                        const isSelected = selectedDraftIndex === idx;
                        const isTopNLP = idx === 0;
                        const colors = draft.theme?.colors || {
                          primary: "#1F6FEB",
                          secondary: "#EAF1FD",
                          background: "#FFFFFF",
                          accent: "#38BDF8",
                          text: "#0B1220",
                        };

                        return (
                          <div
                            key={idx}
                            onClick={() => setSelectedDraftIndex(idx)}
                            className={`cursor-pointer rounded-2xl border p-5 transition relative flex flex-col justify-between ${
                              isSelected
                                ? "border-white ring-1 ring-white bg-[#181818]"
                                : "border-white/10 hover:border-white/20 bg-[#181818]"
                            }`}
                          >
                            <div>
                              <div className="flex justify-between items-center mb-3">
                                <div className="flex items-center space-x-2">
                                  <span className="text-xs font-mono text-[#FAFAFA] font-semibold">
                                    Combo #{idx + 1}
                                  </span>
                                  {isTopNLP && (
                                    <span className="bg-amber-500/10 text-amber-300 text-[10px] font-mono px-2 py-0.5 rounded-full border border-amber-500/30">
                                      ✨ Recommended
                                    </span>
                                  )}
                                </div>
                                {isSelected && (
                                  <span className="text-xs font-mono font-bold text-black bg-white px-2 py-0.5 rounded-full">
                                    Selected
                                  </span>
                                )}
                              </div>

                              <div className="space-y-1.5 text-xs text-[#A1A1AA]">
                                <div className="flex justify-between">
                                  <span className="text-[#696970]">Layout:</span>
                                  <span className="font-semibold text-white capitalize">
                                    {draft.layout_name}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[#696970]">Theme:</span>
                                  <span className="font-semibold text-white capitalize">
                                    {draft.theme_name.replace("_", " ")}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[#696970]">Page:</span>
                                  <span className="font-mono">
                                    {draft.page.width_mm} × {draft.page.height_mm} mm
                                  </span>
                                </div>
                              </div>

                              {/* Swatches */}
                              <div className="mt-4 pt-4 border-t border-white/10">
                                <span className="text-[10px] font-mono text-[#696970] uppercase tracking-wider block mb-2">
                                  Color Palette
                                </span>
                                <div className="flex space-x-1.5">
                                  {Object.entries(colors).map(([key, val]) => (
                                    <div
                                      key={key}
                                      title={`${key}: ${val}`}
                                      className="w-6 h-6 rounded-md border border-white/10 shadow-xs"
                                      style={{ backgroundColor: String(val) }}
                                    />
                                  ))}
                                </div>
                              </div>
                            </div>

                            <div className="mt-5 space-y-2">
                              <button
                                type="button"
                                className={`w-full py-2 rounded-full text-xs font-semibold transition ${
                                  isSelected
                                    ? "bg-white text-black"
                                    : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                                }`}
                              >
                                {isSelected ? "Active Draft" : "Select This Combination"}
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedDraftIndex(idx);
                                  setStep4ViewMode("editor");
                                  setCurrentStep(4);
                                }}
                                className="w-full py-1.5 rounded-full text-xs font-medium bg-white/5 border border-white/15 text-[#A1A1AA] hover:text-white hover:bg-white/10 transition flex items-center justify-center space-x-1.5"
                              >
                                <span>🎨</span>
                                <span>Fine-tune in Spec Editor</span>
                              </button>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-white/10">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-4 py-2 border border-white/15 hover:bg-white/5 text-[#A1A1AA] hover:text-white text-xs font-semibold rounded-full transition"
                >
                  ← Back to Attendees
                </button>
                <button
                  disabled={drafts.length === 0}
                  onClick={() => setCurrentStep(4)}
                  className="px-5 py-2 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-sm transition disabled:opacity-40"
                >
                  Open Badge Studio →
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: BADGE PREVIEW & VISUAL SPEC EDITOR */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-[#FAFAFA]">Step 4: Badge Studio & Live Proofing</h2>
                  <p className="text-sm text-[#A1A1AA] mt-1">
                    Fine-tune layout geometry, typography, and visual branding with real-time vector proofing and automated QA inspection.
                  </p>
                </div>

                {/* View Mode Switcher */}
                <div className="flex border border-white/10 rounded-full p-1 bg-[#181818]">
                  <button
                    onClick={() => setStep4ViewMode("editor")}
                    className={`px-4 py-1.5 rounded-full text-xs font-semibold transition flex items-center space-x-1.5 ${
                      step4ViewMode === "editor"
                        ? "bg-white text-black shadow-xs"
                        : "text-[#A1A1AA] hover:text-white"
                    }`}
                  >
                    <span>🎨</span>
                    <span>Visual Design Studio</span>
                  </button>
                  <button
                    onClick={() => setStep4ViewMode("preview")}
                    className={`px-4 py-1.5 rounded-full text-xs font-semibold transition flex items-center space-x-1.5 ${
                      step4ViewMode === "preview"
                        ? "bg-white text-black shadow-xs"
                        : "text-[#A1A1AA] hover:text-white"
                    }`}
                  >
                    <span>🔍</span>
                    <span>Live Proof & QA Inspection</span>
                  </button>
                </div>
              </div>

              {/* Success Notification Banner */}
              {specCustomizedBanner && (
                <div className="bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-3 text-xs text-emerald-300 flex items-center justify-between shadow-xs">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold">✓</span>
                    <span>{specCustomizedBanner}</span>
                  </div>
                  <button
                    onClick={() => setSpecCustomizedBanner(null)}
                    className="text-emerald-400 hover:text-emerald-200 font-bold ml-2"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* VIEW MODE 1: VISUAL SPEC EDITOR */}
              {step4ViewMode === "editor" && (
                <VisualSpecEditor
                  initialSpec={drafts[selectedDraftIndex] || FALLBACK_DEFAULT_SPEC}
                  attendees={people}
                  onApplySpec={(updatedSpec) => {
                    const nextDrafts = drafts.length > 0 ? [...drafts] : [updatedSpec];
                    nextDrafts[selectedDraftIndex] = updatedSpec;
                    setDrafts(nextDrafts);
                    setSpecCustomizedBanner(
                      "Design Spec customized and saved to active draft! Your adjustments will be included in batch export."
                    );
                    setTimeout(() => setSpecCustomizedBanner(null), 6000);
                  }}
                />
              )}

              {/* VIEW MODE 2: QUICK PREVIEW & QA DIAGNOSTICS */}
              {step4ViewMode === "preview" && (
                <div className="space-y-6">
                  {/* Quick Layout & Theme Switcher (3x3 Combos) */}
                  <div className="bg-[#181818] border border-white/10 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-xs">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">Layout:</span>
                      {(["classic", "minimal", "split"] as const).map((l) => {
                        const currentDraft = drafts[selectedDraftIndex];
                        const isActive = currentDraft?.layout_name === l;
                        return (
                          <button
                            key={l}
                            type="button"
                            onClick={() => {
                              const currentTheme = currentDraft?.theme_name || "clean_light";
                              const targetIdx = drafts.findIndex(
                                (d) => d.layout_name === l && d.theme_name === currentTheme
                              );
                              if (targetIdx !== -1) {
                                setSelectedDraftIndex(targetIdx);
                              } else {
                                const fallbackIdx = drafts.findIndex((d) => d.layout_name === l);
                                if (fallbackIdx !== -1) setSelectedDraftIndex(fallbackIdx);
                              }
                            }}
                            className={`px-3 py-1 rounded-full text-xs font-semibold transition capitalize ${
                              isActive
                                ? "bg-white text-black shadow-xs"
                                : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                            }`}
                          >
                            {l}
                          </button>
                        );
                      })}
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">Theme:</span>
                      {(["clean_light", "dark_tech", "bold_event"] as const).map((t) => {
                        const currentDraft = drafts[selectedDraftIndex];
                        const isActive = currentDraft?.theme_name === t;
                        const label = t === "clean_light" ? "Clean Light" : t === "dark_tech" ? "Dark Tech" : "Bold Event";
                        return (
                          <button
                            key={t}
                            type="button"
                            onClick={() => {
                              const currentLayout = currentDraft?.layout_name || "classic";
                              const targetIdx = drafts.findIndex(
                                (d) => d.layout_name === currentLayout && d.theme_name === t
                              );
                              if (targetIdx !== -1) {
                                setSelectedDraftIndex(targetIdx);
                              } else {
                                const fallbackIdx = drafts.findIndex((d) => d.theme_name === t);
                                if (fallbackIdx !== -1) setSelectedDraftIndex(fallbackIdx);
                              }
                            }}
                            className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                              isActive
                                ? "bg-white text-black shadow-xs"
                                : "bg-white/5 border border-white/10 text-[#A1A1AA] hover:text-white hover:bg-white/10"
                            }`}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>

                    <div className="flex items-center space-x-2 text-[11px] text-[#A1A1AA] font-mono bg-white/5 px-3 py-1 rounded-full border border-white/10">
                      <span className="font-semibold text-white">Role Cues:</span>
                      <span title="Circle symbol for Participant">● Participant</span>
                      <span title="Square symbol for Organizer">■ Organizer</span>
                      <span title="Triangle symbol for Mentor">▲ Mentor</span>
                      <span title="Diamond symbol for Volunteer">◆ Volunteer</span>
                    </div>
                  </div>

                  {/* Attendee Selector & Guides Toggle */}
                  <div className="flex items-center justify-between bg-[#181818] border border-white/10 rounded-xl p-3">
                    <div className="flex items-center space-x-3">
                      <label className="flex items-center space-x-2 text-xs font-medium text-[#A1A1AA] cursor-pointer bg-white/5 px-3 py-1.5 rounded-full border border-white/10 hover:text-white transition">
                        <input
                          type="checkbox"
                          checked={showDebugGuides}
                          onChange={(e) => setShowDebugGuides(e.target.checked)}
                          className="rounded border-white/20 bg-[#121214] text-white focus:ring-0"
                        />
                        <span>Print Guides (Bleed/Trim/Safe)</span>
                      </label>
                    </div>

                    {people.length > 1 && (
                      <div className="flex items-center space-x-1 border border-white/10 rounded-full p-0.5 bg-white/5">
                        <button
                          onClick={() =>
                            setCurrentPersonIndex((prev) => (prev > 0 ? prev - 1 : people.length - 1))
                          }
                          className="px-2.5 py-1 text-xs font-bold text-[#A1A1AA] hover:text-white hover:bg-white/10 rounded-full transition"
                        >
                          ◀
                        </button>
                        <span className="text-xs font-mono px-2 text-[#FAFAFA]">
                          {currentPersonIndex + 1} / {people.length}
                        </span>
                        <button
                          onClick={() =>
                            setCurrentPersonIndex((prev) => (prev < people.length - 1 ? prev + 1 : 0))
                          }
                          className="px-2.5 py-1 text-xs font-bold text-[#A1A1AA] hover:text-white hover:bg-white/10 rounded-full transition"
                        >
                          ▶
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Attendee Info Card */}
                  {people[currentPersonIndex] && (
                    <div className="bg-[#181818] border border-white/10 rounded-xl p-3 flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-3">
                        <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center font-bold text-[#FAFAFA] border border-white/15">
                          {people[currentPersonIndex].name.charAt(0)}
                        </div>
                        <div>
                          <span className="font-bold text-[#FAFAFA]">
                            {people[currentPersonIndex].name}
                          </span>
                          <span className="text-white/20 mx-2">•</span>
                          <span className="text-[#A1A1AA] font-mono">
                            ID: {people[currentPersonIndex].id || "Auto"}
                          </span>
                          {people[currentPersonIndex].team && (
                            <>
                              <span className="text-white/20 mx-2">•</span>
                              <span className="text-[#A1A1AA] font-mono">
                                Team: {people[currentPersonIndex].team}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border ${
                          people[currentPersonIndex].role === "organizer"
                            ? "bg-amber-950/40 border-amber-500/30 text-amber-300"
                            : people[currentPersonIndex].role === "mentor"
                            ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
                            : "bg-sky-950/40 border-sky-500/30 text-sky-300"
                        }`}
                      >
                        {people[currentPersonIndex].role || "participant"}
                      </span>
                    </div>
                  )}

                  {/* Main Preview Workarea */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* SVG Canvas Area */}
                    <div className="lg:col-span-2 bg-[#121214] rounded-2xl p-8 flex items-center justify-center min-h-[500px] border border-white/10 shadow-2xl relative">
                      {previewLoading ? (
                        <div className="text-center space-y-3">
                          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
                          <p className="text-xs text-[#A1A1AA] font-mono">Rendering preview SVG from backend...</p>
                        </div>
                      ) : previewSvg ? (
                        <div
                          className="shadow-[0_20px_60px_rgba(0,0,0,0.6)] rounded-sm overflow-hidden bg-white max-w-sm w-full transition transform hover:scale-[1.01]"
                          dangerouslySetInnerHTML={{ __html: previewSvg }}
                        />
                      ) : (
                        <div className="text-center text-[#696970] text-xs font-mono">
                          No badge rendered yet. Select an attendee or click Preview Badge.
                        </div>
                      )}
                    </div>

                    {/* QA Checklist and Inspection Panel */}
                    <div className="space-y-4">
                      <div className="border border-white/10 rounded-xl p-4 bg-[#181818] shadow-xs">
                        <h3 className="text-xs font-bold text-[#FAFAFA] uppercase tracking-wider mb-3">
                          Automated QA Diagnostics
                        </h3>

                        {previewIssues.length === 0 ? (
                          <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 flex items-center space-x-2">
                            <span className="font-bold">✓</span>
                            <span className="font-medium">All QA checks passed cleanly!</span>
                          </div>
                        ) : (
                          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                            {previewIssues.map((issue, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded-lg border text-xs space-y-1 ${
                                  issue.severity === "error"
                                    ? "bg-rose-950/40 border-rose-500/30 text-rose-300"
                                    : issue.severity === "warning"
                                    ? "bg-amber-950/40 border-amber-500/30 text-amber-300"
                                    : "bg-sky-950/40 border-sky-500/30 text-sky-300"
                                }`}
                              >
                                <div className="flex justify-between items-center font-bold text-[10px] uppercase font-mono">
                                  <span>{issue.check}</span>
                                  <span>{issue.severity}</span>
                                </div>
                                <p className="font-medium text-[#FAFAFA]">{issue.message}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="border border-white/10 rounded-xl p-4 bg-[#181818] text-xs space-y-2 text-[#A1A1AA] font-mono">
                        <span className="font-semibold text-[#FAFAFA] block">Print Geometry Specifications:</span>
                        <ul className="space-y-1 text-[11px]">
                          <li>• Canvas: 60 × 92 mm (with 3mm bleed margin)</li>
                          <li>• Finished Trim: 54 × 86 mm (ISO/IEC 7810 ID-1 Standard)</li>
                          <li>• Safe Inset: 4 mm inside trim line</li>
                          <li>• Photo: Smart face centering & aspect crop</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-white/10">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-4 py-2 border border-white/15 hover:bg-white/5 text-[#A1A1AA] hover:text-white text-xs font-semibold rounded-full transition"
                >
                  ← Back to Drafts
                </button>
                <button
                  onClick={() => setCurrentStep(5)}
                  className="px-5 py-2 bg-white text-black hover:bg-slate-100 text-xs font-semibold rounded-full shadow-sm transition"
                >
                  Proceed to Export →
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: BATCH EXPORT */}
          {currentStep === 5 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-[#FAFAFA]">Step 5: Production Export & Commercial Print</h2>
                <p className="text-sm text-[#A1A1AA] mt-1">
                  Generate press-ready badge packages in multi-page vector PDF, 300 DPI raster archive, or commercial imposition sheets.
                </p>
              </div>

              {/* Export Mode Selector */}
              <div className="flex border border-white/10 max-w-2xl bg-[#0E0E10] rounded-xl p-1 gap-1">
                <button
                  type="button"
                  onClick={() => setExportMode("batch")}
                  className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition ${
                    exportMode === "batch"
                      ? "bg-white text-black shadow-sm"
                      : "text-[#A1A1AA] hover:text-white"
                  }`}
                >
                  📦 Individual Badges / ZIP Archive
                </button>
                <button
                  type="button"
                  onClick={() => setExportMode("print_sheet")}
                  className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition ${
                    exportMode === "print_sheet"
                      ? "bg-white text-black shadow-sm"
                      : "text-[#A1A1AA] hover:text-white"
                  }`}
                >
                  🖨️ Commercial Print Sheet (A4 / A3)
                </button>
              </div>

              {/* Export Form */}
              <div className="max-w-2xl bg-[#181818] border border-white/10 rounded-2xl p-6 space-y-5">
                {exportMode === "batch" ? (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      {/* Format */}
                      <div>
                        <label className="block text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider mb-1.5">
                          Export Format
                        </label>
                        <select
                          value={exportFormat}
                          onChange={(e) => setExportFormat(e.target.value as any)}
                          className="w-full rounded-lg border border-white/15 p-2.5 text-xs bg-[#121214] text-[#FAFAFA] focus:border-white/40 focus:ring-1 focus:ring-white/20 outline-none"
                        >
                          <option value="pdf">PDF (Print Vector)</option>
                          <option value="png">PNG (300 DPI Raster)</option>
                          <option value="svg">SVG (Raw Vector Markup)</option>
                        </select>
                      </div>

                      {/* Orientation */}
                      <div>
                        <label className="block text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider mb-1.5">
                          Orientation
                        </label>
                        <select
                          value={exportOrientation}
                          onChange={(e) => setExportOrientation(e.target.value as "portrait" | "landscape")}
                          className="w-full rounded-lg border border-white/15 p-2.5 text-xs bg-[#121214] text-[#FAFAFA] focus:border-white/40 focus:ring-1 focus:ring-white/20 outline-none"
                        >
                          <option value="portrait">Portrait (54 × 86 mm)</option>
                          <option value="landscape">Landscape (86 × 54 mm)</option>
                        </select>
                      </div>

                      {/* DPI */}
                      <div>
                        <label className="block text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider mb-1.5">
                          Resolution (DPI)
                        </label>
                        <select
                          value={exportDpi}
                          onChange={(e) => setExportDpi(parseInt(e.target.value, 10))}
                          className="w-full rounded-lg border border-white/15 p-2.5 text-xs bg-[#121214] text-[#FAFAFA] focus:border-white/40 focus:ring-1 focus:ring-white/20 outline-none"
                        >
                          <option value={300}>300 DPI (Commercial Standard)</option>
                          <option value={150}>150 DPI (Quick Draft)</option>
                        </select>
                      </div>
                    </div>

                    {/* Collation Option (PDF only) */}
                    {exportFormat === "pdf" && (
                      <div className="pt-2">
                        <label className="flex items-center space-x-2 text-xs text-[#FAFAFA] cursor-pointer font-medium">
                          <input
                            type="checkbox"
                            checked={collatePdf}
                            onChange={(e) => setCollatePdf(e.target.checked)}
                            className="rounded border-white/20 bg-[#121214] text-white focus:ring-0"
                          />
                          <span>Collate into a single multi-page PDF document (1 page per attendee)</span>
                        </label>
                        <p className="text-[11px] text-[#A1A1AA] ml-5 mt-0.5 font-mono">
                          If unchecked, downloads a ZIP archive containing individual PDF cards and a QA report.
                        </p>
                      </div>
                    )}

                    {/* Bleed checkbox */}
                    <div>
                      <label className="flex items-center space-x-2 text-xs text-[#FAFAFA] cursor-pointer font-medium">
                        <input
                          type="checkbox"
                          checked={exportBleed}
                          onChange={(e) => setExportBleed(e.target.checked)}
                          className="rounded border-white/20 bg-[#121214] text-white focus:ring-0"
                        />
                        <span>Include 3mm print bleed (60 × 92 mm canvas with trim allowance)</span>
                      </label>
                    </div>

                    {/* Batch Summary Box */}
                    <div className="bg-[#121214] border border-white/10 rounded-xl p-4 text-xs space-y-1">
                      <span className="font-semibold text-[#FAFAFA] block uppercase tracking-wider text-[11px]">Batch Overview:</span>
                      <div className="grid grid-cols-2 gap-2 text-[#A1A1AA] pt-1 font-mono">
                        <div>• Total Attendees: <strong className="text-[#FAFAFA]">{people.length || 1}</strong></div>
                        <div>• Selected Layout: <strong className="text-[#FAFAFA]">{drafts[selectedDraftIndex]?.layout_name || "classic"}</strong></div>
                        <div>• Selected Theme: <strong className="text-[#FAFAFA]">{drafts[selectedDraftIndex]?.theme_name || "clean_light"}</strong></div>
                        <div>• Output: <strong className="text-[#FAFAFA]">{collatePdf ? "Single cards.pdf" : "cards.zip Archive"}</strong></div>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="space-y-4">
                      {/* Target Page Size */}
                      <div>
                        <label className="block text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider mb-1.5">
                          Commercial Imposition Sheet Size
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={() => setPrintSheetPage("A4")}
                            className={`p-3 rounded-xl border text-left transition ${
                              printSheetPage === "A4"
                                ? "bg-white/10 border-white text-white"
                                : "bg-[#121214] border-white/15 text-[#A1A1AA] hover:text-white"
                            }`}
                          >
                            <div className="flex justify-between items-center font-bold text-xs">
                              <span>A4 Commercial Sheet</span>
                              <span className="text-[10px] font-mono">3 × 3 Grid</span>
                            </div>
                            <p className="text-[11px] text-[#A1A1AA] mt-1 font-mono">
                              210 × 297 mm • 9 cards / page • 15mm margins
                            </p>
                          </button>

                          <button
                            type="button"
                            onClick={() => setPrintSheetPage("A3")}
                            className={`p-3 rounded-xl border text-left transition ${
                              printSheetPage === "A3"
                                ? "bg-white/10 border-white text-white"
                                : "bg-[#121214] border-white/15 text-[#A1A1AA] hover:text-white"
                            }`}
                          >
                            <div className="flex justify-between items-center font-bold text-xs">
                              <span>A3 Press Sheet</span>
                              <span className="text-[10px] font-mono">4 × 4 Grid</span>
                            </div>
                            <p className="text-[11px] text-[#A1A1AA] mt-1 font-mono">
                              297 × 420 mm • 16 cards / page • 28.5mm margins
                            </p>
                          </button>
                        </div>
                      </div>

                      {/* Crop Marks Toggle */}
                      <div className="pt-1">
                        <label className="flex items-center space-x-2 text-xs text-[#FAFAFA] cursor-pointer font-medium">
                          <input
                            type="checkbox"
                            checked={printSheetCropMarks}
                            onChange={(e) => setPrintSheetCropMarks(e.target.checked)}
                            className="rounded border-white/20 bg-[#121214] text-white focus:ring-0"
                          />
                          <span>Render 8 Precision Corner Crop Marks (0.5mm offset at 54 × 86 mm trim lines)</span>
                        </label>
                        <p className="text-[11px] text-[#A1A1AA] ml-5 mt-0.5 font-mono">
                          Essential for commercial guillotine cutter alignment with standard 3mm bleed margin.
                        </p>
                      </div>

                      {/* Imposition Summary Box */}
                      <div className="bg-[#121214] border border-white/10 rounded-xl p-4 text-xs space-y-1">
                        <span className="font-semibold text-[#FAFAFA] block uppercase tracking-wider text-[11px]">Print Sheet Imposition Details:</span>
                        <div className="grid grid-cols-2 gap-2 text-[#A1A1AA] pt-1 font-mono">
                          <div>• Total Attendees: <strong className="text-[#FAFAFA]">{people.length || 1}</strong></div>
                          <div>• Grid Layout: <strong className="text-[#FAFAFA]">{printSheetPage === "A4" ? "3 cols × 3 rows (9/page)" : "4 cols × 4 rows (16/page)"}</strong></div>
                          <div>• Total Imposed Pages: <strong className="text-[#FAFAFA]">{Math.ceil((people.length || 1) / (printSheetPage === "A4" ? 9 : 16))} sheet(s)</strong></div>
                          <div>• Technical Margins: <strong className="text-[#FAFAFA]">{printSheetPage === "A4" ? "X: 15mm, Y: 10.5mm" : "X: 28.5mm, Y: 26mm"}</strong></div>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {/* Action button */}
                <button
                  type="button"
                  onClick={handleBatchExport}
                  disabled={exportLoading}
                  className="w-full py-3 bg-white hover:bg-slate-100 text-black font-semibold text-sm rounded-full shadow-sm transition disabled:opacity-40 flex items-center justify-center space-x-2"
                >
                  {exportLoading ? (
                    <>
                      <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                      <span>{exportMode === "print_sheet" ? `Rendering ${printSheetPage} Imposed Sheet...` : "Generating Batch & Packing Archive..."}</span>
                    </>
                  ) : (
                    <span>
                      {exportMode === "print_sheet"
                        ? `Download Imposed ${printSheetPage} Print Sheet (PDF)`
                        : collatePdf
                        ? "Download Collated PDF"
                        : "Download ZIP Package"}
                    </span>
                  )}
                </button>
              </div>

              {/* Success Result Box */}
              {exportSuccess && (
                <div className="max-w-2xl bg-emerald-950/40 border border-emerald-500/30 rounded-2xl p-5 text-xs text-emerald-300 space-y-2">
                  <div className="flex items-center space-x-2 font-bold text-sm">
                    <span>✓</span>
                    <span>Download Complete!</span>
                  </div>
                  <p className="font-mono">{exportSuccess}</p>
                </div>
              )}

              <div className="flex justify-start items-center pt-4 border-t border-white/10">
                <button
                  onClick={() => setCurrentStep(4)}
                  className="px-4 py-2 border border-white/15 hover:bg-white/5 text-[#A1A1AA] hover:text-white text-xs font-semibold rounded-full transition"
                >
                  ← Back to Badge Studio
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
