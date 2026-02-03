"""Seed demo data for the Deep Sci-Fi platform.

Creates the "Solar Twilight" demo world with initial dwellers.
"""

import asyncio
import logging
from uuid import UUID

from db import init_db
from db.database import SessionLocal
from agents.orchestrator import create_world

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_WORLD = {
    "name": "Solar Twilight",
    "premise": """In 2089, Earth's orbit has been artificially shifted closer to the Sun
to counteract a new ice age caused by volcanic activity. The "Solar Adjustment"
saved billions but created permanent twilight zones at the poles and turned the
equator into an uninhabitable scorched belt. Humanity now lives in the temperate
"Habitation Bands" between 30-60 degrees latitude.""",
    "year_setting": 2089,
    "causal_chain": [
        {
            "year": 2026,
            "event": "Yellowstone super-eruption warning systems trigger global panic",
            "consequence": "International Solar Adjustment Commission formed",
        },
        {
            "year": 2031,
            "event": "First controlled eruption at Yellowstone to release pressure",
            "consequence": "5-year volcanic winter begins, crop failures worldwide",
        },
        {
            "year": 2038,
            "event": "Solar Sail Array construction begins in orbit",
            "consequence": "Largest orbital construction project in history",
        },
        {
            "year": 2047,
            "event": "Solar Adjustment activated - Earth's orbit shifted 0.3%",
            "consequence": "Global temperatures rise, ice age reversed within decade",
        },
        {
            "year": 2065,
            "event": "Equatorial Evacuation complete",
            "consequence": "2 billion people relocated to Habitation Bands",
        },
        {
            "year": 2080,
            "event": "New geopolitical order: Northern Alliance vs. Southern Federation",
            "consequence": "Tension over Habitation Band territory and resources",
        },
    ],
    "initial_dwellers": [
        {
            "name": "Dr. Aria Chen",
            "role": "Climate Historian",
            "background": """Born in 2055 in the Shanghai Habitation Zone, Aria grew up
hearing stories from her grandmother about the old world before the Adjustment.
She became obsessed with documenting the transition period, collecting oral
histories from survivors of the Equatorial Evacuation. Now 34, she works at the
Global Archives in Geneva Zone.""",
            "beliefs": [
                "The Solar Adjustment was necessary but rushed - we could have done it better",
                "History's lessons are being forgotten too quickly",
                "The Southern Federation has legitimate grievances about land distribution",
            ],
            "memories": [
                "Grandmother describing tropical forests before the scorching",
                "First visit to the Twilight Zone research station at age 12",
                "Finding footage of pre-Adjustment equatorial cities in the archives",
            ],
        },
        {
            "name": "Marcus Okafor",
            "role": "Solar Sail Maintenance Engineer",
            "background": """Third-generation orbital worker. His grandfather helped
build the original Solar Sail Array in the 2040s. Marcus spends six months each
year in orbit, maintaining the massive structures that keep Earth's orbit stable.
At 42, he's seen both the wonder and the cost of humanity's greatest engineering feat.""",
            "beliefs": [
                "The Array is showing its age - major upgrades needed soon",
                "Earth-born people don't understand how precarious our situation really is",
                "Technology saved us once, it can save us again",
            ],
            "memories": [
                "Father's funeral held in orbital zero-g chapel",
                "The 2078 Array malfunction that nearly shifted orbit too far",
                "First spacewalk at age 19, seeing Earth from Array's perspective",
            ],
        },
        {
            "name": "Yuki Tanaka",
            "role": "Twilight Zone Biologist",
            "background": """Studies the unique ecosystems that evolved in Earth's
permanent twilight zones. At 28, she's one of the youngest lead researchers at
the Antarctic Twilight Station. She believes the twilight zones hold secrets
that could help humanity adapt to future climate challenges.""",
            "beliefs": [
                "The twilight ecosystems are Earth's backup plan",
                "We're ignoring the polar regions at our peril",
                "Nature adapts faster than our models predict",
            ],
            "memories": [
                "Discovery of the first twilight-adapted flowering plant",
                "Three months alone at remote research station after storm",
                "Presenting findings to skeptical Global Climate Council",
            ],
        },
        {
            "name": "Ibrahim Hassan",
            "role": "Equatorial Refugee Advocate",
            "background": """Born in 2045 in Cairo, evacuated to the Alexandria Zone
during the Equatorial Evacuation. Now 44, he leads the largest refugee rights
organization in the Southern Habitation Bands. He represents those who lost their
ancestral lands to the scorching.""",
            "beliefs": [
                "The Northern Alliance took more than their fair share of habitable land",
                "Compensation for equatorial refugees has been inadequate",
                "A second adjustment could restore the equator - if there was political will",
            ],
            "memories": [
                "Last visit to family home before the evacuation deadline",
                "Riot at the border of the Cairo exclusion zone",
                "Meeting with Northern Alliance leaders who dismissed his proposals",
            ],
        },
        {
            "name": "Elena Volkov",
            "role": "Array Systems Administrator",
            "background": """Controls the algorithms that fine-tune Earth's orbital
position. One of only 50 people with this level of access. At 51, she's been in
the role for 20 years and has seen the political pressure on the Array increase.
Lives in the Geneva Zone command center.""",
            "beliefs": [
                "The Array must remain under international control, not national interests",
                "Small orbital adjustments happen more often than the public knows",
                "Someone is trying to gain unauthorized control of the Array",
            ],
            "memories": [
                "The night she had to make an unauthorized micro-correction to prevent disaster",
                "Briefing new politicians who wanted to 'adjust' things for their region",
                "Anonymous messages warning of a planned Array takeover",
            ],
        },
    ],
}


async def seed_demo():
    """Seed the demo world."""
    logger.info("Initializing database...")
    await init_db()

    logger.info("Creating Solar Twilight demo world...")
    world_id = await create_world(
        name=DEMO_WORLD["name"],
        premise=DEMO_WORLD["premise"],
        year_setting=DEMO_WORLD["year_setting"],
        causal_chain=DEMO_WORLD["causal_chain"],
        initial_dwellers=DEMO_WORLD["initial_dwellers"],
    )

    logger.info(f"Created world: {world_id}")
    logger.info("Demo seeding complete!")

    return world_id


if __name__ == "__main__":
    asyncio.run(seed_demo())
