import asyncio
import json
from datetime import datetime

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import Literal

from research_assistant import vault
from research_assistant.configuration import Configuration
from research_assistant.documents import local_docs_search
from research_assistant.lmstudio import ChatLMStudio
from research_assistant.notifications import notify_run_complete
from research_assistant.prompts import (
    comparison_planning_instructions,
    comparison_report_synthesis_instructions,
    get_current_date,
    json_mode_query_instructions,
    json_mode_reflection_instructions,
    profile_context_block,
    profile_update_instructions,
    query_writer_instructions,
    reflection_instructions,
    report_synthesis_instructions,
    summarizer_instructions,
    tool_calling_query_instructions,
    tool_calling_reflection_instructions,
    vault_context_block,
)
from research_assistant.state import (
    SummaryState,
    SummaryStateInput,
    SummaryStateOutput,
)
from research_assistant.utils import (
    deduplicate_and_format_sources,
    duckduckgo_search,
    format_sources,
    get_config_value,
    perplexity_search,
    searxng_search,
    strip_thinking_tokens,
    tavily_search,
)

# Constants
MAX_TOKENS_PER_SOURCE = 1000
PROFILE_MAX_CHARS = 6000          # how much of Profile.md may be pasted into a prompt
CHARS_PER_TOKEN = 4

def generate_search_query_with_structured_output(
    configurable: Configuration,
    messages: list,
    tool_class,
    fallback_query: str,
    tool_query_field: str,
    json_query_field: str,
    secondary_field: str | None = None,
):
    """Helper function to generate search queries using either tool calling or JSON mode.

    Args:
        configurable: Configuration object
        messages: List of messages to send to LLM
        tool_class: Tool class for tool calling mode
        fallback_query: Fallback search query if extraction fails
        tool_query_field: Field name in tool args containing the query
        json_query_field: Field name in JSON response containing the query
        secondary_field: Optional second field name to also extract (e.g. a
            rationale/knowledge-gap field), returned under the same key.

    Returns:
        Dictionary with a "search_query" key, and the secondary_field key if given.
    """
    def _with_secondary(out: dict, source: dict | None) -> dict:
        if secondary_field:
            out[secondary_field] = source.get(secondary_field) if source else None
        return out

    if configurable.use_tool_calling:
        llm = get_llm(configurable).bind_tools([tool_class])
        result = llm.invoke(messages)

        if not result.tool_calls:
            return _with_secondary({"search_query": fallback_query}, None)

        try:
            tool_data = result.tool_calls[0]["args"]
            search_query = tool_data.get(tool_query_field)
            return _with_secondary({"search_query": search_query}, tool_data)
        except (IndexError, KeyError):
            return _with_secondary({"search_query": fallback_query}, None)

    else:
        # Use JSON mode
        llm = get_llm(configurable)
        result = llm.invoke(messages)
        content = result.content
        if configurable.strip_thinking_tokens:
            content = strip_thinking_tokens(content)     # strip BEFORE parsing: thinking models put JSON after </think>

        try:
            parsed_json = json.loads(content)
            if not isinstance(parsed_json, dict):
                raise ValueError("model returned JSON that is not an object")
            search_query = parsed_json.get(json_query_field)
            if not search_query:
                return _with_secondary({"search_query": fallback_query}, parsed_json)
            return _with_secondary({"search_query": search_query}, parsed_json)
        except (json.JSONDecodeError, ValueError, KeyError):
            return _with_secondary({"search_query": fallback_query}, None)

def get_llm(configurable: Configuration):
    """Helper function to initialize LLM based on configuration.

    Uses JSON mode if use_tool_calling is False, otherwise regular mode for tool calling.

    Args:
        configurable: Configuration object containing LLM settings

    Returns:
        Configured LLM instance
    """
    if configurable.llm_provider == "lmstudio":
        if configurable.use_tool_calling:
            return ChatLMStudio(
                base_url=configurable.lmstudio_base_url,
                model=configurable.local_llm,
                temperature=0,
            )
        else:
            return ChatLMStudio(
                base_url=configurable.lmstudio_base_url,
                model=configurable.local_llm,
                temperature=0,
                format="json",
            )
    else:  # Default to Ollama
        if configurable.use_tool_calling:
            return ChatOllama(
                base_url=configurable.ollama_base_url,
                model=configurable.local_llm,
                temperature=0,
            )
        else:
            return ChatOllama(
                base_url=configurable.ollama_base_url,
                model=configurable.local_llm,
                temperature=0,
                format="json",
            )


def get_report_llm(configurable: Configuration):
    """Plain (non-structured-output) LLM for prose generation: report synthesis
    and profile updates. Always regular mode - these don't need JSON/tool parsing."""
    if configurable.llm_provider == "lmstudio":
        return ChatLMStudio(
            base_url=configurable.lmstudio_base_url,
            model=configurable.local_llm,
            temperature=0,
        )
    return ChatOllama(
        base_url=configurable.ollama_base_url,
        model=configurable.local_llm,
        temperature=0,
    )


# Nodes
def load_profile(state: SummaryState, config: RunnableConfig):
    """LangGraph node that starts a research run.

    Does a cheap Ollama reachability check (so a down Ollama fails fast with a
    clear message instead of deep inside generate_query), computes this run's
    date and topic slug once (so the Sources archive folder, the report
    filename, and the profile's Session Log entry all agree), and reads (or
    bootstraps) the evolving profile note.

    Args:
        state: Current graph state containing the research topic
        config: Configuration for the runnable

    Returns:
        Dictionary with state update: run_date, topic_slug, profile_content
    """
    configurable = Configuration.from_runnable_config(config)

    if configurable.llm_provider == "ollama":
        try:
            httpx.get(f"{configurable.ollama_base_url.rstrip('/')}/api/version", timeout=3.0)
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Ollama isn't reachable at {configurable.ollama_base_url} - "
                "start it before running research."
            ) from e

    profile = vault.read_profile(configurable.vault_path, configurable.profile_note_path)
    if len(profile) > PROFILE_MAX_CHARS:
        # The note grows by one Session Log entry per run and is pasted into every prompt. Keep the top
        # (standing preferences and the newest log entries) and say that the rest was left out.
        profile = profile[:PROFILE_MAX_CHARS].rsplit("\n", 1)[0] + "\n\n[older profile entries omitted to fit the model's context]"
    return {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "topic_slug": vault.slugify(state.research_topic),
        "profile_content": profile,
    }


def retrieve_vault_context(state: SummaryState, config: RunnableConfig):
    """LangGraph node that retrieves relevant prior research notes from the vault.

    Args:
        state: Current graph state containing the research topic
        config: Configuration for the runnable, including vault settings

    Returns:
        Dictionary with state update, including vault_context (empty string if
        disabled, or if the vault has no research notes yet)
    """
    configurable = Configuration.from_runnable_config(config)
    if not configurable.enable_vault_context:
        return {"vault_context": ""}

    context = vault.retrieve_vault_context(
        vault_path=configurable.vault_path,
        research_subdir=configurable.research_subdir,
        embedding_model=configurable.embedding_model,
        topic=state.research_topic,
        top_k=configurable.vault_context_top_k,
        ollama_base_url=configurable.ollama_base_url,
    )
    return {"vault_context": context}


def plan_research(state: SummaryState, config: RunnableConfig):
    """LangGraph node that decides whether the topic names 2+ things to compare.

    Binds a single conduct_research tool and asks the model to call it once
    per distinct entity to compare (validated empirically: llama3.1:8b calls
    it exactly 3 times for a real 3-way comparison prompt, and exactly once
    for a plain single-topic prompt - not a habitual over-split). If disabled
    or the model doesn't call the tool, falls back to the single topic as-is.

    Args:
        state: Current graph state containing the research topic
        config: Configuration for the runnable

    Returns:
        Dictionary with state update: entity_topics (list of 1+ topic strings)
    """
    configurable = Configuration.from_runnable_config(config)
    if not configurable.enable_comparison_planning:
        return {"entity_topics": [state.research_topic]}

    @tool
    class ConductResearch(BaseModel):
        """Research one specific, standalone sub-topic."""

        research_topic: str = Field(
            description="A specific, standalone research topic - self-contained, "
            "no reference to other sub-topics"
        )

    if configurable.llm_provider == "lmstudio":
        tool_llm = ChatLMStudio(
            base_url=configurable.lmstudio_base_url, model=configurable.local_llm, temperature=0)
    else:
        tool_llm = ChatOllama(
            base_url=configurable.ollama_base_url, model=configurable.local_llm, temperature=0)
    llm = tool_llm.bind_tools([ConductResearch])

    result = llm.invoke(
        [
            SystemMessage(content=comparison_planning_instructions),
            HumanMessage(content=state.research_topic),
        ]
    )

    topics = [
        c["args"]["research_topic"]
        for c in result.tool_calls
        if c["args"].get("research_topic")
    ][: configurable.max_comparison_entities]

    return {"entity_topics": topics or [state.research_topic]}


def route_after_planning(
    state: SummaryState, config: RunnableConfig
) -> Literal["generate_query", "parallel_research"]:
    """LangGraph routing function: comparison branch if plan_research found 2+
    entities, otherwise today's existing single-topic path, unchanged."""
    return "parallel_research" if len(state.entity_topics) >= 2 else "generate_query"


def generate_query(state: SummaryState, config: RunnableConfig):
    """LangGraph node that generates a search query based on the research topic.

    Uses an LLM to create an optimized search query for web research based on
    the user's research topic, calibrated by prior vault research and the
    user's profile when available. Supports both LMStudio and Ollama as LLM providers.

    Args:
        state: Current graph state containing the research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated query
    """

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date, research_topic=state.research_topic
    )
    if state.vault_context:
        formatted_prompt += vault_context_block.format(vault_context=state.vault_context)
    if state.profile_content:
        formatted_prompt += profile_context_block.format(profile_content=state.profile_content)

    # Generate a query
    configurable = Configuration.from_runnable_config(config)

    @tool
    class Query(BaseModel):
        """
        This tool is used to generate a query for web search.
        """

        query: str = Field(description="The actual search query string")
        rationale: str = Field(
            description="Brief explanation of why this query is relevant"
        )

    messages = [
        SystemMessage(
            content=formatted_prompt + (
                tool_calling_query_instructions if configurable.use_tool_calling
                else json_mode_query_instructions
            )
        ),
        HumanMessage(content="Generate a query for web search:"),
    ]

    return generate_search_query_with_structured_output(
        configurable=configurable,
        messages=messages,
        tool_class=Query,
        fallback_query=f"Tell me more about {state.research_topic}",
        tool_query_field="query",
        json_query_field="query",
    )


def _fallback_sources_text(sources_gathered: list[str]) -> str:
    """Dedupe the "* title : url" bullet blocks from format_sources() into one
    flat list. Used only when source archiving is disabled, to preserve a
    basic citation list in the report."""
    seen: set[str] = set()
    lines = []
    for block in sources_gathered:
        for line in block.split("\n"):
            if line.strip() and line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def web_research(state: SummaryState, config: RunnableConfig):
    """LangGraph node that performs web research using the generated search query.

    Executes a web search using the configured search API (tavily, perplexity,
    duckduckgo, or searxng), archives each source's full content to the vault,
    and formats the results for further processing.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count,
        web_research_results, and archived_sources
    """

    # Configure
    configurable = Configuration.from_runnable_config(config)

    # Get the search API
    search_api = get_config_value(configurable.search_api)

    # Search the web
    if search_api == "tavily":
        search_results = tavily_search(
            state.search_query,
            fetch_full_page=configurable.fetch_full_page,
            max_results=1,
        )
    elif search_api == "perplexity":
        search_results = perplexity_search(
            state.search_query, state.research_loop_count
        )
    elif search_api == "duckduckgo":
        search_results = duckduckgo_search(
            state.search_query,
            max_results=3,
            fetch_full_page=configurable.fetch_full_page,
        )
    elif search_api == "searxng":
        search_results = searxng_search(
            state.search_query,
            max_results=3,
            fetch_full_page=configurable.fetch_full_page,
        )
    elif search_api == "local_docs":
        search_results = local_docs_search(
            state.search_query,
            docs_path=configurable.docs_path,
            embedding_model=configurable.embedding_model,
            top_k=configurable.docs_top_k,
            chunk_size=configurable.docs_chunk_size,
            ollama_base_url=configurable.ollama_base_url,
        )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    search_str = deduplicate_and_format_sources(
        search_results,
        max_tokens_per_source=MAX_TOKENS_PER_SOURCE,
        fetch_full_page=configurable.fetch_full_page,
    )

    archived_sources = []
    if configurable.archive_full_sources:
        archived_sources = vault.archive_sources(
            vault_path=configurable.vault_path,
            sources_subdir=configurable.sources_subdir,
            topic_slug=state.topic_slug,
            run_date=state.run_date,
            search_query=state.search_query,
            search_api=search_api,
            search_results=search_results,
        )

    return {
        "sources_gathered": [format_sources(search_results)],
        "research_loop_count": state.research_loop_count + 1,
        "web_research_results": [search_str],
        "archived_sources": archived_sources,
    }


def summarize_sources(state: SummaryState, config: RunnableConfig):
    """LangGraph node that summarizes web research results.

    Uses an LLM to create or update a running summary based on the newest web research
    results, integrating them with any existing summary, prior vault research, and
    the user's profile when available.

    Args:
        state: Current graph state containing research topic, running summary,
              and web research results
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including running_summary key containing the updated summary
    """

    # Existing summary
    existing_summary = state.running_summary

    # Most recent web research
    most_recent_web_research = state.web_research_results[-1]

    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
            f"<New Context> \n {most_recent_web_research} \n <New Context>"
            f"Update the Existing Summary with the New Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
        )
    else:
        human_message_content = (
            f"<Context> \n {most_recent_web_research} \n <Context>"
            f"Create a Summary using the Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
        )

    # Run the LLM
    configurable = Configuration.from_runnable_config(config)
    llm = get_report_llm(configurable)

    system_content = summarizer_instructions
    if state.vault_context:
        system_content += vault_context_block.format(vault_context=state.vault_context)
    if state.profile_content:
        system_content += profile_context_block.format(profile_content=state.profile_content)

    result = llm.invoke(
        [
            SystemMessage(content=system_content),
            HumanMessage(content=human_message_content),
        ]
    )

    # Strip thinking tokens if configured
    running_summary = result.content
    if configurable.strip_thinking_tokens:
        running_summary = strip_thinking_tokens(running_summary)

    return {"running_summary": running_summary}


def reflect_on_summary(state: SummaryState, config: RunnableConfig):
    """LangGraph node that identifies knowledge gaps and generates follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    a new search query to address those gaps. Uses structured output to extract
    the follow-up query in JSON format. The knowledge gap is accumulated in state
    for the final report's "Open Questions" section.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update: search_query, and knowledge_gaps if one was found
    """

    # Generate a query
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = reflection_instructions.format(
        research_topic=state.research_topic
    )

    @tool
    class FollowUpQuery(BaseModel):
        """
        This tool is used to generate a follow-up query to address a knowledge gap.
        """

        follow_up_query: str = Field(
            description="Write a specific question to address this gap"
        )
        knowledge_gap: str = Field(
            description="Describe what information is missing or needs clarification"
        )

    messages = [
        SystemMessage(
            content=formatted_prompt + (
                tool_calling_reflection_instructions if configurable.use_tool_calling
                else json_mode_reflection_instructions
            )
        ),
        HumanMessage(
            content=f"Reflect on our existing knowledge: \n === \n {state.running_summary}, \n === \n And now identify a knowledge gap and generate a follow-up web search query:"
        ),
    ]

    result = generate_search_query_with_structured_output(
        configurable=configurable,
        messages=messages,
        tool_class=FollowUpQuery,
        fallback_query=f"Tell me more about {state.research_topic}",
        tool_query_field="follow_up_query",
        json_query_field="follow_up_query",
        secondary_field="knowledge_gap",
    )

    output = {"search_query": result["search_query"]}
    if result.get("knowledge_gap"):
        output["knowledge_gaps"] = [result["knowledge_gap"]]
    return output


def _run_entity_pipeline(entity_topic: str, state: SummaryState, config: RunnableConfig) -> dict:
    """Plain sync helper: runs the existing single-topic node functions in a loop
    for one comparison entity, manually applying their returned update-dicts the
    way LangGraph's reducers would (list-extend for the Annotated accumulator
    fields, replace otherwise). Reuses generate_query/web_research/
    summarize_sources/reflect_on_summary verbatim, unmodified - this function
    only orchestrates them.

    Runs inside a worker thread (via asyncio.to_thread in parallel_research) so
    that N entities' llm.invoke()/search calls genuinely run concurrently -
    these node functions are synchronous, so calling them directly inside
    asyncio.gather without a thread would just serialize them.
    """
    configurable = Configuration.from_runnable_config(config)
    entity_state = SummaryState(
        research_topic=entity_topic,
        profile_content=state.profile_content,
        vault_context=state.vault_context,
        run_date=state.run_date,
        topic_slug=vault.slugify(entity_topic),
    )

    for key, value in generate_query(entity_state, config).items():
        setattr(entity_state, key, value)

    while True:
        for key, value in web_research(entity_state, config).items():
            if key in ("archived_sources", "sources_gathered", "web_research_results"):
                getattr(entity_state, key).extend(value)
            else:
                setattr(entity_state, key, value)

        for key, value in summarize_sources(entity_state, config).items():
            setattr(entity_state, key, value)

        for key, value in reflect_on_summary(entity_state, config).items():
            if key == "knowledge_gaps":
                entity_state.knowledge_gaps.extend(value)
            else:
                setattr(entity_state, key, value)

        if entity_state.research_loop_count > configurable.max_web_research_loops:
            break

    return {
        "topic": entity_topic,
        "summary": entity_state.running_summary,
        "archived_sources": entity_state.archived_sources,
        "knowledge_gaps": entity_state.knowledge_gaps,
        "loops": entity_state.research_loop_count,
    }


async def parallel_research(state: SummaryState, config: RunnableConfig):
    """LangGraph node that researches every comparison entity concurrently.

    Each entity gets its own full copy of the single-topic research loop,
    run in its own worker thread via asyncio.to_thread, so N entities'
    research genuinely overlaps in wall-clock time instead of running
    sequentially.

    Args:
        state: Current graph state containing entity_topics from plan_research
        config: Configuration for the runnable

    Returns:
        Dictionary with state update: entity_research (per-entity results),
        merged archived_sources/knowledge_gaps, and research_loop_count set
        to the deepest entity's loop count (informational only)
    """
    results = await asyncio.gather(
        *[
            asyncio.to_thread(_run_entity_pipeline, topic, state, config)
            for topic in state.entity_topics
        ]
    )
    return {
        "entity_research": results,
        "archived_sources": [s for r in results for s in r["archived_sources"]],
        "knowledge_gaps": [g for r in results for g in r["knowledge_gaps"]],
        "research_loop_count": max((r["loops"] for r in results), default=0),
    }


def _synthesis_text(state: SummaryState) -> str:
    """Text to synthesize the report from: the comparison entities'
    joined summaries if this was a comparison run, else the normal single-topic
    running summary."""
    if state.entity_research:
        return "\n\n".join(f"### {r['topic']}\n{r['summary']}" for r in state.entity_research)
    return state.running_summary


def finalize_summary(state: SummaryState, config: RunnableConfig):
    """LangGraph node that finalizes the research report.

    Calls the LLM once more to synthesize the running summary and accumulated
    knowledge gaps into a structured report (Key Findings / Open Questions),
    then deterministically assembles a Sources section from the archived
    sources and writes the whole thing as a markdown note into the Obsidian
    vault's Research folder.

    Args:
        state: Current graph state containing the running summary, knowledge
              gaps, and archived sources

    Returns:
        Dictionary with state update: running_summary (now the structured
        report body) and report_path (the file written to the vault)
    """
    configurable = Configuration.from_runnable_config(config)

    knowledge_gaps_text = (
        "\n".join(f"- {gap}" for gap in state.knowledge_gaps)
        if state.knowledge_gaps
        else "None identified."
    )

    if state.entity_research:
        formatted_prompt = comparison_report_synthesis_instructions.format(
            research_topic=state.research_topic,
            entity_summaries=_synthesis_text(state),
            knowledge_gaps=knowledge_gaps_text,
        )
    else:
        formatted_prompt = report_synthesis_instructions.format(
            research_topic=state.research_topic,
            running_summary=state.running_summary,
            knowledge_gaps=knowledge_gaps_text,
        )

    llm = get_report_llm(configurable)
    result = llm.invoke(
        [
            SystemMessage(content=formatted_prompt),
            HumanMessage(content="Write the report body now."),
        ]
    )
    report_body = result.content
    if configurable.strip_thinking_tokens:
        report_body = strip_thinking_tokens(report_body)

    fallback_sources_text = (
        None if state.archived_sources else _fallback_sources_text(state.sources_gathered)
    )

    report_path = vault.write_report(
        vault_path=configurable.vault_path,
        research_subdir=configurable.research_subdir,
        sources_subdir=configurable.sources_subdir,
        run_date=state.run_date,
        topic_slug=state.topic_slug,
        research_topic=state.research_topic,
        report_body=report_body,
        archived_sources=state.archived_sources,
        loops=state.research_loop_count,
        fallback_sources_text=fallback_sources_text,
    )

    return {"running_summary": report_body, "report_path": report_path}


def update_profile(state: SummaryState, config: RunnableConfig):
    """LangGraph node that appends a session-log entry to the evolving profile note.

    Additive only: asks the LLM for a short dated entry summarizing what this
    session reveals about the user's interests, and appends it under the
    profile's "## Session Log" heading. Never touches "## Standing
    Preferences", which stays human-owned.

    Args:
        state: Current graph state containing the profile, topic, and final report
        config: Configuration for the runnable

    Returns:
        Empty dict - this node's effect is the vault write, not graph state
    """
    configurable = Configuration.from_runnable_config(config)
    if not configurable.enable_profile_update:
        return {}

    formatted_prompt = profile_update_instructions.format(
        profile_content=state.profile_content,
        research_topic=state.research_topic,
        running_summary=state.running_summary,
    )

    llm = get_report_llm(configurable)
    result = llm.invoke(
        [
            SystemMessage(content=formatted_prompt),
            HumanMessage(content="Write the session log entry now."),
        ]
    )
    bullets = result.content
    if configurable.strip_thinking_tokens:
        bullets = strip_thinking_tokens(bullets)

    vault.append_profile_session(
        vault_path=configurable.vault_path,
        profile_note_path=configurable.profile_note_path,
        run_date=state.run_date,
        research_topic=state.research_topic,
        session_bullets=bullets,
    )
    return {}


def notify_complete(state: SummaryState, config: RunnableConfig):
    """LangGraph node that fires a native OS notification when the run finishes.

    A notification failure never fails the run - see notifications.py.

    Args:
        state: Current graph state containing the topic and report path
        config: Configuration for the runnable

    Returns:
        Empty dict - this node's effect is the OS notification, not graph state
    """
    configurable = Configuration.from_runnable_config(config)
    if configurable.notify_on_complete:
        notify_run_complete(state.research_topic, state.report_path)
    return {}


def route_research(
    state: SummaryState, config: RunnableConfig
) -> Literal["finalize_summary", "web_research"]:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to move on to finalizing the summary, based on the configured maximum number of
    research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_web_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """

    configurable = Configuration.from_runnable_config(config)
    # research_loop_count is the number of search passes done so far, so "< max" means max passes in total
    # (the inherited "<=" ran one pass more than the dashboard's "Max research loops" said).
    if state.research_loop_count < configurable.max_web_research_loops:
        return "web_research"
    else:
        return "finalize_summary"


# Add nodes and edges
builder = StateGraph(
    SummaryState,
    input_schema=SummaryStateInput,
    output_schema=SummaryStateOutput,
    config_schema=Configuration,
)
builder.add_node("load_profile", load_profile)
builder.add_node("retrieve_vault_context", retrieve_vault_context)
builder.add_node("plan_research", plan_research)
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("summarize_sources", summarize_sources)
builder.add_node("reflect_on_summary", reflect_on_summary)
builder.add_node("parallel_research", parallel_research)
builder.add_node("finalize_summary", finalize_summary)
builder.add_node("update_profile", update_profile)
builder.add_node("notify_complete", notify_complete)

# Add edges
builder.add_edge(START, "load_profile")
builder.add_edge("load_profile", "retrieve_vault_context")
builder.add_edge("retrieve_vault_context", "plan_research")
builder.add_conditional_edges("plan_research", route_after_planning)
builder.add_edge("generate_query", "web_research")
builder.add_edge("web_research", "summarize_sources")
builder.add_edge("summarize_sources", "reflect_on_summary")
builder.add_conditional_edges("reflect_on_summary", route_research)
builder.add_edge("parallel_research", "finalize_summary")
builder.add_edge("finalize_summary", "update_profile")
builder.add_edge("update_profile", "notify_complete")
builder.add_edge("notify_complete", END)

graph = builder.compile()
