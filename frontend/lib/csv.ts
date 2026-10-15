/**
 * Lightweight client-side CSV parser adhering to RFC 4180.
 * Handles quoted cells, commas, escaped quotes (""), and UTF-8 BOM.
 */

import { Person } from "../types";

export interface ParsedCsv {
  headers: string[];
  rows: Record<string, string>[];
  people: Person[];
  skippedRows: Record<string, any>[];
}

export function parseCsvText(text: string, columnMapping?: Record<string, string>): ParsedCsv {
  // Strip BOM if present
  let cleanText = text;
  if (cleanText.charCodeAt(0) === 0xfeff) {
    cleanText = cleanText.slice(1);
  }

  const lines = parseCsvLines(cleanText);
  if (lines.length === 0) {
    return { headers: [], rows: [], people: [], skippedRows: [] };
  }

  const headers = lines[0].map((h) => h.trim().toLowerCase());
  const rows: Record<string, string>[] = [];
  const people: Person[] = [];
  const skippedRows: Record<string, any>[] = [];

  // Determine standard field keys
  const mapping = columnMapping || {
    name: headers.find((h) => h.includes("name")) || "name",
    role: headers.find((h) => h.includes("role") || h.includes("type")) || "role",
    id: headers.find((h) => h.includes("id") || h.includes("roll")) || "id",
    team: headers.find((h) => h.includes("team") || h.includes("org")) || "team",
    email: headers.find((h) => h.includes("email") || h.includes("mail")) || "email",
    photo: headers.find((h) => h.includes("photo") || h.includes("image")) || "photo",
  };

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    // Skip empty lines
    if (line.length === 0 || (line.length === 1 && line[0].trim() === "")) {
      continue;
    }

    const rowObj: Record<string, string> = {};
    for (let j = 0; j < headers.length; j++) {
      rowObj[headers[j]] = line[j] !== undefined ? line[j].trim() : "";
    }
    rows.push(rowObj);

    // Extract person fields based on mapping
    const nameCol = mapping["name"] || "name";
    const name = rowObj[nameCol] || rowObj["name"] || "";

    if (!name || name.trim() === "") {
      skippedRows.push({ row_index: i, reason: "Missing name", raw: rowObj });
      continue;
    }

    const roleCol = mapping["role"] || "role";
    const rawRole = (rowObj[roleCol] || rowObj["role"] || "participant").toLowerCase();
    const validRoles = ["participant", "organizer", "mentor", "volunteer"];
    const role = validRoles.includes(rawRole) ? rawRole : "participant";

    const idCol = mapping["id"] || "id";
    const id = rowObj[idCol] || rowObj["id"] || `ATT-${i.toString().padStart(3, "0")}`;

    const teamCol = mapping["team"] || "team";
    const team = rowObj[teamCol] || rowObj["team"] || undefined;

    const emailCol = mapping["email"] || "email";
    const email = rowObj[emailCol] || rowObj["email"] || undefined;

    const photoCol = mapping["photo"] || "photo";
    const photo = rowObj[photoCol] || rowObj["photo"] || undefined;

    people.push({
      name: name.trim(),
      role,
      id: id.trim(),
      team: team?.trim(),
      email: email?.trim(),
      photo: photo?.trim(),
    });
  }

  return {
    headers,
    rows,
    people,
    skippedRows,
  };
}

function parseCsvLines(text: string): string[][] {
  const result: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;
  let i = 0;

  while (i < text.length) {
    const char = text[i];
    const nextChar = i + 1 < text.length ? text[i + 1] : "";

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          cell += '"';
          i += 2;
          continue;
        } else {
          inQuotes = false;
          i++;
          continue;
        }
      } else {
        cell += char;
        i++;
        continue;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
        i++;
        continue;
      } else if (char === ",") {
        row.push(cell);
        cell = "";
        i++;
        continue;
      } else if (char === "\r") {
        if (nextChar === "\n") {
          i++;
        }
        row.push(cell);
        result.push(row);
        row = [];
        cell = "";
        i++;
        continue;
      } else if (char === "\n") {
        row.push(cell);
        result.push(row);
        row = [];
        cell = "";
        i++;
        continue;
      } else {
        cell += char;
        i++;
        continue;
      }
    }
  }

  if (cell !== "" || row.length > 0) {
    row.push(cell);
    result.push(row);
  }

  return result;
}
