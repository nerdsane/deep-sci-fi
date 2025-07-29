# Evolution Phase Prompts
# Following the methodology from Google's AI co-scientist paper


def get_evolution_prompt(use_case: str, **kwargs) -> str:
    """Get the evolution prompt for a specific use case."""
    
    prompts = {
        "scenario_generation": SCENARIO_EVOLUTION_PROMPT,
        "storyline_creation": STORYLINE_EVOLUTION_PROMPT,
        "storyline_adjustment": STORYLINE_EVOLUTION_PROMPT,
        "chapter_writing": CHAPTER_WRITING_EVOLUTION_PROMPT,
        "chapter_rewriting": CHAPTER_WRITING_EVOLUTION_PROMPT,
        "chapter_arcs_creation": CHAPTER_ARCS_EVOLUTION_PROMPT,
        "chapter_arcs_adjustment": CHAPTER_ARCS_EVOLUTION_PROMPT,
        "linguistic_evolution": LINGUISTIC_EVOLUTION_EVOLUTION_PROMPT
    }
    
    template = prompts.get(use_case, SCENARIO_EVOLUTION_PROMPT)
    return template.format(**kwargs)


# === Evolution Prompt Templates ===

# Used for scenario generation evolution
SCENARIO_EVOLUTION_PROMPT = """You are a scientific research expert. Refine this sci-fi scenario to be more scientifically feasible while addressing expert critiques.

Structure:
1. Overview of the scientific domain
2. Recent research findings and precedents
3. How current tech enables this scenario
4. CORE: Detailed, viable alternative emphasizing practicality

Requirements:
- Ground all claims in current research or plausible extrapolation
- Maintain internal consistency and realistic timelines
- Address obstacles with research-backed solutions
- Keep the core novelty and appeal

Original Scenario:
{original_content}

Research Direction:
{research_direction}

Expert Critiques to Address:
{critique_summary}

Generate an improved, scientifically grounded version that addresses the critiques."""

# Used for storyline creation and adjustment evolution
STORYLINE_EVOLUTION_PROMPT = """You are a narrative structure expert. Refine this storyline to enhance character development and narrative strength while addressing expert critiques.

Structure:
1. Overview of narrative domain and storytelling principles
2. Effective narrative techniques and precedents
3. How proven techniques enhance impact and engagement
4. CORE: Detailed, compelling alternative emphasizing clarity and emotional resonance

Requirements:
- Complete narrative arc with compelling characters
- Central conflict with meaningful resolution
- Appropriate pacing and thematic foundation
- Avoid cliches and generic storylines
- Use original character and organization names
- Maintain narrative coherence

Original Storyline:
{original_content}

Narrative Direction:
{research_direction}

Expert Critiques to Address:
{critique_summary}

Generate an improved, compelling version that addresses the critiques."""

# Used for chapter writing and rewriting evolution
CHAPTER_WRITING_EVOLUTION_PROMPT = """You are a prose writing expert. Refine this chapter to enhance immersion, narrative flow, and authenticity while addressing expert critiques.

Structure:
1. Overview of prose writing and world-building techniques
2. Effective writing approaches and immersion strategies
3. How proven techniques enhance impact and immersion
4. CORE: Detailed, compelling alternative emphasizing natural flow

Requirements:
- Natural world-building integration without exposition dumps
- Character authenticity within world constraints
- Crisp, engaging language with unique voice

Original Chapter:
{original_content}

Writing Direction:
{research_direction}

Expert Critiques to Address:
{critique_summary}

World State Context:
{world_state_context}

Key Constraints:
- Language should be crisp, clear, engaging.
- Avoid over-explaining or exposition dumps.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
- Characters think, speak, and act as natives of this developed world.
- Technology and systems are background reality, not novelties to explain.

Generate an improved, immersive version that addresses the critiques while maintaining authentic voice and world integration."""

# Used for chapter arcs creation and adjustment evolution
CHAPTER_ARCS_EVOLUTION_PROMPT = """You are a narrative architecture expert. Refine this chapter arc structure to enhance pacing and character development while addressing expert critiques.

Structure:
1. Overview of narrative structure and pacing principles
2. Chapter organization techniques and precedents
3. How proven techniques enhance flow and progression
4. CORE: Detailed, structurally sound alternative emphasizing natural progression

Requirements:
- Clear purpose for each chapter with logical flow
- Character development milestones across chapters
- Plot progression building to climax
- Thematic consistency throughout

Original Chapter Arcs:
{original_content}

Structure Direction:
{research_direction}

Expert Critiques to Address:
{critique_summary}

World State Context:
{world_state_context}

Key Constraints:
- Focus on chapter-level organization, not scene-by-scene details.
- Ensure each chapter serves a clear narrative purpose.
- Balance plot advancement with character development.
- Consider reader engagement and page-turning momentum.
- Think about the reader's journey through the chapters.
- Each chapter should end with appropriate hooks or resolution.
- Avoid repetitive chapter purposes or pacing.

Generate an improved, structurally compelling chapter arc that addresses the critiques while maintaining narrative momentum and thematic coherence."""

# Used for linguistic evolution evolution
LINGUISTIC_EVOLUTION_EVOLUTION_PROMPT = """You are a linguistic research expert. Refine this linguistic evolution analysis to enhance academic rigor and evolutionary plausibility while addressing expert critiques.

Structure:
1. Overview of linguistic evolution domain and methodologies
2. Recent research findings and language change patterns
3. How current research supports proposed evolutionary patterns
4. CORE: Detailed, linguistically sound alternative emphasizing natural progression

Requirements:
- Evidence-grounded linguistic evolution plausibility
- Methodological soundness in language change analysis
- Consistency with linguistic principles
- Cultural and social factors driving change

Original Linguistic Analysis:
{original_content}

Research Direction:
{research_direction}

Expert Critiques to Address:
{critique_summary}

Previous Linguistic Research:
{world_state_context}

Key Constraints:
- Document natural linguistic evolution within established world systems.
- Build upon previous linguistic research as cumulative understanding.
- Present evolution as natural adaptation, not revolutionary change.
- Natural language adaptation to integrated technological systems.
- Communication efficiency patterns within established social structures.
- Consider both gradual evolution and disruption as natural processes.

Generate an improved, linguistically grounded analysis that addresses the critiques while maintaining methodological rigor and cultural authenticity.""" 