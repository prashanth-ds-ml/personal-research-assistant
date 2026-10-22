"""Benchmark candidate models on multi-parallel-tool-calling reliability - the
mechanism comparison mode's plan_research node depends on. Tests both a
positive case (a real 3-way comparison, should call the tool 3 times in one
turn) and a negative case (a plain single topic, should call it exactly
once - not habitually over-split).

Used to decide whether comparison mode needed a different model than the
existing default. Run with Ollama running locally and the candidate models
already pulled:

    python evals/scripts/benchmarks/benchmark_tool_calling.py
"""

import time

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

MODELS = [
    "llama3.1:8b",
    "qwen3:8b",
    "ministral-3:8b",
    "granite4.1:8b",
    "qwen3.5:latest",
    "llama3.2:3b",
    "qwen2.5-coder:7b",
    "lfm2.5:8b",
]


@tool
def conduct_research(research_topic: str) -> str:
    """Research one specific, standalone sub-topic. Call this once per distinct
    sub-topic that needs independent research (e.g. once per entity being compared)."""
    return "stub"


SYSTEM = """You are a research supervisor. Given a user's research request, decide whether it names \
multiple distinct things that should be researched independently and compared.

<SCALING RULES>
- Comparisons presented in the user request can use a sub-agent for each element of the comparison.
  Example: "Compare OpenAI vs. Anthropic vs. DeepMind approaches to AI safety" -> call conduct_research \
  3 times in this same turn, once per company, each with a specific standalone research_topic.
- Delegate clear, distinct, non-overlapping subtopics.
- If the request is about a SINGLE topic with no explicit comparison, call conduct_research ONCE with \
  the whole topic as-is. Do not invent a comparison that isn't there.
</SCALING RULES>

Call the conduct_research tool once for each sub-topic that needs independent research."""

POSITIVE_CASE = "Compare PostgreSQL vs. MongoDB vs. Redis for a high-write-throughput analytics workload."
NEGATIVE_CASE = "What is the Model Context Protocol (MCP) and why does it matter for AI agents?"


def run_case(model: str, human: str) -> tuple[float, int, list[str]]:
    llm = ChatOllama(model=model, temperature=0, base_url="http://localhost:11434").bind_tools(
        [conduct_research]
    )
    start = time.time()
    result = llm.invoke([("system", SYSTEM), ("human", human)])
    elapsed = time.time() - start
    topics = [c["args"].get("research_topic", "?")[:40] for c in result.tool_calls]
    return elapsed, len(result.tool_calls), topics


def main():
    print(f"{'model':<20} {'positive (want 3)':<45} {'negative (want 1)'}")
    for model in MODELS:
        try:
            t1, n1, topics1 = run_case(model, POSITIVE_CASE)
            t2, n2, _ = run_case(model, NEGATIVE_CASE)
            print(f"{model:<20} {t1:>5.1f}s n_calls={n1} {str(topics1)[:35]:<35} | {t2:>5.1f}s n_calls={n2}")
        except Exception as e:
            print(f"{model:<20} ERROR: {e}")


if __name__ == "__main__":
    main()
