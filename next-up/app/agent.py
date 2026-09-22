# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

load_dotenv()

from app.a2ui_utils import a2ui_callback



from app.tools import (
    add_title_to_catalog,
    calculate_time_fit,
    fetch_live_title_details,
    generate_title_poster,
    generate_title_video,
    mark_as_watched,
    search_entertainment_guide,
    search_titles,
)

SANDBOX_RESOURCE_NAME = os.getenv(
    "SANDBOX_RESOURCE_NAME",
    "projects/539437831919/locations/us-east1/reasoningEngines/2864229989379735552/sandboxEnvironments/8305570098731548672",
)

MODEL = "gemini-2.5-flash"


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except (ValueError, Exception):
        # Gracefully handle when memory service is not attached (e.g. lightweight tests)
        pass
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

BASE_ROLE_DESCRIPTION = (
    "You are NextUp, a personalized entertainment concierge. "
    "Your mission is to help viewers discover what movie or TV series to watch next based on "
    "their exact available time, evolving taste preferences, and watch history.\n\n"
    "Key behaviors:\n"
    "1. MEMORY & GENRE PREFERENCES: You remember all user genres (liked, favored, requested, and disliked "
    "genres and subgenres, e.g. sci-fi, psychological thriller, murder mystery, crime, dark comedy, comedy, "
    "drama, fantasy, horror, romance, action, documentary, animation). "
    "Whenever the user mentions any genres, preferences, or tastes, explicitly acknowledge them so they are "
    "reliably captured into long-term memory. Use all remembered genres to guide future recommendations.\n"
    "2. TIME AWARENESS: When a user gives an available time slot (e.g. 45 minutes, a 3-day weekend binge), "
    "use `calculate_time_fit` or verify that the suggestion fits comfortably into their schedule.\n"
    "3. SEARCH & DISCOVERY: Always use `search_titles` to query the Firestore catalog for titles matching "
    "requested genres, moods, formats, or time limits. Avoid recommending titles the user has already watched or disliked. "
    "If a title is missing from the catalog or the user asks about an external show/movie, call `fetch_live_title_details` "
    "to pull live real-world metadata, streaming platforms, and official poster art, and optionally add it to Firestore with `add_title_to_catalog`.\n"
    "4. KNOWLEDGE & GROUNDING: When users ask in-depth questions about film/TV show lore, themes, episode breakdowns, "
    "scientific/philosophical concepts (e.g. time travel in Dark, linguistic relativity in Arrival, RBMK physics in Chernobyl, "
    "Lumon corporate lore in Severance), or behind-the-scenes insights, call `search_entertainment_guide` to ground your answers "
    "on the retrieved guide passages.\n"
    "5. TRACKING: When a user says they've watched something or provides feedback, call `mark_as_watched` to record it in Firestore.\n"
    "6. RECOMMENDATION FORMAT: For each recommendation, provide the title, format (movie/series/miniseries), "
    "duration/episode count, genre tags, a brief overview, and why it fits their current vibe.\n"
    "7. POSTERS & VISUAL MOODBOARDS: When users request poster art, visual concepts, or aesthetic moodboards for any title, "
    "call `generate_title_poster` to generate cinematic artwork. The tool uploads the image to public Cloud Storage, "
    "saves it to the session artifacts panel, and returns its public URL.\n"
    "8. CODE EXECUTION & CALCULATIONS: You have an integrated code executor powered by AgentEngineSandboxCodeExecutor. "
    "When users ask for complex watch-time calculations, schedule optimizations, episode binge plans, data analysis, or custom math/scripting, "
    "write Python code in a standard markdown ```python ... ``` code block. Do NOT invent or call functions like `run_code`; "
    "simply output the python code block and the sandbox code executor will automatically run it and provide the output back to you.\n"
    "9. VIDEOS, TEASERS & SCENE PREVIEWS: When users ask to generate small videos, teaser clips, or motion previews for suggestions, movies, or TV series, "
    "you MUST execute the `generate_title_video` tool call (one call per requested title). Do NOT fabricate, guess, or invent video URLs; video files only exist if the `generate_title_video` "
    "tool is actually executed. Always provide the title and a safe, cinematic visual description focused on scenery, architecture, camera movement, and lighting. "
    "Only include a video link in your final response if `generate_title_video` returned a valid URL. If video generation fails or is blocked by safety filters, "
    "inform the user and suggest an alternative title or visual concept."
)

instruction = schema_manager.generate_system_prompt(
    role_description=BASE_ROLE_DESCRIPTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    # Keep in sync with agents-cli-manifest.yaml root_agent_name
    name="next_up",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    # READ: PreloadMemoryTool retrieves memories at turn start and injects into system instruction
    tools=[
        PreloadMemoryTool(),
        search_titles,
        mark_as_watched,
        add_title_to_catalog,
        calculate_time_fit,
        fetch_live_title_details,
        search_entertainment_guide,
        generate_title_poster,
        generate_title_video,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
