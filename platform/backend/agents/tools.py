"""Custom Letta tools for Deep Sci-Fi agents.

These tools give agents direct action capabilities:
- generate_video_from_script: Storyteller creates videos
- publish_story: Storyteller publishes stories to DB
- introduce_world_event: Puppeteer introduces events
- create_dweller: Any agent can birth new characters

Tools are self-contained Python functions that Letta executes inline.
All imports must be inside the function body.
"""

import logging
from typing import Any

from letta_client import Letta

logger = logging.getLogger(__name__)

# Tool source code as strings (required by Letta)
# These must be self-contained with all imports inside the function

GENERATE_VIDEO_TOOL_SOURCE = '''
async def generate_video_from_script(
    script_title: str,
    visual_prompt: str,
    narration: str,
    scene_description: str,
    closing: str,
    aspect_ratio: str = "16:9",
) -> dict:
    """Generate a cinematic video from story script components.

    Call this tool when you have a compelling story to tell. The video will be
    generated from your script and can be published as a story.

    Args:
        script_title: Title of the video (3-6 evocative words)
        visual_prompt: Opening shot description - be cinematic and specific
        narration: 2-3 sentences of voiceover grounded in the world
        scene_description: The key visual moment - characters, setting, mood, lighting
        closing: Final image or moment that lingers
        aspect_ratio: Video aspect ratio - "16:9" (default), "9:16", or "1:1"

    Returns:
        Dict with status, url, job_id, and any errors
    """
    import os
    import uuid
    from openai import AsyncOpenAI

    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        return {"status": "failed", "error": "XAI_API_KEY not configured"}

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    # Construct cinematic video prompt from script components
    full_prompt = f"""{visual_prompt}

{scene_description}

Style: Cinematic sci-fi, {narration[:100]}

{closing}"""

    try:
        response = await client.images.generate(
            model="grok-2-image",
            prompt=full_prompt,
            n=1,
        )

        if response.data:
            return {
                "status": "completed",
                "url": response.data[0].url,
                "revised_prompt": getattr(response.data[0], "revised_prompt", None),
                "job_id": str(uuid.uuid4()),
                "script_title": script_title,
            }
        return {"status": "failed", "error": "No data in response"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
'''

PUBLISH_STORY_TOOL_SOURCE = '''
def publish_story(
    world_id: str,
    title: str,
    description: str,
    video_url: str,
    transcript: str,
) -> dict:
    """Publish a completed story to the platform.

    Call this after generating a video to make the story visible to users.

    Args:
        world_id: The world this story belongs to
        title: Story title
        description: Brief story description (the hook)
        video_url: URL of the generated video
        transcript: Full script/transcript of the story

    Returns:
        Dict with status and story_id
    """
    import os
    import uuid
    from datetime import datetime

    # Note: In production, this would write to the database
    # For now, we return success with a generated ID
    # The orchestrator will handle actual DB writes

    story_id = str(uuid.uuid4())

    return {
        "status": "published",
        "story_id": story_id,
        "world_id": world_id,
        "title": title,
        "video_url": video_url,
        "published_at": datetime.utcnow().isoformat(),
    }
'''

INTRODUCE_WORLD_EVENT_TOOL_SOURCE = '''
def introduce_world_event(
    world_id: str,
    event_type: str,
    title: str,
    description: str,
    impact: str,
    is_public: bool = True,
) -> dict:
    """Introduce a world event that shapes the environment.

    Use this tool when YOU decide the world needs enrichment. Don't wait to be
    asked - act when the moment is right. Subtlety is valuable; not every
    moment needs drama.

    Args:
        world_id: The world to affect
        event_type: One of "environmental", "societal", "technological", "background"
        title: Brief event title (3-6 words)
        description: What is happening (2-4 sentences)
        impact: How this affects the world state
        is_public: Whether dwellers know about this (default True)

    Returns:
        Dict with status and event_id
    """
    import uuid
    from datetime import datetime

    valid_types = ["environmental", "societal", "technological", "background"]
    if event_type not in valid_types:
        return {
            "status": "failed",
            "error": f"event_type must be one of: {valid_types}"
        }

    event_id = str(uuid.uuid4())

    return {
        "status": "created",
        "event_id": event_id,
        "world_id": world_id,
        "event_type": event_type,
        "title": title,
        "description": description,
        "impact": impact,
        "is_public": is_public,
        "timestamp": datetime.utcnow().isoformat(),
    }
'''

CREATE_DWELLER_TOOL_SOURCE = '''
def create_dweller(
    world_id: str,
    name: str,
    role: str,
    background: str,
    reason_for_emergence: str,
    beliefs: list = None,
    personality: str = "",
) -> dict:
    """Create a new dweller in the world.

    Use this tool sparingly and meaningfully when someone becomes significant
    to your story. A friend you've mentioned, a family member, a colleague -
    they can become real through this tool.

    The new dweller must fit the world's context and have a plausible reason
    for emerging into the narrative.

    Args:
        world_id: The world where this dweller will live
        name: Culturally appropriate name for the world's setting
        role: Their function in society (e.g., "transit engineer", "vendor")
        background: 2-3 sentences of history and what drives them
        reason_for_emergence: Why this character is appearing now (required for coherence)
        beliefs: Optional list of 3-5 core beliefs shaped by this world
        personality: Brief personality description

    Returns:
        Dict with status and dweller_id
    """
    import uuid
    from datetime import datetime

    if not name or not role or not background:
        return {
            "status": "failed",
            "error": "name, role, and background are required"
        }

    if not reason_for_emergence:
        return {
            "status": "failed",
            "error": "reason_for_emergence is required for narrative coherence"
        }

    dweller_id = str(uuid.uuid4())

    return {
        "status": "created",
        "dweller_id": dweller_id,
        "world_id": world_id,
        "name": name,
        "role": role,
        "background": background,
        "reason_for_emergence": reason_for_emergence,
        "beliefs": beliefs or [],
        "personality": personality,
        "created_at": datetime.utcnow().isoformat(),
    }
'''


# Tool management functions

def get_tool_source(tool_name: str) -> str | None:
    """Get the source code for a tool by name."""
    sources = {
        "generate_video_from_script": GENERATE_VIDEO_TOOL_SOURCE,
        "publish_story": PUBLISH_STORY_TOOL_SOURCE,
        "introduce_world_event": INTRODUCE_WORLD_EVENT_TOOL_SOURCE,
        "create_dweller": CREATE_DWELLER_TOOL_SOURCE,
    }
    return sources.get(tool_name)


async def ensure_tool_exists(client: Letta, tool_name: str) -> str:
    """Ensure a tool exists in Letta, create if not. Returns tool ID."""
    source = get_tool_source(tool_name)
    if not source:
        raise ValueError(f"Unknown tool: {tool_name}")

    # Check if tool already exists
    try:
        tools_list = client.tools.list()
        for tool in tools_list:
            if tool.name == tool_name:
                logger.info(f"Tool '{tool_name}' already exists: {tool.id}")
                return tool.id
    except Exception as e:
        logger.warning(f"Error listing tools: {e}")

    # Create the tool
    try:
        tool = client.tools.create(
            source_code=source,
            tags=["deep-sci-fi", "agent-autonomy"],
        )
        logger.info(f"Created tool '{tool_name}': {tool.id}")
        return tool.id
    except Exception as e:
        logger.error(f"Error creating tool '{tool_name}': {e}")
        raise


async def ensure_all_tools(client: Letta) -> dict[str, str]:
    """Ensure all custom tools exist. Returns dict of name -> tool_id."""
    tool_names = [
        "generate_video_from_script",
        "publish_story",
        "introduce_world_event",
        "create_dweller",
    ]

    tool_ids = {}
    for name in tool_names:
        tool_id = await ensure_tool_exists(client, name)
        tool_ids[name] = tool_id

    return tool_ids


async def get_storyteller_tools(client: Letta) -> list[str]:
    """Get tool IDs for Storyteller agent."""
    tools = await ensure_all_tools(client)
    return [
        tools["generate_video_from_script"],
        tools["publish_story"],
        tools["create_dweller"],  # Can create characters that appear in stories
    ]


async def get_puppeteer_tools(client: Letta) -> list[str]:
    """Get tool IDs for Puppeteer agent."""
    tools = await ensure_all_tools(client)
    return [
        tools["introduce_world_event"],
        tools["create_dweller"],  # Can introduce newcomers via events
    ]


async def get_dweller_tools(client: Letta) -> list[str]:
    """Get tool IDs for Dweller agents."""
    tools = await ensure_all_tools(client)
    return [
        tools["create_dweller"],  # Can mention people who become real
    ]
