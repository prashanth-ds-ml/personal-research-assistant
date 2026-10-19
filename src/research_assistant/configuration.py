import os
from enum import Enum
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class SearchAPI(Enum):
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    LOCAL_DOCS = "local_docs"


# Settings a caller may change for a single run (the dashboard form, the API). Everything else,
# notably every path and every service URL, is environment/default only. See from_runnable_config.
PER_RUN_KEYS = frozenset({
    "max_web_research_loops", "local_llm", "llm_provider", "search_api", "fetch_full_page",
    "strip_thinking_tokens", "use_tool_calling", "enable_vault_context", "vault_context_top_k",
    "archive_full_sources", "enable_profile_update", "notify_on_complete", "enable_comparison_planning",
    "max_comparison_entities", "planner_model", "extractor_model", "writer_model",
    "ask_clarifying_questions", "require_plan_approval", "auto_ingest", "collect_sources", "seed_urls",
    "fetch_max_sources", "fetch_min_relevance", "docs_retrieval_k", "docs_top_k", "docs_chunk_size",
    "contact_email", "collect_review", "include_archived_pages", "coverage_check", "claim_labels",
    "min_section_facts", "min_section_documents", "min_supported_share", "plan_thinking",
})


class Configuration(BaseModel):
    """The configurable fields for the research assistant."""

    max_web_research_loops: int = Field(
        default=3,
        title="Research Depth",
        description="Number of research iterations to perform",
    )
    local_llm: str = Field(
        default="llama3.2",
        title="LLM Model Name",
        description="Name of the LLM model to use",
    )
    llm_provider: Literal["ollama", "lmstudio"] = Field(
        default="ollama",
        title="LLM Provider",
        description="Provider for the LLM (Ollama or LMStudio)",
    )
    search_api: Literal[
        "perplexity", "tavily", "duckduckgo", "searxng", "local_docs"
    ] = Field(
        default="duckduckgo",
        title="Search API",
        description="Search backend: a web search API, or local_docs to search docs_path",
    )
    docs_path: str = Field(
        default="",
        title="Internal Docs Path",
        description="Folder of PDF/Markdown/text files searched when search_api=local_docs",
    )
    docs_top_k: int = Field(
        default=4,
        title="Docs Top K",
        description="Number of document chunks retrieved per search when search_api=local_docs",
    )
    docs_chunk_size: int = Field(
        default=1500,
        title="Docs Chunk Size",
        description="Characters per document chunk when search_api=local_docs",
    )
    fetch_full_page: bool = Field(
        default=True,
        title="Fetch Full Page",
        description="Include the full page content in the search results",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434/",
        title="Ollama Base URL",
        description="Base URL for Ollama API",
    )
    lmstudio_base_url: str = Field(
        default="http://localhost:1234/v1",
        title="LMStudio Base URL",
        description="Base URL for LMStudio OpenAI-compatible API",
    )
    strip_thinking_tokens: bool = Field(
        default=True,
        title="Strip Thinking Tokens",
        description="Whether to strip <think> tokens from model responses",
    )
    use_tool_calling: bool = Field(
        default=False,
        title="Use Tool Calling",
        description="Use tool calling instead of JSON mode for structured output",
    )

    # --- Personal research assistant additions ---
    vault_path: str = Field(
        default="",
        title="Obsidian Vault Path",
        description="Absolute path to the Obsidian vault this assistant reads/writes",
    )
    sources_subdir: str = Field(
        default="Sources",
        title="Sources Subdirectory",
        description="Vault subfolder where archived full source content is saved",
    )
    research_subdir: str = Field(
        default="Research",
        title="Research Subdirectory",
        description="Vault subfolder where finished research reports are saved",
    )
    profile_note_path: str = Field(
        default="Profile.md",
        title="Profile Note Path",
        description="Vault-relative path to the evolving personal profile note",
    )
    archive_full_sources: bool = Field(
        default=True,
        title="Archive Full Sources",
        description="Save each source's full fetched content to the vault's Sources folder",
    )
    enable_vault_context: bool = Field(
        default=True,
        title="Enable Vault Context",
        description="Retrieve relevant prior research notes from the vault before researching",
    )
    vault_context_top_k: int = Field(
        default=5,
        title="Vault Context Top K",
        description="Number of prior notes to retrieve as context",
    )
    embedding_model: str = Field(
        default="ollama:qwen3-embedding:0.6b",
        title="Embedding Model",
        description="init_embeddings()-style model string used for vault retrieval",
    )
    enable_profile_update: bool = Field(
        default=True,
        title="Enable Profile Update",
        description="Append a session log entry to the profile note after each run",
    )
    notify_on_complete: bool = Field(
        default=True,
        title="Notify On Complete",
        description="Show a native OS notification when a research run finishes",
    )
    enable_comparison_planning: bool = Field(
        default=True,
        title="Enable Comparison Planning",
        description=(
            "Detect whether a topic names 2+ things to compare and research each "
            "one independently and concurrently. Cheap (~10s) and empirically "
            "discriminates correctly; killswitch if it ever misfires on real usage."
        ),
    )
    max_comparison_entities: int = Field(
        default=4,
        title="Max Comparison Entities",
        description="Cap on how many conduct_research calls plan_research will honor in one turn",
    )
    # --- Goal-driven deep research (deep_research graph) ---
    kb_path: str = Field(
        default="",
        title="Knowledge Base Path",
        description="SQLite knowledge-base file; default <vault_path>/.kb/library.sqlite",
    )
    planner_model: str = Field(default="", title="Planner Model", description="Blank = local_llm")
    extractor_model: str = Field(default="", title="Extractor Model", description="Blank = local_llm")
    writer_model: str = Field(default="", title="Writer Model", description="Blank = local_llm")
    ask_clarifying_questions: bool = Field(
        default=True,
        title="Ask Clarifying Questions",
        description="Pause and ask the user a few questions about the goal before planning",
    )
    require_plan_approval: bool = Field(
        default=True,
        title="Require Plan Approval",
        description="Pause and show the research plan for approval before the expensive steps",
    )
    library_folders: str = Field(
        default="",
        title="Library Folders",
        description=(
            "Folders kept indexed, separated by ';'. Blank = <vault>/Sources and <vault>/Library. "
            "Each folder's name is its namespace in the knowledge base."
        ),
    )
    auto_ingest: bool = Field(
        default=True,
        title="Auto-Ingest",
        description="Index new or changed files in the library folders at the start of each deep-research run",
    )
    collect_sources: bool = Field(
        default=False,
        title="Fetch New Sources",
        description="After plan approval, fetch open-access papers (arXiv, Europe PMC) for the plan's questions",
    )
    seed_urls: str = Field(
        default="",
        title="Seed URLs",
        description="Pages or PDFs to fetch into the library before researching, separated by whitespace or ';'",
    )
    fetch_max_sources: int = Field(
        default=0, title="Max New Sources",
        description="Cap on sources saved per run. 0 = no limit (you choose what to collect in the review step)")
    collect_max_candidates: int = Field(
        default=0, title="Max Candidates",
        description="Cap on the total number of candidates shown for review. 0 = no cap (each question still gets "
                    "its own search; more candidates means more relevance checks and a longer list to review)")
    collect_europepmc: bool = Field(
        default=True, title="Search Europe PMC",
        description="Search Europe PMC (open-access biomedical papers). Turn off for AI or software topics: it only adds "
                    "unrelated medical papers there")
    collect_huggingface: bool = Field(
        default=True, title="Search Hugging Face",
        description="Also search Hugging Face Papers, model cards and dataset cards for each question")
    collect_ai_sites: bool = Field(
        default=True, title="Search AI Engineering Sites",
        description="Also run site-restricted web searches over the sites listed in collect_extra_sites")
    collect_extra_sites: str = Field(
        default=";".join(["sebastianraschka.com", "magazine.sebastianraschka.com", "karpathy.github.io", "karpathy.ai", "jalammar.github.io", "newsletter.languagemodels.co", "huggingface.co", "github.com", "docs.langchain.com", "anthropic.com", "openai.com", "ai.google.dev", "lilianweng.github.io", "eugeneyan.com", "huyenchip.com", "hamel.dev", "simonwillison.net", "pinecone.io"]),
        title="AI Engineering Sites",
        description="Sites for the extra searches, separated by ';' (the first 18 are used, in groups of six: one extra search per group). Edit to taste")
    fetch_min_relevance: int = Field(
        default=3, title="Min Relevance",
        description="Keep a fetched source only if the local model scores it at least this (0-3). 3 = directly answers "
                    "the question; 2 lets in tangential papers that then stay in the library")
    min_section_facts: int = Field(
        default=2, title="Passages Per Section",
        description="A report section is written from evidence only if its questions have at least this many useful passages "
                    "(v3: a whole passage carries more than one extracted fact did, so 2 instead of 3)")
    min_section_documents: int = Field(
        default=2, title="Documents Per Section",
        description="... from at least this many different documents; otherwise the section says what is missing")
    min_supported_share: float = Field(
        default=0.5, title="Supported Share",
        description="If fewer than this share of the evidence sections are supported, the report is a gap report: it gives "
                    "no recommendation and lists what to collect")
    plan_thinking: bool = Field(
        default=False, title="Think When Planning",
        description="Let the model think before writing the plan (about 85 s per planning call instead of 8 s with "
                    "qwen3.5:4b; plans then vary between runs). Other steps never think.")
    claim_labels: bool = Field(
        default=True, title="Label Claims",
        description="Mark every sentence [established], [single source], [inference] or [inference: figures not from sources]")
    coverage_check: bool = Field(
        default=True, title="Coverage Check",
        description="Before asking you to approve the plan, check what the library can answer for each question "
                    "(answered / thin / nothing) so you can collect sources for the gaps first")
    include_archived_pages: bool = Field(
        default=False, title="Include Archived Pages",
        description="Deep research leaves out copies of your own documents that the quick assistant archived into the "
                    "vault's Sources folder (they only repeat files already in the library). Turn on to search them too")
    search_backend: Literal["ddgs", "searxng"] = Field(
        default="ddgs", title="Web Search Backend",
        description="Where the source collector finds web pages: DuckDuckGo (ddgs) or your SearXNG instance")
    searxng_url: str = Field(
        default="", title="SearXNG URL",
        description="Address of your SearXNG instance, used when the search backend is searxng (environment only)")
    collect_allow_domains: str = Field(
        default="", title="Allowed Domains",
        description="Only collect web pages from these domains, separated by ';' (for example who.int;cdc.gov;*.gov.in). "
                    "Blank = any public site")
    collect_block_domains: str = Field(
        default="", title="Blocked Domains", description="Never collect from these domains, separated by ';'")
    collect_candidates_per_question: int = Field(
        default=8, title="Candidates Per Question", description="Web pages shown per plan question (papers come on top)")
    collect_review: bool = Field(
        default=True, title="Review Sources",
        description="Pause and show the candidate pages and papers so you choose which to collect. Off = collect "
                    "everything scoring at least the minimum relevance (for unattended runs)")
    contact_email: str = Field(
        default="", title="Contact Email",
        description="Put in the fetcher's User-Agent so site owners can reach you (good manners; optional)")
    docs_retrieval_k: int = Field(
        default=8,
        title="Passages Per Question",
        description="Passages retrieved per sub-question in deep research",
    )

    @classmethod
    def from_runnable_config(
        cls, config: RunnableConfig | None = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig.

        Precedence for each setting: environment variable (NAME in upper case) > the run's
        ``configurable`` dict > the class default. Two rules make this safe to expose:

        * An environment variable that is set but EMPTY counts as unset (docker-compose passes
          blanks for unset options; they must not beat a per-run value).
        * Only the keys in ``PER_RUN_KEYS`` may be set per run. Paths and service URLs (vault, knowledge
          base, library folders, Ollama/LM Studio address) come only from the environment or defaults,
          because a per-run override would let whoever can reach the API point the assistant at
          arbitrary folders or hosts.
        """
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        values: dict[str, Any] = {}
        for name in cls.model_fields:
            env = os.environ.get(name.upper())
            if env:
                values[name] = env
            elif name in PER_RUN_KEYS and configurable.get(name) is not None:
                values[name] = configurable[name]

        return cls(**values)
