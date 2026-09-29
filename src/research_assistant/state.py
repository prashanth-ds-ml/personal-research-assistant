import operator
from dataclasses import dataclass, field

from typing_extensions import Annotated


@dataclass(kw_only=True)
class SummaryState:
    research_topic: str = field(default=None)  # Report topic
    search_query: str = field(default=None)  # Search query
    web_research_results: Annotated[list, operator.add] = field(default_factory=list)
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list)
    research_loop_count: int = field(default=0)  # Research loop count
    running_summary: str = field(default=None)  # Final report

    # Personal research assistant additions
    run_date: str = field(default=None)  # e.g. "2026-09-28", set once in load_profile
    topic_slug: str = field(default=None)  # e.g. "mcp-explained", set once in load_profile
    profile_content: str = field(default="")  # Contents of Profile.md, read in load_profile
    vault_context: str = field(default="")  # Relevant prior notes, set in retrieve_vault_context
    knowledge_gaps: Annotated[list, operator.add] = field(default_factory=list)
    archived_sources: Annotated[list, operator.add] = field(default_factory=list)
    report_path: str = field(default=None)  # Absolute path to the written Obsidian note
    advocate_view: str = field(default="")  # Debate mode: GPU model's case for the findings
    critic_view: str = field(default="")  # Debate mode: CPU model's concerns/caveats
    entity_topics: list = field(default_factory=list)  # Set by plan_research; len<2 means not a comparison
    entity_research: list = field(default_factory=list)  # Set by parallel_research; each: {topic, summary, loops}


@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: str = field(default=None)  # Report topic


@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: str = field(default=None)  # Final report
    report_path: str = field(default=None)  # So callers (e.g. the dashboard) can link to it
