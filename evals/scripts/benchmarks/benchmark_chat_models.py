"""Benchmark candidate chat models on the two prompts that matter most for
this graph: JSON-mode query generation (generate_query) and unconstrained
summarization (summarize_sources).

Used to pick LOCAL_LLM. Run with Ollama running locally and the candidate
models already pulled:

    python evals/scripts/benchmarks/benchmark_chat_models.py
"""

import json
import time

from langchain_ollama import ChatOllama

MODELS = [
    "deepseek-r1:8b",
    "qwen3.5:4b",
    "qwen3.5:latest",
    "llama3.1:8b",
    "qwen3:8b",
    "ministral-3:8b",
    "granite4.1:8b",
]

QUERY_SYSTEM = """Your goal is to generate a targeted web search query.

<CONTEXT>
Current date: September 28, 2026
Please ensure your queries account for the most current information available as of this date.
</CONTEXT>

<TOPIC>
What is the Model Context Protocol (MCP)?
</TOPIC>

<FORMAT>
Format your response as a JSON object with ALL three of these exact keys:
- "query": The actual search query string
- "rationale": Brief explanation of why this query is relevant
</FORMAT>

Provide your response in JSON format:"""

SUMMARY_SYSTEM = """
<GOAL>
Generate a high-quality summary of the provided context.
</GOAL>

<REQUIREMENTS>
When creating a NEW summary:
1. Highlight the most relevant information related to the user topic from the search results
2. Ensure a coherent flow of information
</REQUIREMENTS>

< FORMATTING >
- Start directly with the updated summary, without preamble or titles. Do not use XML tags in the output.
< /FORMATTING >
"""

SUMMARY_HUMAN = """<Context>
The Model Context Protocol (MCP) is an open standard introduced by Anthropic that provides a universal way for AI models to connect with external data sources and tools. It uses a client-server architecture where MCP servers expose resources, prompts, and tools that MCP clients (like Claude Desktop) can access. This eliminates the need for custom integrations for every data source.
<Context>Create a Summary using the Context on this topic:
<User Input>
What is the Model Context Protocol (MCP)?
<User Input>"""


def strip_thinking(text: str) -> str:
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text


def bench_query_gen(model: str) -> tuple[float, bool]:
    llm = ChatOllama(model=model, temperature=0, format="json", base_url="http://localhost:11434")
    start = time.time()
    result = llm.invoke([("system", QUERY_SYSTEM), ("human", "Generate a query for web search:")])
    elapsed = time.time() - start
    try:
        valid = bool(json.loads(result.content).get("query"))
    except Exception:
        valid = False
    return elapsed, valid


def bench_summarize(model: str) -> tuple[float, bool]:
    llm = ChatOllama(model=model, temperature=0, base_url="http://localhost:11434")
    start = time.time()
    result = llm.invoke([("system", SUMMARY_SYSTEM), ("human", SUMMARY_HUMAN)])
    elapsed = time.time() - start
    stripped = strip_thinking(result.content).strip()
    return elapsed, bool(stripped)


def main():
    print(f"{'model':<20} {'query_gen':>12} {'summarize':>12} {'total':>10}  valid")
    for model in MODELS:
        try:
            t1, v1 = bench_query_gen(model)
            t2, v2 = bench_summarize(model)
            print(f"{model:<20} {t1:>10.1f}s {t2:>10.1f}s {t1 + t2:>8.1f}s  {v1 and v2}")
        except Exception as e:
            print(f"{model:<20} ERROR: {e}")


if __name__ == "__main__":
    main()
