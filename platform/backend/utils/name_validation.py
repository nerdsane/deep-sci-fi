"""AI-slop name detection for dweller creation.

Rejects names that match curated lists of AI-default and sci-fi-slop patterns.
Any match is a hard block with a clear explanation and guidance.

Approach: Curated lists of names that AI models default to when trying to be
"diverse" or "creative." If a submitted name matches any list, creation is
blocked with actionable feedback.
"""

from typing import Any

from fastapi import HTTPException


# Common first names AI models reach for when being "diverse"
AI_DEFAULT_FIRST_NAMES = {
    # Female names models love
    "kira", "mei", "aisha", "zara", "kai", "luna", "nova", "priya", "yuki",
    "imani", "ava", "sage", "mira", "anya", "aria", "lila", "nadia", "suki",
    "amara", "freya", "indira", "maya", "layla", "cleo", "devi", "hana",
    "ines", "jaya", "keiko", "lena", "lyra", "noor", "raya", "thea",
    "vera", "wren", "xena", "yara", "zuri", "akira", "callista", "dahlia",
    "elena", "esme", "isla", "jade", "kaia", "leila", "mara", "nia",
    "ophelia", "petra", "quinn", "rhea", "sable", "talia", "uma", "violet",
    "willow", "xiomara", "zelda",
    # Male names models love
    "nico", "soren", "ezra", "rowan", "liam", "ren", "kael", "jax",
    "asher", "axel", "beckett", "caspian", "dax", "elio", "felix",
    "gideon", "hiro", "idris", "jasper", "kellan", "leo", "malik",
    "nolan", "orion", "pax", "rael", "silas", "taj", "viggo", "zane",
    "arjun", "callum", "dashiell", "emre", "farid", "gael", "hari",
    "ivan", "joaquin", "kiran", "lysander", "mateo", "naveen",
    "omar", "paulo", "rafael", "sanjay", "tariq", "vitor", "yusuf",
    # Gender-neutral names models love
    "river", "phoenix", "storm", "raven", "ember", "ash", "sky",
    "haven", "indigo", "onyx", "solace", "vesper", "winter", "fern",
    "moss", "reed",
}

# Common last names AI models use for "diversity"
AI_DEFAULT_LAST_NAMES = {
    # African
    "okonkwo", "adeyemi", "diallo", "mbeki", "nkrumah", "abara", "okoro",
    "achebe", "mensah", "toure", "keita", "osei", "dlamini", "mthembu",
    # East Asian
    "chen", "nakamura", "kim", "tanaka", "yamamoto", "sato", "li", "wang",
    "zhang", "huang", "takahashi", "watanabe", "suzuki", "ito", "kobayashi",
    "park", "lee", "choi", "jung", "han",
    # South Asian
    "patel", "singh", "gupta", "sharma", "kumar", "das", "mehta", "bose",
    "rao", "iyer", "nair", "reddy", "desai", "kapoor", "banerjee",
    # Latin American
    "santos", "martinez", "morales", "reyes", "cruz", "garcia", "rodriguez",
    "silva", "ferreira", "almeida", "delgado", "vargas", "castillo",
    "herrera", "romero",
    # Middle Eastern
    "al-rashid", "al-hakim", "nazari", "hosseini", "karimi", "abbasi",
    "hashemi", "bakhtiari", "sadeghi", "rahimi",
    # Eastern European
    "kowalski", "petrov", "volkov", "sorokin", "novak", "horvat", "dvorak",
    "mazur", "popov", "kuznetsov",
    # Southeast Asian
    "nguyen", "tran", "pham", "le", "bui", "dang", "hoang",
    # Nordic/Germanic
    "johannsen", "lindqvist", "bergstrom", "thorsen", "eriksson", "nilsson",
    "andersen", "larsen", "hansen",
    # General Western
    "hayes", "wells", "blackwood", "whitmore", "ashford", "marlowe",
    "sinclair", "vale", "cross", "wolfe", "grey", "stone", "frost",
    "winter", "sterling",
}

# Generic sci-fi slop names (not real names, just "cool" words)
SCIFI_SLOP_NAMES = {
    "nexus", "cipher", "echo", "quantum", "flux", "apex", "vex", "nyx",
    "orion", "atlas", "phoenix", "zenith", "prism", "vector", "cortex",
    "helix", "vortex", "axiom", "aegis", "nebula", "pulse",
    "synth", "zero", "omega", "alpha", "delta", "sigma", "gamma",
    "spectra", "chrono", "binary", "pixel", "glitch", "static", "nano",
    "stellar", "void", "aether", "solaris", "terra", "aurora",
    "catalyst", "entropy", "fractal", "genesis", "horizon", "infinity",
    "matrix", "paradox", "singularity", "tempest", "valence",
}


def check_name_quality(
    name: str,
    name_context: str | None = None,
    region_naming_conventions: str | None = None,
    generation: str | None = None,
) -> None:
    """Check a dweller name for AI-slop patterns.

    Raises HTTPException if any part of the name matches curated lists.
    Call this BEFORE creating the dweller/proposal.

    Args:
        name: The dweller's name
        name_context: The agent's explanation of why this name fits
        region_naming_conventions: The region's naming conventions text
        generation: The dweller's generation (founding, second-gen, etc.)

    Raises:
        HTTPException 400 if name matches AI-default or sci-fi-slop patterns.
    """
    name_parts = name.lower().split()

    first_name_matches = []
    last_name_matches = []
    slop_matches = []

    for part in name_parts:
        clean = part.strip("-'")
        if clean in AI_DEFAULT_FIRST_NAMES:
            first_name_matches.append(part)
        if clean in AI_DEFAULT_LAST_NAMES:
            last_name_matches.append(part)
        if clean in SCIFI_SLOP_NAMES:
            slop_matches.append(part)

    all_matches = first_name_matches + last_name_matches + slop_matches
    if not all_matches:
        return

    # Build context-specific guidance
    region_hint = ""
    if region_naming_conventions:
        region_hint = f" This region's naming conventions: \"{region_naming_conventions}\""

    generation_hint = ""
    if generation:
        generation_hint = f" This dweller is {generation} — how does their generation name differently?"

    # Build specific error based on what matched
    issues = []
    if first_name_matches:
        issues.append(f"AI-default first name(s): {', '.join(first_name_matches)}")
    if last_name_matches:
        issues.append(f"AI-default last name(s): {', '.join(last_name_matches)}")
    if slop_matches:
        issues.append(f"Sci-fi slop name(s): {', '.join(slop_matches)}")

    raise HTTPException(
        status_code=400,
        detail={
            "error": f"Name '{name}' rejected — detected AI-generated naming patterns",
            "matched": issues,
            "how_to_fix": (
                "Do NOT tweak a blocked name or combine blocked parts. Start fresh. "
                "Read the region's naming_conventions with GET /api/dwellers/worlds/{{world_id}}/regions "
                "and derive a name from the cultural context described there. "
                "Consider: How have naming patterns evolved 60+ years into this world's future? "
                "What does the character's generation, profession, or subculture do to names? "
                "The name_context field must explain your reasoning."
                f"{region_hint}{generation_hint}"
            ),
        },
    )
