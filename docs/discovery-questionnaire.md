# Discovery questionnaire

Questions to answer with a customer **before** deploying this system. Each one
maps to a concrete configuration decision or a known limit, so the answers are
not just conversation - they change what gets built and how it is set up.

## 1. The decision behind the report
| Ask | Why it matters | Where it lands |
|---|---|---|
| What decision will a report support, and who signs off on it? | Determines the methodology (evidence review, technology comparison, landscape scan) and how much citation rigour is needed. | Goal text + clarifying answers; the plan's outline |
| Who reads it: clinicians, engineers, executives? | Sets depth and vocabulary. | Clarifying questions ("audience") |
| What does a *wrong* report cost? | Decides whether every claim must be human-verified, and how much review time to budget. | Review process; see "Limits" below |

## 2. The documents
| Ask | Why it matters | Where it lands |
|---|---|---|
| Where do the documents live (shared drive, SharePoint, email exports, EHR exports)? | The knowledge base ingests a folder; anything else needs an export step. | Ingestion runbook |
| Formats and volume (PDF/DOCX/HTML, how many, how large)? | Docling converts about 1-4 minutes per paper-sized PDF on CPU; a large backlog is an overnight job. | `scripts/ingest_library.py` |
| Scanned/image-only PDFs? | Text extraction needs OCR; slower and less reliable. Tables in scans are the hardest case. | Set expectations up front |
| How often do documents change, and are old versions superseded? | Ingestion is incremental by file hash, but it does not know a newer policy replaces an older one. | Naming/versioning convention |
| Are there documents that must *never* be mixed in one report (different tenants, patients, clients)? | One knowledge base = one retrieval scope. | One KB file per scope (`KB_PATH`) |

## 3. Data sensitivity and deployment
| Ask | Why it matters | Where it lands |
|---|---|---|
| Can documents leave the machine or network at all? | If not, this system is a fit: all models run locally via Ollama, nothing is sent to an API. | [Deployment runbook](deployment-runbook.md), air-gapped section |
| Does any document contain patient or personal data? | Reports quote sources verbatim, so PII in sources can reach a report. | De-identify before ingest, or restrict who reads reports |
| Who administers the machine, and what hardware exists (GPU, RAM)? | An 8 GB GPU runs 8B models fully on-GPU; larger models spill to CPU and slow down sharply. | Model roles (`DOCKER_PLANNER_MODEL`, `DOCKER_EXTRACTOR_MODEL`, `DOCKER_WRITER_MODEL`) |
| Is Docker permitted? Linux, Windows, or both? | Compose is the supported install; Windows also has an autostart script. | Runbook |

## 4. How they want to work with it
| Ask | Why it matters | Where it lands |
|---|---|---|
| Should the agent ask questions before starting, or run unattended? | Interrupt-based clarification and plan approval can be turned off for batch/overnight use. | per-run `ask_clarifying_questions`, `require_plan_approval` |
| How long may a run take (20 minutes, or overnight)? | Depth is bounded by time, not by cost, since models are local. | Number of sub-questions, passages per question |
| Where should reports land (Obsidian vault, shared folder, wiki)? | Reports are markdown with frontmatter, written to a vault folder. | `VAULT_PATH` |
| Who gives feedback on report quality, and how? | The system improves only from feedback that is written down. | Feedback notes in the vault (planned) |

## 5. Success criteria (agree these on day one)
- A fixed set of 20-30 real questions whose answers are known, used to measure
  retrieval recall on *their* documents (`scripts/eval_retrieval.py`).
- A sample of extracted claims labelled by their domain expert, used to measure
  how often the automatic faithfulness check agrees with a human
  (`scripts/make_faithfulness_sheet.py`, `scripts/score_faithfulness.py`).
- A time budget per report and an acceptable review effort per report.

## Limits to state plainly
- Reports are only as good as the library: with no evidence, a section says so
  instead of guessing, but a *thin* library gives thin reports.
- Claims are checked for a verbatim supporting quote and by a second model, but
  the sources themselves are not fact-checked.
- Local 8B models write competent but not exceptional prose; treat the output
  as a cited first draft for an expert, not a finished document.
