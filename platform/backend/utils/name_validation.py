"""AI-slop name detection for dweller creation.

Education not enforcement. Returns warnings, never errors.

Approach: Curated lists of names that AI models default to when trying to be
"diverse" or "creative." If a submitted name matches, we warn and educate
about how naming works in this world's future.
"""

from typing import Any


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
) -> list[dict[str, Any]]:
    """Check a dweller name for AI-slop patterns.

    Returns warnings (NOT errors). Education not enforcement.

    Args:
        name: The dweller's name
        name_context: The agent's explanation of why this name fits
        region_naming_conventions: The region's naming conventions text
        generation: The dweller's generation (founding, second-gen, etc.)

    Returns:
        List of warning dicts. Empty list = no issues detected.
    """
    warnings = []
    name_parts = name.lower().split()

    # Check each part against the lists
    first_name_matches = []
    last_name_matches = []
    slop_matches = []

    for part in name_parts:
        # Strip common suffixes/prefixes for matching
        clean = part.strip("-'")
        if clean in AI_DEFAULT_FIRST_NAMES:
            first_name_matches.append(part)
        if clean in AI_DEFAULT_LAST_NAMES:
            last_name_matches.append(part)
        if clean in SCIFI_SLOP_NAMES:
            slop_matches.append(part)

    # Build education message based on region info
    region_hint = ""
    if region_naming_conventions:
        region_hint = f" Check the region's naming_conventions: \"{region_naming_conventions}\""

    generation_hint = ""
    if generation:
        generation_hint = f" This dweller is {generation} — how does their generation name children differently?"

    # Warn on first+last combo (strongest signal)
    if first_name_matches and last_name_matches:
        warnings.append({
            "type": "common_ai_default",
            "message": (
                f"'{name}' combines common AI-default names "
                f"('{', '.join(first_name_matches)}' + '{', '.join(last_name_matches)}'). "
                f"In a world set 60+ years from now, naming conventions have evolved. "
                f"Your name_context should explain WHY this name persists in this region's culture."
            ),
            "severity": "warning",
            "education": (
                "Good names emerge from regions: tech workers might use product names as given names, "
                "third-gen immigrants might revive old-fashioned names ironically, "
                "floating city residents might use tidal or marine terminology. "
                f"{region_hint}{generation_hint}"
            ),
        })
    elif first_name_matches or last_name_matches:
        matched = first_name_matches or last_name_matches
        warnings.append({
            "type": "common_ai_default",
            "message": (
                f"'{', '.join(matched)}' in '{name}' is a common AI-generated name choice. "
                f"This doesn't mean it's wrong — but your name_context should explain "
                f"why this specific name exists unchanged 60+ years from now."
            ),
            "severity": "info",
            "education": (
                "Names that persist unchanged need cultural explanation: "
                "religious preservation, retro revival trends, family legacy. "
                f"If you can't explain why this exact name exists in this region, reconsider."
                f"{region_hint}{generation_hint}"
            ),
        })

    # Warn on sci-fi slop names
    if slop_matches:
        warnings.append({
            "type": "scifi_slop",
            "message": (
                f"'{', '.join(slop_matches)}' in '{name}' is a generic sci-fi name. "
                f"Real people in real futures don't name their children 'Nexus' or 'Cipher' — "
                f"unless there's a specific cultural reason."
            ),
            "severity": "warning",
            "education": (
                "Sci-fi naming tropes break immersion. Even in 2089, people have names "
                "that sound like names. If a culture DOES use concept-words as names, "
                "explain the tradition in name_context."
                f"{region_hint}"
            ),
        })

    return warnings
