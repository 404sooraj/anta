import { NextRequest, NextResponse } from "next/server";
import path from "node:path";
import fs from "node:fs/promises";
import type { ProcessedCallData, Ps2AnalysisListItem } from "@/types/analysis";

const JSON_EXT = ".json";

/** Only allow safe filenames: alphanumeric, underscore, hyphen, period. No path traversal. */
function isSafeFilename(name: string): boolean {
  return /^[a-zA-Z0-9_.-]+$/.test(name) && name.endsWith(JSON_EXT);
}

function isSafeId(id: string): boolean {
  return /^[a-zA-Z0-9_.-]+$/.test(id) && !id.includes("..") && !id.includes("/");
}

function getOutputDir(): string {
  const envPath = process.env.ANALYSIS_OUTPUT_PATH;
  if (envPath) return path.resolve(envPath);
  return path.join(process.cwd(), "..", "data-normalization", "output");
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  const outputDir = getOutputDir();

  try {
    const stat = await fs.stat(outputDir);
    if (!stat.isDirectory()) {
      return NextResponse.json(
        { error: "Analysis output path is not a directory" },
        { status: 500 }
      );
    }
  } catch (err) {
    return NextResponse.json(
      { error: "Analysis output directory not found", list: [] },
      { status: 200 }
    );
  }

  if (id !== null && id !== undefined && id !== "") {
    if (!isSafeId(id)) {
      return NextResponse.json({ error: "Invalid id" }, { status: 400 });
    }
    const filename = id.endsWith(JSON_EXT) ? id : `${id}${JSON_EXT}`;
    if (!isSafeFilename(filename)) {
      return NextResponse.json({ error: "Invalid id" }, { status: 400 });
    }
    const filePath = path.join(outputDir, filename);
    try {
      const raw = await fs.readFile(filePath, "utf-8");
      const data = JSON.parse(raw) as ProcessedCallData;
      return NextResponse.json(data);
    } catch {
      return NextResponse.json(
        { error: "Analysis not found" },
        { status: 404 }
      );
    }
  }

  const entries = await fs.readdir(outputDir);
  const jsonFiles = entries.filter((e) => e.endsWith(JSON_EXT) && isSafeFilename(e));
  const list: Ps2AnalysisListItem[] = [];

  for (const filename of jsonFiles) {
    const filePath = path.join(outputDir, filename);
    try {
      const raw = await fs.readFile(filePath, "utf-8");
      const data = JSON.parse(raw) as ProcessedCallData;
      const itemId = filename.slice(0, -JSON_EXT.length);
      list.push({
        id: itemId,
        filename,
        metadata: data.metadata,
        partnerSatisfactionScore: data.analysis.partnerSatisfactionScore,
      });
    } catch {
      // skip invalid/corrupt files
    }
  }

  return NextResponse.json({ list });
}
