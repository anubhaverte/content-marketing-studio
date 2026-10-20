import { DesignSpec, LayoutElement } from "../types";

const VALID_BACKEND_LAYOUTS = ["classic", "minimal", "split"];
const VALID_BACKEND_THEMES = ["clean_light", "dark_tech", "bold_event"];

const KNOWN_PRESET_FILES: Record<string, string> = {
  decal_terminal: "assets/art/decal_terminal.svg",
  decal_star: "assets/art/decal_star.svg",
  decal_shield: "assets/art/decal_shield.svg",
  decal_chip: "assets/art/decal_chip.svg",
  bg_tech_grid: "assets/art/bg_tech_grid.svg",
  bg_circuit_lines: "assets/art/bg_circuit_lines.svg",
  bg_geometric_mesh: "assets/art/bg_geometric_mesh.svg",
  bg_svnit_watermark: "assets/art/bg_svnit_watermark.svg",
  logo_acm: "assets/logos/acm_nitsurat.svg",
  logo_svnit: "assets/logos/svnit.svg",
  acm_nitsurat: "assets/logos/acm_nitsurat.svg",
  acm: "assets/logos/acm_nitsurat.svg",
  svnit: "assets/logos/svnit.svg",
};

/**
 * Normalizes an image/logo/decal source into a brand logo key and a repo-relative file path.
 */
function resolveLogoKeyAndPath(
  src: string,
  elementId?: string
): { key: string; repoPath: string } | null {
  if (!src || typeof src !== "string") return null;

  // Direct known keys
  if (KNOWN_PRESET_FILES[src]) {
    return { key: src, repoPath: KNOWN_PRESET_FILES[src] };
  }

  // Path like /art/decal_terminal.svg or /art/bg_tech_grid.svg
  if (src.startsWith("/art/")) {
    const filename = src.replace("/art/", "");
    const baseKey = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: baseKey,
      repoPath: `assets/art/${filename}`,
    };
  }

  if (src.startsWith("/logos/")) {
    const filename = src.replace("/logos/", "");
    const baseKey = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: baseKey,
      repoPath: `assets/logos/${filename}`,
    };
  }

  if (src.startsWith("frontend/public/art/")) {
    const filename = src.replace("frontend/public/art/", "");
    const baseKey = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: baseKey,
      repoPath: `assets/art/${filename}`,
    };
  }

  if (src.startsWith("frontend/public/logos/")) {
    const filename = src.replace("frontend/public/logos/", "");
    const baseKey = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: baseKey,
      repoPath: `assets/logos/${filename}`,
    };
  }

  if (src.startsWith("assets/")) {
    const filename = src.split("/").pop() || "asset";
    const baseKey = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: baseKey,
      repoPath: src,
    };
  }

  if (src.startsWith("data:")) {
    const cleanId = (elementId || "custom_asset").replace(/[^a-zA-Z0-9_]/g, "_");
    return {
      key: cleanId,
      repoPath: src,
    };
  }

  // If it's a generated element ID or arbitrary string
  const cleanId = (elementId || "decal").replace(/[^a-zA-Z0-9_]/g, "_");
  return {
    key: cleanId,
    repoPath: `assets/art/${src}`,
  };
}


/**
 * Validates that an element color/fill/stroke uses canonical theme token names,
 * never raw hex colors (which would cause backend AttributeError in _color).
 */
const VALID_THEME_TOKENS = new Set([
  "background",
  "primary",
  "secondary",
  "accent",
  "text",
  "text_on_primary",
  "none",
  "role",
]);

function safeThemeToken(val: any, fallback: string = "background"): string {
  if (typeof val !== "string") return fallback;
  const clean = val.trim().toLowerCase();
  if (VALID_THEME_TOKENS.has(clean)) return clean;
  // If a raw hex code was erroneously assigned to the element fill/stroke, fall back to safe token
  return fallback;
}

/**
 * Sanitizes and converts a client-side DesignSpec into a strict, compliant
 * FastAPI Pydantic DesignSpec (StrictModel with extra="forbid").
 *
 * 1. Preserves and registers background images as valid 'logo' elements with
 *    registered brand.logos paths so they render across all export formats (PDF, PNG, SVG, Print Sheet).
 * 2. Maps custom decals/images into schema-compliant 'logo' elements.
 * 3. Enforces valid backend layout and theme names ('classic', 'minimal', 'split').
 * 4. Ensures layout tokens are strictly used for fills/strokes, preventing hex crashes.
 */
export function sanitizeSpecForBackend(rawSpec: DesignSpec): DesignSpec {
  if (!rawSpec) return rawSpec;

  const cloned: any = JSON.parse(JSON.stringify(rawSpec));

  // 1. Resolve layout_name and theme_name to known backend templates
  const rawLayout = (cloned.layout_name || "").toLowerCase();
  const baseLayout = (cloned.base_layout || cloned.baseLayout || "").toLowerCase();
  const safeLayout = VALID_BACKEND_LAYOUTS.includes(rawLayout)
    ? rawLayout
    : VALID_BACKEND_LAYOUTS.includes(baseLayout)
    ? baseLayout
    : "classic";

  const rawTheme = (cloned.theme_name || cloned.theme?.name || "").toLowerCase();
  const baseTheme = (cloned.base_theme || cloned.baseTheme || "").toLowerCase();

  // Intelligent theme detection: if custom theme, infer from background color luminance
  let fallbackTheme = "clean_light";
  const bgHex = cloned.theme?.colors?.background || "";
  if (typeof bgHex === "string" && bgHex.startsWith("#") && bgHex.length >= 7) {
    const r = parseInt(bgHex.slice(1, 3), 16) || 0;
    const g = parseInt(bgHex.slice(3, 5), 16) || 0;
    const b = parseInt(bgHex.slice(5, 7), 16) || 0;
    const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    if (lum < 0.4) {
      fallbackTheme = "dark_tech";
    }
  }

  const safeTheme = VALID_BACKEND_THEMES.includes(rawTheme)
    ? rawTheme
    : VALID_BACKEND_THEMES.includes(baseTheme)
    ? baseTheme
    : fallbackTheme;

  // 2. Initialize brand logos
  const brandLogos: Record<string, string> = {
    svnit: "assets/logos/svnit.svg",
    acm_nitsurat: "assets/logos/acm_nitsurat.svg",
    acm: "assets/logos/acm_nitsurat.svg",
    logo_acm: "assets/logos/acm_nitsurat.svg",
    logo_svnit: "assets/logos/svnit.svg",
    ...(cloned.brand?.logos || {}),
  };

  // 3. Detect background image (either in elements, top-level bg_image, brand.logos, or dark_tech theme)
  let bgLogoElement: any = null;
  const rawBgEl =
    (cloned.elements || []).find((el: any) => el.id === "bg_image" || el.is_background) ||
    cloned.bg_image ||
    (cloned.brand?.logos && cloned.brand.logos["bg_image"] ? { src: "bg_image" } : null) ||
    (cloned.brand?.logos && cloned.brand.logos["bg_custom"] ? { src: "bg_custom" } : null) ||
    (cloned.brand?.logos && cloned.brand.logos["bg_tech_grid"] ? { src: "bg_tech_grid" } : null) ||
    (safeTheme === "dark_tech" ? { src: "bg_tech_grid" } : null);

  if (rawBgEl) {
    const rawSrc = rawBgEl.src || rawBgEl.url || "";
    const resolved = resolveLogoKeyAndPath(rawSrc, "bg_image");
    let bgRepoPath =
      (cloned.brand?.logos && cloned.brand.logos[rawSrc]) ||
      (cloned.brand?.logos && cloned.brand.logos["bg_image"]) ||
      (cloned.brand?.logos && cloned.brand.logos["bg_custom"]) ||
      (cloned.brand?.logos && cloned.brand.logos["bg_tech_grid"]) ||
      (resolved ? resolved.repoPath : "assets/art/bg_tech_grid.svg");

    if (bgRepoPath.startsWith("frontend/public/art/")) {
      bgRepoPath = bgRepoPath.replace("frontend/public/art/", "assets/art/");
    } else if (bgRepoPath.startsWith("/art/")) {
      bgRepoPath = "assets" + bgRepoPath;
    }

    brandLogos["bg_image"] = bgRepoPath;

    const canvasW = Number(cloned.page?.width_mm || 54) + 2 * Number(cloned.page?.bleed_mm ?? 3);
    const canvasH = Number(cloned.page?.height_mm || 86) + 2 * Number(cloned.page?.bleed_mm ?? 3);

    bgLogoElement = {
      id: "bg_image",
      type: "logo",
      src: "bg_image",
      x: 0,
      y: 0,
      w: canvasW,
      h: canvasH,
      fit: "contain",
    };
  }

  // 4. Scan elements for images/decals and register their brand logo paths
  (cloned.elements || []).forEach((el: any) => {
    if (el.id === "bg_image" || el.is_background) return;
    if (el.type === "image" || el.type === "svg_asset") {
      const resolved = resolveLogoKeyAndPath(el.src, el.id);
      if (resolved && !brandLogos[resolved.key]) {
        brandLogos[resolved.key] = resolved.repoPath;
      }
    } else if (el.type === "logo" && el.src) {
      if (!brandLogos[el.src]) {
        const resolved = resolveLogoKeyAndPath(el.src, el.id);
        if (resolved) {
          brandLogos[el.src] = resolved.repoPath;
        }
      }
    }
  });

  // Normalize all brand logo paths: replace any legacy frontend/public/ paths with assets/
  for (const [key, pathVal] of Object.entries(brandLogos)) {
    if (typeof pathVal === "string") {
      if (pathVal.startsWith("frontend/public/art/")) {
        brandLogos[key] = pathVal.replace("frontend/public/art/", "assets/art/");
      } else if (pathVal.startsWith("frontend/public/logos/")) {
        brandLogos[key] = pathVal.replace("frontend/public/logos/", "assets/logos/");
      }
    }
  }


  // 5. Sanitize elements strictly
  const sanitizedElements: any[] = [];

  for (const el of cloned.elements || []) {
    // Skip bg_image in normal loop; we position it deterministically right after the background rect
    if (el.id === "bg_image" || el.is_background) {
      continue;
    }

    const id = String(el.id || `${el.type}_${Math.random().toString(36).substring(2, 7)}`);

    switch (el.type) {
      case "rect":
        sanitizedElements.push({
          id,
          type: "rect",
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 2, 0.1),
          h: Math.max(Number(el.h) || 2, 0.1),
          fill: typeof el.fill === "object" ? el.fill : safeThemeToken(el.fill, id === "bg" ? "background" : "primary"),
          stroke: safeThemeToken(el.stroke, "none"),
          stroke_width: Number(el.stroke_width) || 0,
          radius: Number(el.radius) || 0,
          dash: Array.isArray(el.dash) ? el.dash : undefined,
          opacity: el.opacity !== undefined ? Math.min(Math.max(Number(el.opacity), 0), 1) : 1,
        });
        break;

      case "line":
        sanitizedElements.push({
          id,
          type: "line",
          x1: Number(el.x1) || 0,
          y1: Number(el.y1) || 0,
          x2: Number(el.x2) || 0,
          y2: Number(el.y2) || 0,
          stroke: safeThemeToken(el.stroke, "text"),
          stroke_width: Math.max(Number(el.stroke_width) || 0.3, 0.05),
          dash: Array.isArray(el.dash) ? el.dash : undefined,
          opacity: el.opacity !== undefined ? Math.min(Math.max(Number(el.opacity), 0), 1) : 1,
        });
        break;

      case "circle":
        sanitizedElements.push({
          id,
          type: "circle",
          cx: Number(el.cx) || 0,
          cy: Number(el.cy) || 0,
          r: Math.max(Number(el.r) || 1, 0.1),
          fill: typeof el.fill === "object" ? el.fill : safeThemeToken(el.fill, "none"),
          stroke: safeThemeToken(el.stroke, "none"),
          stroke_width: Number(el.stroke_width) || 0,
          opacity: el.opacity !== undefined ? Math.min(Math.max(Number(el.opacity), 0), 1) : 1,
        });
        break;

      case "text": {
        const textObj: any = {
          id,
          type: "text",
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 10, 1),
          font: el.font === "heading" ? "heading" : "body",
          color: safeThemeToken(el.color, "text"),
          max_font: Number(el.max_font) || 14,
          min_font: Math.min(Number(el.min_font) || 8, Number(el.max_font) || 14),
          max_lines: Math.max(Math.round(Number(el.max_lines) || 1), 1),
          align: ["left", "center", "right"].includes(el.align) ? el.align : "left",
          bold: Boolean(el.bold),
          uppercase: Boolean(el.uppercase),
        };
        if (el.value !== undefined && el.value !== null) {
          textObj.value = String(el.value);
        } else {
          textObj.field = el.field || "name";
        }
        sanitizedElements.push(textObj);
        break;
      }

      case "photo":
        sanitizedElements.push({
          id,
          type: "photo",
          field: el.field || "photo",
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 10, 1),
          h: Math.max(Number(el.h) || 10, 1),
          shape: ["rect", "rounded", "circle"].includes(el.shape) ? el.shape : "rect",
          radius: Number(el.radius) || 0,
        });
        break;

      case "logo": {
        const resolved = resolveLogoKeyAndPath(el.src, id);
        const logoKey = resolved ? resolved.key : el.src || "acm_nitsurat";
        if (resolved && !brandLogos[logoKey]) {
          brandLogos[logoKey] = resolved.repoPath;
        }
        sanitizedElements.push({
          id,
          type: "logo",
          src: logoKey,
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 5, 0.5),
          h: el.h ? Math.max(Number(el.h), 0.5) : undefined,
          fit: "contain",
        });
        break;
      }

      case "image":
      case "svg_asset": {
        // Convert image / decal into a valid LogoEl registered in brand.logos
        const resolved = resolveLogoKeyAndPath(el.src, id);
        const logoKey = resolved ? resolved.key : "acm_nitsurat";
        if (resolved && !brandLogos[logoKey]) {
          brandLogos[logoKey] = resolved.repoPath;
        }
        sanitizedElements.push({
          id,
          type: "logo",
          src: logoKey,
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 5, 0.5),
          h: el.h ? Math.max(Number(el.h), 0.5) : Number(el.w) || 5,
          fit: "contain",
        });
        break;
      }

      case "role_badge":
        sanitizedElements.push({
          id,
          type: "role_badge",
          field: el.field || "role",
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: Math.max(Number(el.w) || 10, 1),
          h: Math.max(Number(el.h) || 4, 1),
          text_color: safeThemeToken(el.text_color, "background"),
        });
        break;

      case "qr": {
        const qrSize = Math.max(Number(el.w) || 14, 12);
        sanitizedElements.push({
          id,
          type: "qr",
          field: el.field || "qr_url",
          x: Number(el.x) || 0,
          y: Number(el.y) || 0,
          w: qrSize,
          h: qrSize,
          fg: safeThemeToken(el.fg, "text"),
          bg: safeThemeToken(el.bg, "background"),
        });
        break;
      }

      default:
        // Ignore unrecognized elements
        break;
    }
  }

  // 6. Guarantee Base Card Background Rectangle at index 0 (with support for custom colors & transparency)
  const canvasW = Number(cloned.page?.width_mm || 54) + 2 * Number(cloned.page?.bleed_mm ?? 3);
  const canvasH = Number(cloned.page?.height_mm || 86) + 2 * Number(cloned.page?.bleed_mm ?? 3);

  const rawBgColor = cloned.theme?.colors?.background;
  const isTransparent =
    rawBgColor === "none" ||
    rawBgColor === "transparent" ||
    rawBgColor === "#00000000" ||
    rawBgColor === "#ffffff00" ||
    (cloned.elements || []).some(
      (el: any) =>
        (el.id === "bg" || el.id === "background") &&
        (el.fill === "none" || el.opacity === 0)
    );

  // Remove any preexisting canvas background rect to avoid duplicate stacking
  const existingBgIdx = sanitizedElements.findIndex(
    (el) =>
      el.type === "rect" &&
      (el.id === "bg" ||
        el.id === "background" ||
        (el.x === 0 && el.y === 0 && el.w >= canvasW - 1 && el.h >= canvasH - 1))
  );

  let existingBgRadius = 0;
  if (existingBgIdx !== -1) {
    existingBgRadius = sanitizedElements[existingBgIdx].radius || 0;
    sanitizedElements.splice(existingBgIdx, 1);
  }

  // Prepend guaranteed base background rect at index 0
  sanitizedElements.unshift({
    id: "bg",
    type: "rect",
    x: 0,
    y: 0,
    w: canvasW,
    h: canvasH,
    fill: isTransparent ? "none" : "background",
    stroke: "none",
    stroke_width: 0,
    radius: existingBgRadius,
    opacity: 1,
  });

  // 7. Insert background image immediately after the base background rect (at index 1)
  if (bgLogoElement) {
    sanitizedElements.splice(1, 0, bgLogoElement);
  }

  // Construct strict payload
  const result: DesignSpec = {
    schema_version: "1.0",
    layout_name: safeLayout,
    theme_name: safeTheme,
    page: {
      width_mm: Number(cloned.page?.width_mm) || 54,
      height_mm: Number(cloned.page?.height_mm) || 86,
      bleed_mm: Number(cloned.page?.bleed_mm) ?? 3,
      safe_mm: Number(cloned.page?.safe_mm) ?? 4,
    },
    event: {
      event_name: cloned.event?.event_name || "SVNIT ACM Hackathon",
      dates: cloned.event?.dates || null,
      venue: cloned.event?.venue || null,
      tagline: cloned.event?.tagline || null,
    },
    brand: {
      logos: brandLogos,
    },
    theme: {
      name: safeTheme,
      colors: {
        background: isTransparent
          ? "#00000000"
          : (typeof rawBgColor === "string" && /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(rawBgColor.trim()))
          ? rawBgColor.trim().toUpperCase()
          : (safeTheme === "dark_tech" ? "#0B1220" : "#FFFFFF"),
        primary: cloned.theme?.colors?.primary || (safeTheme === "dark_tech" ? "#1E293B" : "#1F6FEB"),
        secondary: cloned.theme?.colors?.secondary || (safeTheme === "dark_tech" ? "#312E81" : "#EAF1FD"),
        accent: cloned.theme?.colors?.accent || (safeTheme === "dark_tech" ? "#38BDF8" : "#38BDF8"),
        text: cloned.theme?.colors?.text || (safeTheme === "dark_tech" ? "#F8FAFC" : "#0B1220"),
      },
      fonts: {
        heading: cloned.theme?.fonts?.heading || "Poppins",
        body: cloned.theme?.fonts?.body || "Inter",
      },
      role_colors: {
        participant: cloned.theme?.role_colors?.participant || (safeTheme === "dark_tech" ? "#38BDF8" : "#1F6FEB"),
        organizer: cloned.theme?.role_colors?.organizer || (safeTheme === "dark_tech" ? "#F97316" : "#D9480F"),
        mentor: cloned.theme?.role_colors?.mentor || (safeTheme === "dark_tech" ? "#4ADE80" : "#2F9E44"),
        volunteer: cloned.theme?.role_colors?.volunteer || (safeTheme === "dark_tech" ? "#A78BFA" : "#8B5CF6"),
      },
    },
    elements: sanitizedElements,
  };

  return result;
}

/**
 * Checks whether a given spec has been modified compared to a reference base combo.
 */
export function isSpecModifiedFromStandard(
  current: DesignSpec,
  standardBase?: DesignSpec
): boolean {
  if (!standardBase) return false;

  // 1. Check if background image is present
  const hasBg = (current.elements || []).some(
    (el: any) => el.id === "bg_image" || el.is_background
  );
  if (hasBg) return true;

  // 2. Check elements length or custom decals
  const currentNonBg = (current.elements || []).filter(
    (el: any) => el.id !== "bg_image" && !el.is_background
  );
  const baseNonBg = (standardBase.elements || []).filter(
    (el: any) => el.id !== "bg_image" && !el.is_background
  );

  if (currentNonBg.length !== baseNonBg.length) return true;

  // Check for any image / decal elements
  const hasDecal = currentNonBg.some(
    (el) => el.type === "image" || el.id?.startsWith("decal_")
  );
  if (hasDecal) return true;

  // 3. Check for geometric differences in elements
  for (const cEl of currentNonBg) {
    const bEl = baseNonBg.find((b) => b.id === cEl.id);
    if (!bEl) return true;
    if (Math.abs((cEl.x ?? 0) - (bEl.x ?? 0)) > 0.1) return true;
    if (Math.abs((cEl.y ?? 0) - (bEl.y ?? 0)) > 0.1) return true;
    if (cEl.w !== undefined && bEl.w !== undefined && Math.abs(cEl.w - bEl.w) > 0.1) return true;
    if (cEl.h !== undefined && bEl.h !== undefined && Math.abs(cEl.h - bEl.h) > 0.1) return true;
  }

  // 4. Check for theme color changes
  const cColors = current.theme?.colors || {};
  const bColors = standardBase.theme?.colors || {};
  for (const key of ["background", "primary", "secondary", "accent", "text"] as const) {
    if (cColors[key] !== bColors[key]) return true;
  }

  return false;
}
