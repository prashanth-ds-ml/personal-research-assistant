"""How authoritative a source is, by what it is and where it lives: 3 paper, 2 official documentation, 1 other web page.

Used to break ties, never to override relevance: candidates are ordered by relevance grade first and authority second, and
an unattended run also takes papers and docs one grade below the bar. The 2026-10-20 audit found 15 of 16 report sources were
web or blog guides (they score 3 on practical questions, paper abstracts often 2), with this unused.
"""
from urllib.parse import urlparse

PAPER, DOCS, WEB = 3, 2, 1          # DOCS = official documentation and the AI-engineering expert sites
PAPER_HOSTS = ("arxiv.org", "aclanthology.org", "openreview.net", "europepmc.org", "ncbi.nlm.nih.gov", "dl.acm.org",
               "ieeexplore.ieee.org", "link.springer.com", "nature.com", "sciencedirect.com", "proceedings.mlr.press",
               "papers.nips.cc", "proceedings.neurips.cc", "semanticscholar.org", "aaai.org", "jmlr.org")
# Where AI engineers publish (the collector's site-restricted searches use this list too): the user's primary domain is
# technical material on LLMs, AI engineering, FDE, agents and LangChain (2026-10-20), so these rank with official docs.
AI_SITES = ["sebastianraschka.com", "magazine.sebastianraschka.com", "karpathy.github.io", "karpathy.ai", "jalammar.github.io",
            "newsletter.languagemodels.co", "huggingface.co", "github.com", "docs.langchain.com", "anthropic.com", "openai.com",
            "ai.google.dev", "lilianweng.github.io", "eugeneyan.com", "huyenchip.com", "hamel.dev", "simonwillison.net",
            "pinecone.io"]
DOCS_HOSTS = tuple(AI_SITES) + (
    "readthedocs.io", "pytorch.org", "python.langchain.com", "langchain.com", "langchain-ai.github.io", "llamaindex.ai",
    "ollama.com", "qdrant.tech", "weaviate.io", "milvus.io", "elastic.co", "sbert.net", "learn.microsoft.com",
    "cloud.google.com", "docs.aws.amazon.com", "deepmind.google", "mistral.ai", "cohere.com", "vllm.ai", "nvidia.com")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").removeprefix("www.").lower()
    except ValueError:
        return ""


def _under(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def authority(url: str = "", kind: str = "") -> int:
    """3 for a paper (a paper source or PDF, or a paper host), 2 for official documentation (a docs.* host or a known
    project / docs site), 1 for any other web page."""
    host = _host(url)
    if kind in ("paper", "pdf") or _under(host, PAPER_HOSTS) or url.lower().split("?")[0].endswith(".pdf"):
        return PAPER
    if host.startswith("docs.") or _under(host, DOCS_HOSTS):
        return DOCS
    return WEB
