import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse, type NextRequest } from "next/server";
import { isIndexed } from "@/lib/library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const VAULT = process.env.VAULT_PATH ?? "";
const TYPES: Record<string, string> = { ".pdf": "application/pdf", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8" };

// GET ?id=<document key>: the original file of a document that has no web address (a PDF you dropped into the Library
// folder). The key must be a document the index holds; the path is then checked to stay inside the vault. Markdown and
// text are sent as plain text, and nothing is ever sent as HTML, so a hostile file cannot run in the page.
export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id") ?? "";
  if (!VAULT || !id || id.length > 600 || id.includes("..") || !isIndexed(id)) return new NextResponse("Not found", { status: 404 });
  const root = path.resolve(VAULT);
  const file = path.resolve(root, id);
  const type = TYPES[path.extname(file).toLowerCase()];
  if (!type || !file.startsWith(root + path.sep)) return new NextResponse("Not found", { status: 404 });
  try {
    const body = await fs.readFile(file);
    return new NextResponse(new Uint8Array(body), {
      headers: {
        "content-type": type,
        "content-disposition": `inline; filename="${encodeURIComponent(path.basename(file))}"`,
        "x-content-type-options": "nosniff",
        "content-security-policy": "sandbox",
      },
    });
  } catch {
    return new NextResponse("The file is no longer on disk.", { status: 404 });
  }
}
