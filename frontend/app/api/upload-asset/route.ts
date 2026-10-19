import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get("content-type") || "";
    let filename = "";
    let buffer: Buffer;
    let mimeType = "image/png";

    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData();
      const file = formData.get("file") as File | null;
      if (!file) {
        return NextResponse.json({ error: "No file provided" }, { status: 400 });
      }
      const rawName = file.name || "uploaded_image.png";
      const bytes = await file.arrayBuffer();
      buffer = Buffer.from(bytes);
      mimeType = file.type || "image/png";
      const ext = path.extname(rawName) || ".png";
      const baseName = path.basename(rawName, ext).replace(/[^a-zA-Z0-9_-]/g, "_");
      filename = `upload_${Date.now()}_${baseName}${ext}`;
    } else {
      const json = await req.json();
      const rawBase64 = json.base64 || "";
      const rawName = json.filename || "uploaded_image.png";
      mimeType = json.mimeType || "image/png";
      const base64Data = rawBase64.replace(/^data:image\/\w+;base64,/, "");
      buffer = Buffer.from(base64Data, "base64");
      const ext = path.extname(rawName) || ".png";
      const baseName = path.basename(rawName, ext).replace(/[^a-zA-Z0-9_-]/g, "_");
      filename = `upload_${Date.now()}_${baseName}${ext}`;
    }

    const artDir = path.join(process.cwd(), "public", "art");
    await fs.mkdir(artDir, { recursive: true });
    const targetPath = path.join(artDir, filename);
    await fs.writeFile(targetPath, buffer);

    const relativeRepoPath = `frontend/public/art/${filename}`;
    const dataUrl = `data:${mimeType};base64,${buffer.toString("base64")}`;

    return NextResponse.json({
      success: true,
      filename,
      publicPath: `/art/${filename}`,
      relativeRepoPath,
      dataUrl,
    });
  } catch (error: any) {
    console.error("Asset upload error:", error);
    return NextResponse.json(
      { error: error?.message || "Failed to upload asset" },
      { status: 500 }
    );
  }
}
