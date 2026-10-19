// Safe to import from client components (no file or database access here).
export type DocKind = "pdf" | "web" | "hf" | "doc";

export interface LibraryDoc {
  /** The document's key in the index: "<library folder>/<path inside it>". */
  id: string;
  title: string;
  kind: DocKind;
  /** Host name for web pages, otherwise the goal folder it was collected for, or "your documents". */
  site: string;
  url: string;
  added: string;
  folder: string;
  chunks: number;
  /** Facts the reports have used from this document, summed over every run. */
  facts: number;
  /** "ok", "empty" or "failed": a failed or empty document is listed but never searched. */
  status: string;
  error: string;
}

const KIND_LABEL: Record<DocKind, string> = { pdf: "PDF", web: "Web page", hf: "Hugging Face", doc: "Local" };
export const kindLabel = (k: DocKind) => KIND_LABEL[k];
