"""Benchmark small models, pinned fully to CPU (num_gpu=0), as debate mode's
critic voice. Speed matters since the critic runs concurrently with the GPU
advocate and shouldn't become the bottleneck; quality matters because a weak
critic just produces generic skepticism instead of a real critique.

Run with Ollama running locally and the candidate models already pulled:

    python scripts/benchmarks/benchmark_debate_critic.py
"""

import time

from langchain_ollama import ChatOllama

MODELS = ["llama3.2:3b", "qwen3.5:2b", "gemma3:4b"]

SYSTEM = (
    "You are a skeptical critic. Given a research summary, argue for why it might be "
    "incomplete, biased, or wrong. Be specific and concise (3-4 sentences)."
)
HUMAN = (
    "Summary: The Model Context Protocol (MCP) is an open standard that lets AI models "
    "connect to external tools and data sources via a client-server architecture, "
    "eliminating custom integrations."
)


def main():
    for model in MODELS:
        llm = ChatOllama(model=model, temperature=0.3, base_url="http://localhost:11434", num_gpu=0)
        start = time.time()
        result = llm.invoke([("system", SYSTEM), ("human", HUMAN)])
        elapsed = time.time() - start
        print(f"=== {model} ({elapsed:.1f}s, {len(result.content)} chars) ===")
        print(result.content)
        print()


if __name__ == "__main__":
    main()
