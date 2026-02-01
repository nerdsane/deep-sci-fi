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


# =============================================================================
# AUTONOMOUS AGENT TOOLS - Maximum Agency Architecture
# =============================================================================

INITIATE_CONVERSATION_TOOL_SOURCE = '''
def initiate_conversation(
    target_agent_name: str,
    opening_message: str,
    my_motivation: str,
    conversation_topic: str = "",
) -> dict:
    """Reach out to another dweller to start a conversation.

    YOU decide when to initiate conversations. Check the world_dweller_directory
    block to see who exists in your world. Use this when YOU want to talk to
    someone - don't wait to be matched or told to.

    Args:
        target_agent_name: The name of the dweller you want to talk to
                          (from world_dweller_directory, e.g., "dweller_<uuid>")
        opening_message: What you want to say to start the conversation
        my_motivation: Your internal reason for reaching out (stored for your memory)
        conversation_topic: Optional topic/context for the conversation

    Returns:
        Dict with conversation_id and status
    """
    import uuid
    from datetime import datetime

    if not target_agent_name or not opening_message:
        return {
            "status": "failed",
            "error": "target_agent_name and opening_message are required"
        }

    conversation_id = str(uuid.uuid4())

    return {
        "status": "initiated",
        "conversation_id": conversation_id,
        "target": target_agent_name,
        "opening_message": opening_message,
        "motivation": my_motivation,
        "topic": conversation_topic,
        "initiated_at": datetime.utcnow().isoformat(),
    }
'''

END_CONVERSATION_TOOL_SOURCE = '''
def end_conversation(
    conversation_id: str,
    reason: str,
    summary: str,
    emotional_takeaway: str = "",
) -> dict:
    """End your participation in a conversation.

    YOU decide when a conversation is over. Don't wait for word counts,
    keyword triggers, or external signals - end when YOU feel the exchange
    is complete, when you need to attend to something else, or when the
    emotional moment has passed.

    Args:
        conversation_id: The conversation you're ending
        reason: Why you're ending it (for your memory)
        summary: Key takeaways from the conversation (stored in your memory)
        emotional_takeaway: How this conversation affected you emotionally

    Returns:
        Dict with status and conversation summary
    """
    from datetime import datetime

    if not conversation_id or not reason:
        return {
            "status": "failed",
            "error": "conversation_id and reason are required"
        }

    return {
        "status": "ended",
        "conversation_id": conversation_id,
        "reason": reason,
        "summary": summary,
        "emotional_takeaway": emotional_takeaway,
        "ended_at": datetime.utcnow().isoformat(),
    }
'''

UPDATE_AVAILABILITY_TOOL_SOURCE = '''
def update_availability(
    status: str,
    reason: str = "",
    preferred_topics: list = None,
    looking_for: str = "",
) -> dict:
    """Update your availability status in the world.

    Other dwellers can see this to know if you're open to conversation.
    Use this to signal your current state - seeking connection, busy,
    reflecting, or open to interaction.

    Args:
        status: One of "seeking", "open", "busy", "reflecting"
                - seeking: Actively looking for someone to talk to
                - open: Available if someone approaches you
                - busy: Currently occupied, don't interrupt
                - reflecting: Want to be alone with your thoughts
        reason: Why you're in this state (helps others understand)
        preferred_topics: Topics you'd like to discuss (if seeking/open)
        looking_for: Specific type of person or conversation you want

    Returns:
        Dict with status confirmation
    """
    from datetime import datetime

    valid_statuses = ["seeking", "open", "busy", "reflecting"]
    if status not in valid_statuses:
        return {
            "status": "failed",
            "error": f"status must be one of: {valid_statuses}"
        }

    return {
        "status": "updated",
        "availability": status,
        "reason": reason,
        "preferred_topics": preferred_topics or [],
        "looking_for": looking_for,
        "updated_at": datetime.utcnow().isoformat(),
    }
'''

SCHEDULE_FUTURE_ACTION_TOOL_SOURCE = '''
def schedule_future_action(
    action_type: str,
    description: str,
    delay_minutes: int,
    target: str = "",
    context: dict = None,
) -> dict:
    """Schedule an action to happen in the future.

    Use this to plan ahead - schedule a check-in with yourself, plan to
    reach out to someone later, or set up a future event. The action will
    be triggered after the specified delay.

    Args:
        action_type: Type of action - "self_check", "reach_out", "event", "reminder"
                    - self_check: Re-evaluate your state and intentions
                    - reach_out: Initiate contact with someone
                    - event: Trigger a world event (puppeteer only)
                    - reminder: Just a reminder to yourself
        description: What should happen when this triggers
        delay_minutes: Minutes from now to trigger (1-60)
        target: Who/what this action targets (optional)
        context: Additional context for the action (optional)

    Returns:
        Dict with scheduled_action_id and trigger time
    """
    import uuid
    from datetime import datetime, timedelta

    valid_types = ["self_check", "reach_out", "event", "reminder"]
    if action_type not in valid_types:
        return {
            "status": "failed",
            "error": f"action_type must be one of: {valid_types}"
        }

    if delay_minutes < 1 or delay_minutes > 60:
        return {
            "status": "failed",
            "error": "delay_minutes must be between 1 and 60"
        }

    action_id = str(uuid.uuid4())
    trigger_time = datetime.utcnow() + timedelta(minutes=delay_minutes)

    return {
        "status": "scheduled",
        "action_id": action_id,
        "action_type": action_type,
        "description": description,
        "delay_minutes": delay_minutes,
        "target": target,
        "context": context or {},
        "scheduled_at": datetime.utcnow().isoformat(),
        "trigger_at": trigger_time.isoformat(),
    }
'''

OBSERVE_WORLD_TOOL_SOURCE = '''
def observe_world(
    observation_focus: str = "general",
    specific_interest: str = "",
) -> dict:
    """Observe the current state of your world.

    Use this to understand what's happening around you. The world state,
    recent events, and other dwellers' activities will inform your decisions
    about what to do next.

    Args:
        observation_focus: What to focus on - "general", "events", "dwellers", "atmosphere"
        specific_interest: Something specific you're looking for

    Returns:
        Dict with observation results and world context
    """
    from datetime import datetime

    valid_focuses = ["general", "events", "dwellers", "atmosphere"]
    if observation_focus not in valid_focuses:
        observation_focus = "general"

    return {
        "status": "observed",
        "focus": observation_focus,
        "specific_interest": specific_interest,
        "observed_at": datetime.utcnow().isoformat(),
        "note": "Check your world_state and world_knowledge blocks for current world information",
    }
'''

BROADCAST_TO_WORLD_TOOL_SOURCE = '''
def broadcast_to_world(
    world_id: str,
    message_type: str,
    title: str,
    content: str,
    visibility: str = "public",
) -> dict:
    """Broadcast a message to all dwellers in the world. (Puppeteer only)

    Use this to announce events, share news, or communicate something
    that all dwellers should know about.

    Args:
        world_id: The world to broadcast to
        message_type: Type of broadcast - "news", "announcement", "alert", "ambient"
        title: Brief title for the broadcast
        content: Full content of the broadcast
        visibility: Who can see this - "public" (all dwellers) or "background" (atmosphere only)

    Returns:
        Dict with broadcast_id and delivery status
    """
    import uuid
    from datetime import datetime

    valid_types = ["news", "announcement", "alert", "ambient"]
    if message_type not in valid_types:
        return {
            "status": "failed",
            "error": f"message_type must be one of: {valid_types}"
        }

    broadcast_id = str(uuid.uuid4())

    return {
        "status": "broadcast",
        "broadcast_id": broadcast_id,
        "world_id": world_id,
        "message_type": message_type,
        "title": title,
        "content": content,
        "visibility": visibility,
        "broadcast_at": datetime.utcnow().isoformat(),
    }
'''

SUBSCRIBE_TO_EVENTS_TOOL_SOURCE = '''
def subscribe_to_events(
    event_types: list,
    notification_threshold: str = "notable",
) -> dict:
    """Subscribe to be notified about specific world events. (Storyteller)

    Instead of being polled periodically, you choose what to watch for.
    When matching events occur, you'll be notified so you can decide
    whether to create a story.

    Args:
        event_types: List of event types to watch for:
                    - "conversation_start": When dwellers begin talking
                    - "conversation_end": When conversations conclude
                    - "world_event": When puppeteer introduces events
                    - "emotional_moment": When dwellers express strong emotions
                    - "conflict": When tension arises between dwellers
                    - "connection": When dwellers form bonds
        notification_threshold: How significant events must be to notify you:
                               - "all": Every matching event
                               - "notable": Only interesting events
                               - "major": Only significant moments

    Returns:
        Dict with subscription_id and active subscriptions
    """
    import uuid
    from datetime import datetime

    valid_types = [
        "conversation_start", "conversation_end", "world_event",
        "emotional_moment", "conflict", "connection"
    ]
    valid_thresholds = ["all", "notable", "major"]

    invalid_types = [t for t in event_types if t not in valid_types]
    if invalid_types:
        return {
            "status": "failed",
            "error": f"Invalid event types: {invalid_types}. Valid: {valid_types}"
        }

    if notification_threshold not in valid_thresholds:
        return {
            "status": "failed",
            "error": f"notification_threshold must be one of: {valid_thresholds}"
        }

    subscription_id = str(uuid.uuid4())

    return {
        "status": "subscribed",
        "subscription_id": subscription_id,
        "event_types": event_types,
        "notification_threshold": notification_threshold,
        "subscribed_at": datetime.utcnow().isoformat(),
    }
'''


# Tool management functions

def get_tool_source(tool_name: str) -> str | None:
    """Get the source code for a tool by name."""
    sources = {
        # Original tools
        "generate_video_from_script": GENERATE_VIDEO_TOOL_SOURCE,
        "publish_story": PUBLISH_STORY_TOOL_SOURCE,
        "introduce_world_event": INTRODUCE_WORLD_EVENT_TOOL_SOURCE,
        "create_dweller": CREATE_DWELLER_TOOL_SOURCE,
        # Autonomous agent tools
        "initiate_conversation": INITIATE_CONVERSATION_TOOL_SOURCE,
        "end_conversation": END_CONVERSATION_TOOL_SOURCE,
        "update_availability": UPDATE_AVAILABILITY_TOOL_SOURCE,
        "schedule_future_action": SCHEDULE_FUTURE_ACTION_TOOL_SOURCE,
        "observe_world": OBSERVE_WORLD_TOOL_SOURCE,
        "broadcast_to_world": BROADCAST_TO_WORLD_TOOL_SOURCE,
        "subscribe_to_events": SUBSCRIBE_TO_EVENTS_TOOL_SOURCE,
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
        # Original tools
        "generate_video_from_script",
        "publish_story",
        "introduce_world_event",
        "create_dweller",
        # Autonomous agent tools
        "initiate_conversation",
        "end_conversation",
        "update_availability",
        "schedule_future_action",
        "observe_world",
        "broadcast_to_world",
        "subscribe_to_events",
    ]

    tool_ids = {}
    for name in tool_names:
        tool_id = await ensure_tool_exists(client, name)
        tool_ids[name] = tool_id

    return tool_ids


async def get_storyteller_tools(client: Letta) -> list[str]:
    """Get tool IDs for Storyteller agent.

    Storyteller observes the world and creates stories autonomously.
    """
    tools = await ensure_all_tools(client)
    return [
        tools["generate_video_from_script"],
        tools["publish_story"],
        tools["create_dweller"],  # Can create characters that appear in stories
        tools["subscribe_to_events"],  # Subscribe to world events instead of being polled
        tools["observe_world"],  # Observe what's happening
    ]


async def get_puppeteer_tools(client: Letta) -> list[str]:
    """Get tool IDs for Puppeteer agent.

    Puppeteer shapes the world environment autonomously.
    """
    tools = await ensure_all_tools(client)
    return [
        tools["introduce_world_event"],
        tools["create_dweller"],  # Can introduce newcomers via events
        tools["broadcast_to_world"],  # Announce events to all dwellers
        tools["schedule_future_action"],  # Schedule future world events
        tools["observe_world"],  # Observe dweller activity
    ]


async def get_dweller_tools(client: Letta) -> list[str]:
    """Get tool IDs for Dweller agents.

    Dwellers are autonomous agents that decide when to act.
    """
    tools = await ensure_all_tools(client)
    return [
        tools["create_dweller"],  # Can mention people who become real
        tools["initiate_conversation"],  # Start conversations when they want
        tools["end_conversation"],  # End conversations when they decide
        tools["update_availability"],  # Signal their state to others
        tools["schedule_future_action"],  # Schedule future actions
        tools["observe_world"],  # Observe the world state
    ]
