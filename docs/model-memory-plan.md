# Model, memory and finishing plan (rewritten 2026-10-01 with measurements; supersedes the earlier draft)

> **Superseded for planning by [`SCOPE.md`](SCOPE.md) v2 (2026-10-12) and [`STATUS.md`](STATUS.md).** Kept as history; open items from here are carried into the phase docs and `ERROR_LOG.md`.

Goal: finish project 4 in 2-3 days. This is the last or second-to-last fix round for speed and memory.

## Evidence (measured on 2026-10-01, machine in its normal working state)

**1. Runs were fast earlier and are 5-10x slower now, with the same code and models.** Seconds per question, from the run records:

| Run (start) | Seconds per question |
|---|---|
| Small-model goal, 16:49 on 30 Sep | 235, 152, 154, 179, 150, 120, 154, 136, 132, 143 |
| Hybrid retrieval goal, 04:18 | 96, 93, 72, 83, 106, 88, 34 |
| Chunking goal, 04:33 | 44, 115, 33, 53, 63, 51 |
| **Chunking goal, 09:23 (today, slow)** | **409, 1483, 812, 666, 316, 517** |

A writing step in the same run took 12 minutes for one section. Nothing in the pipeline changed between 04:33 and 09:23 except
the quality stages (coverage, relevance flag), which add calls but cannot explain 25 minutes for one question.

**2. The machine is paging heavily.** Committed memory is about 76 GB against 23.6 GB of RAM, with the page file at 19.5 GB used.
Available RAM was 1.6 GB. Largest committed (private) memory by process:

| Process | Committed | In RAM now | Notes |
|---|---|---|---|
| python (PID 45288) | **15.1 GB** | 0.02 GB | started 28 Sep, runs `...\.claude\jobs\aeaf5167\tmp\run_node284_demo.py`; not part of this project; paged out |
| llama-server | 5.9 GB | 1.1 GB | Ollama's model runner |
| vmmem + vmmemWSL | **7.6 GB** | 0.6 GB | **Docker Desktop's VM. I started Docker Desktop on 30 Sep for the acceptance test and never closed it** |
| msedgewebview2 | 3.1 GB | 3.0 GB | a WebView2 app |
| claude | 1.2 GB | 0.2 GB | |
Sum of private memory over all processes: 60 GB.

**3. gemma4:e4b is not a GPU-fit problem.** Ollama's own log for gemma4:e4b: all 43 of 43 layers on the GPU (2.8 GB of weights
on the GPU), plus **5.4 GB of weights memory-mapped from system RAM**. The GPU is not the bottleneck; **gemma needs about 5.4 GB of free
system RAM to run**, which was not available. The earlier belief "a 9.6 GB model does not fit 8 GB, so it spills onto the CPU" is
only half right: the compute is on the GPU, the embedding tables live in RAM.

**4. Ollama is a recent version (0.34.3)** with only `OLLAMA_ORIGINS` set. Our code sets no `keep_alive`, `num_gpu` or memory options.

**5. (Found 2026-10-01 afternoon, after Docker was closed and RAM rose from 2.4 to 4.6 GB) The GPU is power-capped.** The plan-only
baseline took 3m47s for planning (about 10 s on a healthy day). `nvidia-smi` under load: 100% utilisation at **180 MHz against a 3,090 MHz
maximum**, 21.7 W, throttle reason "software power cap", **GPU ceiling power limit 10 W against an 80 W default**. Windows is on Best
performance and the laptop (HP OMEN 16) reports AC power but charging at only 3.6 W while the GPU is busy. The cap is set outside Windows
(HP OMEN firmware/Command Center performance mode, or an undersized or loose charger): we cannot change it from this project. This
explains slowdowns of 5-10x better than memory does, and it also explains why a 240 s per-call limit that was fine on 30 Sep killed
writer calls today. Also seen: with llama (5.8 GB) and the embedding model (2.4 GB at 4k context) loaded, VRAM is 7.8 of 8.1 GB.
The coverage result of "7 nothing" in that baseline was not validated (it may be genuine, or the judge calls may have been disturbed).

**What this says:** the main cause is system memory taken by other things (a 3-day-old 15 GB python job, Docker's VM, a WebView2 app),
not model choice and not missing model-swap logic. Model scheduling helps at the margin; freeing memory is what restores speed.
The earlier plan put the model scheduler first; the evidence puts hygiene and a preflight check first.

## Plan (3 days)

### Day 1: make runs fast and keep them fast (about 4-5 hours)
| # | Task | Evidence it addresses | Needs you? | Exit test |
|---|---|---|---|---|
| 1 | **Free memory.** Close Docker Desktop (I started it; `wsl --shutdown` after). Decide about the 15 GB python job (PID 45288, started 28 Sep; I will not touch it unless you say so). Close the WebView2 app if unused. | Evidence 2 | **Yes: your OK for the python job** | Available RAM above 8 GB |
| 2 | **Baseline.** One timed question on the quiet machine, then `ollama ps` for each model with gemma loaded. Saved in `docs/model-memory-measurements.md`. | Evidence 1, 3 | no | A per-question time, compared with the 04:33 run |
| 3 | **Preflight check in the app.** Before approval and before the write phase, read available RAM (and loaded models); under a threshold (default 6 GB) show a warning on the run page with what is large. Log tokens/s per phase so slowdowns show up while they happen. | Evidence 1, 2 | no | Test with a fake low-memory reading |
| 4 | **Explicit model unload** between phases (`keep_alive: 0`) and `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1` in `start-research-assistant.ps1` and the runbook. Small: a function in one module, called at three points. | Hypothesis 3, cheap insurance | no | Fake-Ollama test: no two chat models loaded at once |
| 5 | **Writer decision by measurement:** write one section with gemma4:e4b and with gemma3:4b (3.3 GB, would not need the RAM-mapped tables) on the quiet machine; keep gemma4:e4b only if the speed is acceptable. | Evidence 3 | no | Decision recorded with seconds per section |

### Day 2: finish the report-quality work (about 5-6 hours)
| # | Task | Exit test |
|---|---|---|
| 6 | **Deliverable-aware planning (stage 6, reduced).** Read the goal's "deliverable format" items and turn each into a section; build the key-papers table from sources by code (title, kind, link, best fact); mark decision table and plan as synthesis. Cut: risks-from-facts and the recipe builder (written as ordinary synthesis sections). | A goal with a numbered deliverable list produces one section per item, in order |
| 7 | **Dashboard (stage 7, reduced).** Evidence status and gap notes visible on the run page; the memory warning from task 3; browser click-through by you of `/deep`, `/runs`, `/`. | You can see coverage, collect choice, review lists and the warning in a browser |
| 8 | **Re-run the saved small-model goal** with collect-for-gaps on the quiet machine, compare with the original report on the plan's exit tests (contradictions, uncited numbers, deliverables present, gap sections honest). | Result recorded in `EVALS.md` |

### Day 3: close the project (about 3-4 hours)
| # | Task | Exit test |
|---|---|---|
| 9 | Fix what the day-2 re-run shows (budget one round; tune gate thresholds from the real numbers). | Re-run passes the exit tests or the gap is written down |
| 10 | Docs: README, runbook (memory checklist, Ollama settings), DECISIONS (what the measurements showed, including my Docker mistake), EVALS, next-steps; the final audit of tests, lint, a Docker build, and a live run. | 270+ tests pass, lint clean, one live run completes, handoff updated |

## Cut line (what I will not do in the 3 days)
Disagreement detection between sources, recursive crawling, `collect.py --web`, allow-list presets, a larger writer model, auto-tuning of thresholds,
and the CodeMitra repo. All are listed in `next-steps.md` as later work.

## What could still go wrong
- If speed does not come back after task 1, the cause is not memory alone: tasks 2 and 5 are there to find that out on day 1, not day 3.
- The coverage check and relevance flag add about 30 calls per run; that is a few minutes on a healthy machine and was not the cause of today's slowdown (evidence 1).
- Gate thresholds (3 facts, 2 documents) are untested on real data; day 2's re-run is the first real test.
