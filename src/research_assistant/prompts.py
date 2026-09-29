from datetime import datetime


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


query_writer_instructions = """Your goal is to generate a targeted web search query.

<CONTEXT>
Current date: {current_date}
Please ensure your queries account for the most current information available as of this date.
</CONTEXT>

<TOPIC>
{research_topic}
</TOPIC>

<EXAMPLE>
Example output:
{{
    "query": "machine learning transformer architecture explained",
    "rationale": "Understanding the fundamental structure of transformer models"
}}
</EXAMPLE>"""

json_mode_query_instructions = """<FORMAT>
Format your response as a JSON object with ALL three of these exact keys:
- "query": The actual search query string
- "rationale": Brief explanation of why this query is relevant
</FORMAT>

Provide your response in JSON format:"""

tool_calling_query_instructions = """<INSTRUCTIONS   >
Call the Query tool to format your response with the following keys:
   - "query": The actual search query string
   - "rationale": Brief explanation of why this query is relevant
</INSTRUCTIONS>

Call the Query Tool to generate a query for this request:"""

summarizer_instructions = """
<GOAL>
Generate a high-quality summary of the provided context.
</GOAL>

<REQUIREMENTS>
When creating a NEW summary:
1. Highlight the most relevant information related to the user topic from the search results
2. Ensure a coherent flow of information

When EXTENDING an existing summary:                                                                                                                 
1. Read the existing summary and new search results carefully.                                                    
2. Compare the new information with the existing summary.                                                         
3. For each piece of new information:                                                                             
    a. If it's related to existing points, integrate it into the relevant paragraph.                               
    b. If it's entirely new but relevant, add a new paragraph with a smooth transition.                            
    c. If it's not relevant to the user topic, skip it.                                                            
4. Ensure all additions are relevant to the user's topic.                                                         
5. Verify that your final output differs from the input summary.                                                                                                                                                            
< /REQUIREMENTS >

< FORMATTING >
- Start directly with the updated summary, without preamble or titles. Do not use XML tags in the output.  
< /FORMATTING >

<Task>
Think carefully about the provided Context first. Then generate a summary of the context to address the User Input.
</Task>
"""

reflection_instructions = """You are an expert research assistant analyzing a summary about {research_topic}.

<GOAL>
1. Identify knowledge gaps or areas that need deeper exploration
2. Generate a follow-up question that would help expand your understanding
3. Focus on technical details, implementation specifics, or emerging trends that weren't fully covered
</GOAL>

<REQUIREMENTS>
Ensure the follow-up question is self-contained and includes necessary context for web search.
</REQUIREMENTS>"""

json_mode_reflection_instructions = """<FORMAT>
Format your response as a JSON object with these exact keys:
- knowledge_gap: Describe what information is missing or needs clarification
- follow_up_query: Write a specific question to address this gap
</FORMAT>

<Task>
Reflect carefully on the Summary to identify knowledge gaps and produce a follow-up query. Then, produce your output following this JSON format:
{{
    "knowledge_gap": "The summary lacks information about performance metrics and benchmarks",
    "follow_up_query": "What are typical performance benchmarks and metrics used to evaluate [specific technology]?"
}}
</Task>

Provide your analysis in JSON format:"""

tool_calling_reflection_instructions = """<INSTRUCTIONS>
Call the FollowUpQuery tool to format your response with the following keys:
- follow_up_query: Write a specific question to address this gap
- knowledge_gap: Describe what information is missing or needs clarification
</INSTRUCTIONS>

<Task>
Reflect carefully on the Summary to identify knowledge gaps and produce a follow-up query.
</Task>

Call the FollowUpQuery Tool to generate a reflection for this request:"""


# --- Personal research assistant additions ---

vault_context_block = """
<PRIOR_RESEARCH>
{vault_context}

Avoid re-researching what is already thoroughly covered here; if relevant, favor an
angle that builds on or extends this prior work rather than duplicating it.
</PRIOR_RESEARCH>
"""

profile_context_block = """
<USER_PROFILE>
{profile_content}

Calibrate technical depth and terminology to this profile - assume familiarity with
concepts already noted there, and briefly define genuinely new jargon.
</USER_PROFILE>
"""

report_synthesis_instructions = """You are producing a final structured research report on: {research_topic}

<INPUT>
Running summary of findings:
{running_summary}

Knowledge gaps identified during research (not fully resolved):
{knowledge_gaps}
</INPUT>

<TASK>
Write the report body in markdown with exactly these sections, in this order:

## Key Findings
Organize findings into 2-5 thematic subheadings (###) based on what naturally emerged
from the research. Do not force a fixed number of subheadings if the material doesn't
support it.

## Open Questions
For each knowledge gap above, write a "###" subheading restating it clearly as a
question, followed by a line starting with "**Current best guess:**" giving a
tentative 1-2 sentence answer from your own general knowledge. Explicitly signal
it's unverified (e.g. "likely", "probably", "worth confirming") - never present it
as settled fact. If no gaps were identified, write "None identified this session."
</TASK>

<FORMATTING>
Do not include a Sources section - it is appended separately. Do not repeat the topic
as a title. Start directly with "## Key Findings".
</FORMATTING>"""

profile_update_instructions = """You are maintaining a running profile note about a single user's research
interests, based on their sessions over time.

<EXISTING_PROFILE>
{profile_content}
</EXISTING_PROFILE>

<THIS_SESSION>
Topic: {research_topic}
Summary: {running_summary}
</THIS_SESSION>

<TASK>
Write ONLY a new dated entry as 3-5 bullet points covering: what this session reveals
about the user's current interests/depth, any new jargon they're now likely familiar
with, and natural follow-up areas suggested by this research.
</TASK>

<FORMATTING>
Do NOT rewrite, summarize, or restate the existing profile. Do NOT produce anything
resembling a "Standing Preferences" section - that is manually maintained by the user.
Output ONLY the new bullet list (markdown "- " bullets), no heading, no preamble.
</FORMATTING>"""

debate_advocate_instructions = """You are an advocate for this research summary on: {research_topic}

<SUMMARY>
{running_summary}
</SUMMARY>

<TASK>
Argue for why these findings are solid and well-supported. Highlight the strongest,
most confidently-backed points. Be specific - reference what's actually in the summary,
not generic praise. 3-5 sentences.
</TASK>"""

debate_critic_instructions = """You are a skeptical critic reviewing this research summary on: {research_topic}

<SUMMARY>
{running_summary}
</SUMMARY>

<TASK>
Argue for what might be incomplete, overstated, missing important nuance, or contested.
Be specific - reference what's actually in the summary, not generic skepticism. 3-5 sentences.
</TASK>"""

comparison_planning_instructions = """You are a research supervisor. Decide whether the user's research
request names 2 or more distinct things that should be researched independently and compared,
or whether it's a single topic.

<SCALING RULES>
- If the request is a comparison (e.g. "X vs Y vs Z", "compare A and B", "which is better, ... or ..."),
  call the conduct_research tool once per distinct thing being compared, in this same turn. Each call's
  research_topic must be specific, standalone, and self-contained - the sub-agent researching it won't
  see the other calls, so don't write anything like "the other option" or "compared to X."
- If the request is about a SINGLE topic with no explicit comparison, call conduct_research exactly ONCE
  with the topic as-is. Do not invent a comparison that isn't there - most requests are not comparisons.
- Delegate clear, distinct, non-overlapping subtopics only.
</SCALING RULES>

Call the conduct_research tool now, following these rules."""

comparison_report_synthesis_instructions = """You are producing a final structured comparison report on: {research_topic}

<INPUT>
Independently-researched findings for each thing being compared:
{entity_summaries}

Knowledge gaps identified during research (not fully resolved):
{knowledge_gaps}
</INPUT>

<TASK>
Write the report body in markdown with exactly these sections, in this order:

One "##" section per thing compared, using its name as the heading, presenting that
entity's key findings (organize into "###" thematic subheadings if useful).

## Comparison
Explicitly contrast the entities against each other - where they agree, where they
diverge, and what that implies for someone choosing between them.

## Open Questions
For each knowledge gap above, write a "###" subheading restating it clearly as a
question, followed by a line starting with "**Current best guess:**" giving a
tentative 1-2 sentence answer from your own general knowledge. Explicitly signal
it's unverified (e.g. "likely", "probably", "worth confirming") - never present it
as settled fact. If no gaps were identified, write "None identified this session."
</TASK>

<FORMATTING>
Do not include a Sources section - it is appended separately. Do not repeat the topic
as a title. Start directly with the first entity's "##" heading.
</FORMATTING>"""