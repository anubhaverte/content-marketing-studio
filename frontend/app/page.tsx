"use client";

import React, { useEffect, useState } from "react";
import {
  checkBackendHealth,
  submitBrief,
  uploadAttendeeCsv,
  generateDrafts,
  renderPreview,
  renderBatch,
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

  // Step 4: Preview State
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewSvg, setPreviewSvg] = useState<string>("");
  const [previewIssues, setPreviewIssues] = useState<QAIssue[]>([]);
  const [currentPersonIndex, setCurrentPersonIndex] = useState<number>(0);
  const [showDebugGuides, setShowDebugGuides] = useState<boolean>(false);

  // Step 5: Export State
  const [exportFormat, setExportFormat] = useState<"pdf" | "png" | "svg">("pdf");
  const [collatePdf, setCollatePdf] = useState<boolean>(false);
  const [exportDpi, setExportDpi] = useState<number>(300);
  const [exportBleed, setExportBleed] = useState<boolean>(true);
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
        "Could not connect to FastAPI backend at http://localhost:8000. Please start the backend with uvicorn."
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

  async function handleFetchDrafts() {
    setDraftsLoading(true);
    setGlobalError(null);

    const brief: EventBrief = briefResponse?.brief || {
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
      const res = await generateDrafts(brief, 3);
      setDrafts(res.drafts);
      setDraftsMock(Boolean(res.mock));
      setSelectedDraftIndex(0);
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

    try {
      const result = await renderBatch({
        spec,
        people: exportPeople,
        settings: {
          format: exportFormat,
          dpi: exportDpi,
          orientation: "portrait",
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
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              CS
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-slate-900 leading-none">
                Card Studio
              </h1>
              <p className="text-xs text-slate-500 font-medium mt-0.5">
                ACM NIT Surat Hackathon ID Badge Engine
              </p>
            </div>
          </div>

          {/* Backend Status indicator */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-xs font-medium px-3 py-1.5 rounded-full border border-slate-200 bg-slate-50">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  backendStatus === "online"
                    ? "bg-emerald-500 animate-pulse"
                    : backendStatus === "checking"
                    ? "bg-amber-400"
                    : "bg-rose-500"
                }`}
              />
              <span className="text-slate-700">
                {backendStatus === "online"
                  ? `Backend Live (v${backendVersion})`
                  : backendStatus === "checking"
                  ? "Checking Backend..."
                  : "Backend Offline (:8000)"}
              </span>
            </div>
            {backendStatus === "offline" && (
              <button
                onClick={checkHealth}
                className="text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 px-2 py-1 rounded transition"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Global Error Banner */}
      {globalError && (
        <div className="bg-rose-50 border-b border-rose-200 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-rose-800">
            <div className="flex items-center space-x-2">
              <span className="font-semibold">Notice:</span>
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => setGlobalError(null)}
              className="text-rose-600 hover:text-rose-900 font-bold ml-4"
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
          <ol className="flex items-center justify-between w-full border border-slate-200 rounded-xl bg-white p-3 shadow-sm">
            {steps.map((step, idx) => {
              const isActive = currentStep === step.num;
              const isPast = currentStep > step.num;
              return (
                <li key={step.num} className="flex-1 relative flex items-center">
                  <button
                    onClick={() => setCurrentStep(step.num)}
                    className="flex items-center space-x-3 w-full group focus:outline-none"
                  >
                    <span
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition ${
                        isActive
                          ? "bg-blue-600 text-white shadow-sm ring-4 ring-blue-100"
                          : isPast
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
                      }`}
                    >
                      {isPast ? "✓" : step.num}
                    </span>
                    <span
                      className={`text-sm font-semibold transition ${
                        isActive
                          ? "text-blue-600"
                          : isPast
                          ? "text-slate-900"
                          : "text-slate-500 group-hover:text-slate-700"
                      }`}
                    >
                      {step.label}
                    </span>
                  </button>
                  {idx < steps.length - 1 && (
                    <div className="hidden md:block w-8 h-0.5 bg-slate-200 mx-2" />
                  )}
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Content Area */}
        <main className="flex-1 bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm">
          {/* STEP 1: EVENT BRIEF */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Step 1: Event Brief</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Describe the event in natural language. The backend extracts event details and missing requirements.
                </p>
              </div>

              <form onSubmit={handleBriefSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Event Description
                  </label>
                  <textarea
                    rows={4}
                    value={briefText}
                    onChange={(e) => setBriefText(e.target.value)}
                    placeholder="Enter event name, dates, venue, tagline, and roles..."
                    className="w-full rounded-xl border border-slate-300 p-3.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition font-sans"
                  />
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    type="submit"
                    disabled={briefLoading || !briefText.trim()}
                    className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {briefLoading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Extracting Brief...</span>
                      </>
                    ) : (
                      <span>Submit to /brief</span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setBriefText(
                        "ACM NIT Surat Hackathon 2026. Dates: 10-12 October 2026. Venue: SVNIT Campus, Surat. Tagline: Code Innovate Elevate. Roles: Participant, Organizer, Mentor."
                      );
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium px-3 py-2 rounded-lg hover:bg-blue-50 transition"
                  >
                    Fill Example Brief
                  </button>
                </div>
              </form>

              {/* Extraction Results */}
              {briefResponse && (
                <div className="mt-8 border border-slate-200 rounded-xl p-5 bg-slate-50 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                    <h3 className="font-bold text-slate-800 text-sm">
                      Structured Brief Result
                    </h3>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                        briefResponse.mock
                          ? "bg-amber-100 text-amber-800 border border-amber-200"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                      }`}
                    >
                      {briefResponse.mock ? "Offline Fallback Mode" : "AI Extracted (Gemini)"}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="font-semibold text-slate-500">Event Name:</span>
                      <p className="font-medium text-slate-900 mt-0.5">
                        {briefResponse.brief.event_name || (
                          <span className="text-amber-600 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Dates:</span>
                      <p className="font-medium text-slate-900 mt-0.5">
                        {briefResponse.brief.dates || (
                          <span className="text-amber-600 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Venue:</span>
                      <p className="font-medium text-slate-900 mt-0.5">
                        {briefResponse.brief.venue || (
                          <span className="text-amber-600 italic">Not detected</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Tagline:</span>
                      <p className="font-medium text-slate-900 mt-0.5">
                        {briefResponse.brief.tagline || (
                          <span className="text-slate-400 italic">None specified</span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Clarification Questions */}
                  {briefResponse.questions.length > 0 && (
                    <div className="pt-4 border-t border-slate-200 space-y-3">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Missing Information Questions ({briefResponse.questions.length})
                      </h4>
                      <div className="space-y-3">
                        {briefResponse.questions.map((q) => (
                          <div
                            key={q.field}
                            className="bg-white p-3.5 rounded-lg border border-slate-200 text-xs space-y-1.5"
                          >
                            <label className="font-semibold text-slate-800 block">
                              {q.text} {!q.skippable && <span className="text-rose-500">*</span>}
                            </label>
                            <input
                              type="text"
                              value={questionAnswers[q.field] || ""}
                              onChange={(e) => handleAnswerChange(q.field, e.target.value)}
                              placeholder={`Enter ${q.field}...`}
                              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-xs focus:ring-1 focus:ring-blue-500 outline-none"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-3 flex justify-end">
                    <button
                      onClick={() => setCurrentStep(2)}
                      className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm transition"
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
                <h2 className="text-xl font-bold text-slate-900">Step 2: Attendee Roster Upload</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Upload a CSV file containing attendee details. Verified against backend CSV schema and OpenCV photo constraints.
                </p>
              </div>

              {/* Upload Dropzone */}
              <div className="border-2 border-dashed border-slate-300 rounded-2xl p-8 text-center hover:border-blue-500 transition bg-slate-50/50">
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
                  <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xl font-bold">
                    📄
                  </div>
                  <span className="text-sm font-semibold text-slate-700">
                    {csvFile ? csvFile.name : "Click to select attendee CSV file"}
                  </span>
                  <span className="text-xs text-slate-400">
                    Supports UTF-8, messy headers, and roles (participant, organizer, mentor)
                  </span>
                </label>

                <div className="mt-4 flex items-center justify-center space-x-3">
                  <button
                    type="button"
                    onClick={loadSampleData}
                    className="text-xs bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold px-3 py-1.5 rounded-lg shadow-sm transition"
                  >
                    Load Sample Roster (4 Attendees)
                  </button>
                </div>
              </div>

              {/* Validation Summary */}
              {dataSummary && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-slate-500 font-medium">Loaded Attendees</span>
                      <p className="text-xl font-bold text-slate-900 mt-0.5">
                        {dataSummary.people_loaded}
                      </p>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-slate-500 font-medium">Missing Names</span>
                      <p className="text-xl font-bold text-rose-600 mt-0.5">
                        {dataSummary.issues.missing_names || 0}
                      </p>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-slate-500 font-medium">Invalid Roles</span>
                      <p className="text-xl font-bold text-amber-600 mt-0.5">
                        {dataSummary.issues.unknown_roles ?? dataSummary.issues.invalid_roles ?? 0}
                      </p>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
                      <span className="text-xs text-slate-500 font-medium">Duplicate IDs</span>
                      <p className="text-xl font-bold text-slate-900 mt-0.5">
                        {dataSummary.issues.duplicate_ids || 0}
                      </p>
                    </div>
                  </div>

                  {/* Warnings List */}
                  {dataSummary.warnings.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs space-y-1">
                      <span className="font-bold text-amber-900 block">Validation Warnings:</span>
                      <ul className="list-disc list-inside text-amber-800 space-y-0.5">
                        {dataSummary.warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Attendee Table Preview */}
                  {people.length > 0 && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden">
                      <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                          Attendee Records Preview ({people.length})
                        </span>
                        {skippedRows.length > 0 && (
                          <span className="text-xs text-rose-600 font-medium">
                            {skippedRows.length} rows skipped
                          </span>
                        )}
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-100 text-slate-600 font-semibold sticky top-0">
                            <tr>
                              <th className="px-4 py-2">ID</th>
                              <th className="px-4 py-2">Name</th>
                              <th className="px-4 py-2">Role</th>
                              <th className="px-4 py-2">Team</th>
                              <th className="px-4 py-2">Photo Path</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {people.slice(0, 10).map((p, idx) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-4 py-2 font-mono text-slate-500">{p.id || "—"}</td>
                                <td className="px-4 py-2 font-medium text-slate-900">{p.name}</td>
                                <td className="px-4 py-2">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                      p.role === "organizer"
                                        ? "bg-orange-100 text-orange-800"
                                        : p.role === "mentor"
                                        ? "bg-green-100 text-green-800"
                                        : "bg-blue-100 text-blue-800"
                                    }`}
                                  >
                                    {p.role || "participant"}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-slate-500">{p.team || "—"}</td>
                                <td className="px-4 py-2 font-mono text-slate-400 truncate max-w-xs">
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
                      className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
                    >
                      ← Back to Brief
                    </button>
                    <button
                      onClick={() => {
                        handleFetchDrafts();
                        setCurrentStep(3);
                      }}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                    >
                      Generate Design Drafts →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: DESIGN DRAFTS */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Step 3: Available Design Drafts</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Select a design candidate returned by the backend. Layouts strictly follow theme token colors.
                  </p>
                </div>
                {draftsMock && (
                  <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                    Catalog Variations Active
                  </span>
                )}
              </div>

              {draftsLoading ? (
                <div className="py-16 text-center space-y-3">
                  <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-sm text-slate-500">Querying backend /drafts generator...</p>
                </div>
              ) : drafts.length === 0 ? (
                <div className="text-center py-12 border border-slate-200 rounded-xl bg-slate-50 space-y-3">
                  <p className="text-sm text-slate-600">No design drafts loaded yet.</p>
                  <button
                    onClick={handleFetchDrafts}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                  >
                    Query /drafts Now
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {drafts.map((draft, idx) => {
                    const isSelected = selectedDraftIndex === idx;
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
                        className={`cursor-pointer rounded-2xl border-2 p-5 transition relative flex flex-col justify-between ${
                          isSelected
                            ? "border-blue-600 ring-4 ring-blue-50 bg-blue-50/20"
                            : "border-slate-200 hover:border-slate-300 bg-white"
                        }`}
                      >
                        <div>
                          <div className="flex justify-between items-center mb-3">
                            <span className="text-xs font-bold text-slate-800">
                              Draft #{idx + 1}
                            </span>
                            {isSelected && (
                              <span className="text-xs font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                Selected
                              </span>
                            )}
                          </div>

                          <div className="space-y-1.5 text-xs text-slate-600">
                            <div className="flex justify-between">
                              <span className="text-slate-400">Layout:</span>
                              <span className="font-semibold text-slate-800">
                                {draft.layout_name}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Theme:</span>
                              <span className="font-semibold text-slate-800">
                                {draft.theme_name}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Page:</span>
                              <span>
                                {draft.page.width_mm} × {draft.page.height_mm} mm
                              </span>
                            </div>
                          </div>

                          {/* Swatches */}
                          <div className="mt-4 pt-4 border-t border-slate-100">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                              Color Palette
                            </span>
                            <div className="flex space-x-1.5">
                              {Object.entries(colors).map(([key, val]) => (
                                <div
                                  key={key}
                                  title={`${key}: ${val}`}
                                  className="w-6 h-6 rounded-md border border-slate-200 shadow-xs"
                                  style={{ backgroundColor: String(val) }}
                                />
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="mt-5">
                          <button
                            type="button"
                            className={`w-full py-2 rounded-lg text-xs font-bold transition ${
                              isSelected
                                ? "bg-blue-600 text-white"
                                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                            }`}
                          >
                            {isSelected ? "Active Draft" : "Select This Draft"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-slate-100">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  ← Back to Attendees
                </button>
                <button
                  disabled={drafts.length === 0}
                  onClick={() => setCurrentStep(4)}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
                >
                  Live Preview Badge →
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: BADGE PREVIEW */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Step 4: Live Badge Preview</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Deterministic SVG rendering directly from the backend pipeline. Photo processing uses OpenCV face-aware crop.
                  </p>
                </div>

                {/* Attendee Selector & Guides Toggle */}
                <div className="flex items-center space-x-3">
                  <label className="flex items-center space-x-2 text-xs font-medium text-slate-600 cursor-pointer bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                    <input
                      type="checkbox"
                      checked={showDebugGuides}
                      onChange={(e) => setShowDebugGuides(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span>Print Guides (Bleed/Trim/Safe)</span>
                  </label>

                  {people.length > 1 && (
                    <div className="flex items-center space-x-1 border border-slate-200 rounded-lg p-0.5 bg-slate-50">
                      <button
                        onClick={() =>
                          setCurrentPersonIndex((prev) => (prev > 0 ? prev - 1 : people.length - 1))
                        }
                        className="px-2 py-1 text-xs font-bold text-slate-600 hover:bg-white rounded transition"
                      >
                        ◀
                      </button>
                      <span className="text-xs font-medium px-2 text-slate-700">
                        {currentPersonIndex + 1} / {people.length}
                      </span>
                      <button
                        onClick={() =>
                          setCurrentPersonIndex((prev) => (prev < people.length - 1 ? prev + 1 : 0))
                        }
                        className="px-2 py-1 text-xs font-bold text-slate-600 hover:bg-white rounded transition"
                      >
                        ▶
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Attendee Info Card */}
              {people[currentPersonIndex] && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-3">
                    <div className="w-7 h-7 rounded-full bg-slate-300 flex items-center justify-center font-bold text-slate-700">
                      {people[currentPersonIndex].name.charAt(0)}
                    </div>
                    <div>
                      <span className="font-bold text-slate-900">
                        {people[currentPersonIndex].name}
                      </span>
                      <span className="text-slate-400 mx-2">•</span>
                      <span className="text-slate-500">
                        ID: {people[currentPersonIndex].id || "Auto"}
                      </span>
                      {people[currentPersonIndex].team && (
                        <>
                          <span className="text-slate-400 mx-2">•</span>
                          <span className="text-slate-500">
                            Team: {people[currentPersonIndex].team}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      people[currentPersonIndex].role === "organizer"
                        ? "bg-orange-100 text-orange-800"
                        : people[currentPersonIndex].role === "mentor"
                        ? "bg-green-100 text-green-800"
                        : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {people[currentPersonIndex].role || "participant"}
                  </span>
                </div>
              )}

              {/* Main Preview Workarea */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* SVG Canvas Area */}
                <div className="lg:col-span-2 bg-slate-100 rounded-2xl p-8 flex items-center justify-center min-h-[500px] border border-slate-200">
                  {previewLoading ? (
                    <div className="text-center space-y-3">
                      <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                      <p className="text-xs text-slate-500">Rendering preview SVG from backend...</p>
                    </div>
                  ) : previewSvg ? (
                    <div
                      className="shadow-2xl rounded-sm overflow-hidden bg-white max-w-sm w-full transition transform hover:scale-[1.01]"
                      dangerouslySetInnerHTML={{ __html: previewSvg }}
                    />
                  ) : (
                    <div className="text-center text-slate-400 text-xs">
                      No card rendered yet. Click Render Preview.
                    </div>
                  )}
                </div>

                {/* QA Checklist and Inspection Panel */}
                <div className="space-y-4">
                  <div className="border border-slate-200 rounded-xl p-4 bg-white shadow-xs">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                      Automated QA Diagnostics
                    </h3>

                    {previewIssues.length === 0 ? (
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center space-x-2">
                        <span>✓</span>
                        <span className="font-semibold">All QA checks passed cleanly!</span>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {previewIssues.map((issue, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border text-xs space-y-1 ${
                              issue.severity === "error"
                                ? "bg-rose-50 border-rose-200 text-rose-900"
                                : issue.severity === "warning"
                                ? "bg-amber-50 border-amber-200 text-amber-900"
                                : "bg-blue-50 border-blue-200 text-blue-900"
                            }`}
                          >
                            <div className="flex justify-between items-center font-bold text-[10px] uppercase">
                              <span>{issue.check}</span>
                              <span>{issue.severity}</span>
                            </div>
                            <p className="font-medium text-slate-800">{issue.message}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 text-xs space-y-2 text-slate-600">
                    <span className="font-bold text-slate-800 block">Print Geometry Specs:</span>
                    <ul className="space-y-1 text-[11px]">
                      <li>• Canvas: 60 × 92 mm (with 3mm bleed)</li>
                      <li>• Finished Trim: 54 × 86 mm (ISO/IEC 7810 ID-1)</li>
                      <li>• Safe Inset: 4 mm inside trim line</li>
                      <li>• Photo: Face crop with OpenCV heuristic</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center pt-4 border-t border-slate-100">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  ← Back to Drafts
                </button>
                <button
                  onClick={() => setCurrentStep(5)}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
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
                <h2 className="text-xl font-bold text-slate-900">Step 5: Batch Render & Export</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Export ready-to-print ID cards for the entire roster. Calls the real <code className="text-blue-600 font-mono">POST /render/batch</code> endpoint.
                </p>
              </div>

              {/* Export Form */}
              <div className="max-w-2xl bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Format */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      Export Format
                    </label>
                    <select
                      value={exportFormat}
                      onChange={(e) => setExportFormat(e.target.value as any)}
                      className="w-full rounded-lg border border-slate-300 p-2.5 text-xs bg-white focus:ring-1 focus:ring-blue-500 outline-none"
                    >
                      <option value="pdf">PDF (Print Vector)</option>
                      <option value="png">PNG (300 DPI Raster)</option>
                      <option value="svg">SVG (Raw Vector Markup)</option>
                    </select>
                  </div>

                  {/* DPI */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      Resolution (DPI)
                    </label>
                    <select
                      value={exportDpi}
                      onChange={(e) => setExportDpi(parseInt(e.target.value, 10))}
                      className="w-full rounded-lg border border-slate-300 p-2.5 text-xs bg-white focus:ring-1 focus:ring-blue-500 outline-none"
                    >
                      <option value={300}>300 DPI (Commercial Print Standard)</option>
                      <option value={150}>150 DPI (Quick Draft)</option>
                    </select>
                  </div>
                </div>

                {/* Collation Option (PDF only) */}
                {exportFormat === "pdf" && (
                  <div className="pt-2">
                    <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer font-medium">
                      <input
                        type="checkbox"
                        checked={collatePdf}
                        onChange={(e) => setCollatePdf(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span>Collate into a single multi-page PDF document (1 page per attendee)</span>
                    </label>
                    <p className="text-[11px] text-slate-500 ml-5 mt-0.5">
                      If unchecked, downloads a ZIP archive containing individual PDF cards and a QA report.
                    </p>
                  </div>
                )}

                {/* Bleed checkbox */}
                <div>
                  <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer font-medium">
                    <input
                      type="checkbox"
                      checked={exportBleed}
                      onChange={(e) => setExportBleed(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span>Include 3mm print bleed (60 × 92 mm canvas with trim allowance)</span>
                  </label>
                </div>

                {/* Batch Summary Box */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 text-xs space-y-1">
                  <span className="font-bold text-slate-800 block">Batch Overview:</span>
                  <div className="grid grid-cols-2 gap-2 text-slate-600 pt-1">
                    <div>• Total Attendees: <strong className="text-slate-900">{people.length || 1}</strong></div>
                    <div>• Selected Layout: <strong className="text-slate-900">{drafts[selectedDraftIndex]?.layout_name || "classic"}</strong></div>
                    <div>• Selected Theme: <strong className="text-slate-900">{drafts[selectedDraftIndex]?.theme_name || "clean_light"}</strong></div>
                    <div>• Output: <strong className="text-slate-900">{collatePdf ? "Single cards.pdf" : "cards.zip Archive"}</strong></div>
                  </div>
                </div>

                {/* Action button */}
                <button
                  type="button"
                  onClick={handleBatchExport}
                  disabled={exportLoading}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-xl shadow-sm transition disabled:opacity-50 flex items-center justify-center space-x-2"
                >
                  {exportLoading ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Generating Batch & Packing Archive...</span>
                    </>
                  ) : (
                    <span>Download {collatePdf ? "Collated PDF" : "ZIP Package"}</span>
                  )}
                </button>
              </div>

              {/* Success Result Box */}
              {exportSuccess && (
                <div className="max-w-2xl bg-emerald-50 border border-emerald-200 rounded-2xl p-5 text-xs text-emerald-900 space-y-2">
                  <div className="flex items-center space-x-2 font-bold text-sm">
                    <span>✓</span>
                    <span>Download Complete!</span>
                  </div>
                  <p>{exportSuccess}</p>
                </div>
              )}

              <div className="flex justify-start items-center pt-4 border-t border-slate-100">
                <button
                  onClick={() => setCurrentStep(4)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  ← Back to Badge Preview
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
