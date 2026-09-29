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
    search_api: Literal["perplexity", "tavily", "duckduckgo", "searxng"] = Field(
        default="duckduckgo", title="Search API", description="Web search API to use"
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
    enable_debate_mode: bool = Field(
        default=False,
        title="Enable Debate Mode",
        description="Run a GPU advocate and a CPU-pinned critic concurrently before finalizing",
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
    debate_cpu_model: str = Field(
        default="gemma3:4b",
        title="Debate CPU Model",
        description=(
            "Smaller model pinned to CPU (num_gpu=0) for the debate's critic voice. "
            "Deliberately a different model family than local_llm (Google Gemma vs. "
            "Meta Llama by default) - same-family models share training data/alignment "
            "and produce a much weaker, more agreeable 'debate'."
        ),
    )

    @classmethod
    def from_runnable_config(
        cls, config: RunnableConfig | None = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)
