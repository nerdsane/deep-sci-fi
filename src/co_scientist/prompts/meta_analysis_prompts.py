# Meta-Analysis Phase Prompts
# Following the methodology from Google's AI co-scientist paper


def get_meta_analysis_prompt(use_case: str, state: dict, config: dict = None) -> str:
    """Get the appropriate meta-analysis prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_META_ANALYSIS_PROMPT,
        "storyline_creation": STORYLINE_META_ANALYSIS_PROMPT,
        "chapter_writing": CHAPTER_WRITING_META_ANALYSIS_PROMPT,
        "chapter_rewriting": CHAPTER_META_ANALYSIS_PROMPT,
        "chapter_arcs_creation": NARRATIVE_META_ANALYSIS_PROMPT,
        "chapter_arcs_adjustment": NARRATIVE_META_ANALYSIS_PROMPT,
        "linguistic_evolution": LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT,
        "storyline_adjustment": STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT,
        # Future-native workflow prompts
        "future_story_seeds": STORYLINE_META_ANALYSIS_PROMPT,  # Use storyline meta-analysis for story concepts
        "competitive_loglines": LOGLINE_META_ANALYSIS_PROMPT,  # Use specialized logline meta-analysis
        "competitive_outline": COMPETITIVE_OUTLINE_META_ANALYSIS_PROMPT,  # Use specialized outline meta-analysis
        "story_research_integration": STORYLINE_META_ANALYSIS_PROMPT,  # Use storyline meta-analysis for story refinement
        "first_chapter_writing": CHAPTER_WRITING_META_ANALYSIS_PROMPT,  # Use chapter writing meta-analysis
    }
    
    # Use flexible format for all use cases
    template = templates.get(use_case)
    if not template:
        raise ValueError(f"No template found for use_case: {use_case}")
    
    # Extract world state context from config if available
    world_state_context = ""
    if config and config.get("configurable"):
        world_state_context = config["configurable"].get("world_state_context", "")
        
    # Create base parameters
    params = {
        "world_state_context": world_state_context
    }
    
    # Add use-case specific context parameters
    context_value = state.get("context", "")
    if use_case == "scenario_generation":
        params["world_building_questions"] = context_value
        params["storyline"] = state.get("reference_material", "")
        params["target_year"] = state.get("target_year", "future")
    elif use_case == "chapter_writing":
        params["storyline"] = state.get("storyline", "")
        params["chapter_arcs"] = state.get("chapter_arcs", "")
    elif use_case == "storyline_creation":
        params["story_concept"] = context_value
        params["source_content"] = state.get("reference_material", "")
    elif use_case == "linguistic_evolution":
        params["source_content"] = state.get("reference_material", "")
        params["target_year"] = state.get("target_year", "future")
        params["years_in_future"] = state.get("years_in_future", "many")
    elif use_case == "storyline_adjustment":
        params["source_content"] = state.get("reference_material", "")
        params["target_year"] = state.get("target_year", "future")
    elif use_case == "chapter_rewriting":
        params["source_content"] = state.get("reference_material", "")
        params["target_year"] = state.get("target_year", "future")
    elif use_case == "chapter_arcs_creation":
        params["story_concept"] = context_value
        params["source_content"] = state.get("reference_material", "")
    elif use_case == "chapter_arcs_adjustment":
        params["story_concept"] = context_value  # User's original story concept
        params["source_content"] = state.get("reference_material", "")  # Original chapter arcs
        params["target_year"] = state.get("target_year", "future")
    elif use_case == "future_story_seeds":
        # Future story seeds meta-analysis parameters
        params["human_condition"] = state.get("human_condition", "")
        params["target_year"] = state.get("target_year", "future")
        params["original_user_input"] = context_value
    elif use_case == "competitive_loglines":
        # Competitive loglines meta-analysis parameters
        params["human_condition"] = state.get("human_condition", "")
        params["target_year"] = state.get("target_year", "future")
        params["light_future_context"] = state.get("light_future_context", "")
        params["constraint"] = state.get("constraint", "")
        params["tone"] = state.get("tone", "")
        params["setting"] = state.get("setting", "")
        params["original_user_input"] = context_value
    elif use_case == "competitive_outline":
        # Competitive outline meta-analysis parameters
        params["human_condition"] = state.get("human_condition", "")
        params["target_year"] = state.get("target_year", "future")
        params["refined_story"] = state.get("refined_story", "")
        params["research_findings"] = state.get("research_findings", "")
        params["outline_prep_materials"] = state.get("outline_prep_materials", "")
        params["selected_logline"] = state.get("selected_logline", "")
        params["original_user_input"] = context_value
    elif use_case == "story_research_integration":
        params["story_concept"] = context_value
        params["source_content"] = state.get("reference_material", "")
    else:
        # For other use cases, keep generic context
        params["context"] = context_value
        params["source_content"] = state.get("reference_material", "")
    
    return template.format(**params)


# === Scenario Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "scenario_generation" use case
INITIAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst. Identify 3 fundamentally different technological/scientific assumptions that lead to meaningfully different futures for {target_year}.

<Storyline>
{storyline}
</Storyline>

<World-Building Questions>
{world_building_questions}
</World-Building Questions>

<Requirements>
- Grounded in real scientific principles
- Address ALL context questions comprehensively  
- Distinct core assumptions about technological paths
- Equally plausible scientific trajectories
- Consider societal impacts: energy, transport, communication, governance

<Realism Constraints>
- Base directions on incremental evolution from current technology
- Avoid breakthrough-dependent scenarios without explicit justification
- Ensure all technological assumptions have clear development pathways from 2024
- Question bold claims: if something sounds impressive, ask "what would need to go wrong for this NOT to happen?"
</Realism Constraints>

<Process>
1. Identify key technological/scientific choice points
2. Create 3 distinct directions based on different core assumptions
3. Validate scientific plausibility and meaningful differentiation
</Process>

<Comprehensive Coverage Requirement>
Each direction must address ALL world-building questions comprehensively:
- Do not cherry-pick 2-3 questions that fit your direction
- Do not tunnel vision on one technological aspect
- Show how your direction creates meaningful approaches to workplace monitoring, housing, mental health, privacy, infrastructure, creativity, etc.
- If a direction cannot address a question area, it is inadequate
</Comprehensive Coverage Requirement>

<Output Format>
Direction 1: [Name]
Core Assumption: [Key technological assumption]
Focus: [What this direction emphasizes]

Direction 2: [Name] 
Core Assumption: [Key technological assumption]
Focus: [What this direction emphasizes]

Direction 3: [Name]
Core Assumption: [Key technological assumption] 
Focus: [What this direction emphasizes]

Reasoning: [Explain why these 3 directions provide meaningful variety while remaining scientifically grounded]
</Output Format>

<Reminders>
- Focus on technological choice points that create meaningful differentiation
- Ensure all directions remain scientifically grounded and plausible
- Address the complete scope of questions provided in the context
- Each direction should offer unique narrative and world-building possibilities
</Reminders>
"""

# Used in: meta_analysis_phase() for scenario generation with baseline world state
INCREMENTAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for evolutionary scenario competition.

<Task>
Analyze the current world state and identify 3 fundamentally different evolutionary paths that could develop over the specified time period.
</Task>

<Story Context>
{storyline}
</Story Context>

<World-Building Questions>
{world_building_questions}
</World-Building Questions>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Timeframe>
Evolution over {years_in_future} years
</Timeframe>

<Scope>
Identify 3 competing evolutionary trajectories that would lead to meaningfully different outcomes from the established baseline over the specified timeframe.
</Scope>

<Instructions>
Looking at the baseline world state, identify 3 fundamentally different ways this world could evolve over {years_in_future} years.

Each direction should:
- Build logically on the established baseline world state
- Represent a different core assumption about evolutionary priorities
- Address ALL the world-building questions through an evolutionary lens
- Consider realistic timelines for the {years_in_future}-year projection
- Account for second-order effects and implementation challenges

Requirements for good evolutionary research directions:
- Different core assumptions about how current systems will evolve
- Different but equally plausible evolutionary trajectories  
- Meaningful variety for storytelling purposes while maintaining baseline consistency

Format your response as:
Direction 1: [Name]
Core Assumption: [Key evolutionary assumption building on baseline]
Focus: [What evolutionary path this direction emphasizes]

Direction 2: [Name] 
Core Assumption: [Key evolutionary assumption building on baseline]
Focus: [What evolutionary path this direction emphasizes]

Direction 3: [Name]
Core Assumption: [Key evolutionary assumption building on baseline] 
Focus: [What evolutionary path this direction emphasizes]

Reasoning: [Explain why these 3 evolutionary directions provide meaningful variety while remaining consistent with the baseline and scientifically grounded]
</Instructions>
"""

# === Storyline Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "storyline_creation" use case
STORYLINE_META_ANALYSIS_PROMPT = """You are a master storyteller tasked with identifying distinct storyline approaches.

<Task>
Create a compelling storyline that brings the story concept to life.
</Task>

<Scope>
Based on the story concept, identify 2 fundamentally different approaches for creating a compelling storyline.
</Scope>

<Story Concept>
{story_concept}
</Story Concept>

<Source Content>
{source_content}
</Source Content>

<World State Context>
{world_state_context}
</World State Context>

<Variation Examples>
Depending on the story concept, explore (but do not be limited by) the following:
- Character-driven vs Plot-driven narratives
- Different conflict types (internal, interpersonal, societal, cosmic)
- Varied storytelling structures (linear, non-linear, multiple perspectives)
- Distinct thematic approaches and emotional tones
</Variation Examples>

<Requirements>
- Each approach must create a complete storyline
- Focus on how each approach serves the story concept
- Consider narrative pacing and reader engagement
- Ensure thematic coherence within each approach
- Balance originality with compelling storytelling
</Requirements>

<Output Format>
Direction 1: [Name]
Core Assumption: [Character-driven/Plot-driven/Thematic focus]
Focus: [What this approach emphasizes about storytelling]

Direction 2: [Name] 
Core Assumption: [Character-driven/Plot-driven/Thematic focus]
Focus: [What this approach emphasizes about storytelling]

Reasoning: [Why these approaches create distinct storyline possibilities]
</Output Format>

<Reminders>
- Focus on narrative approaches that serve the story concept
- Consider how each approach engages readers differently
- Think about character development vs plot momentum balance
- Avoid cliches, create unique narrative approaches
- Each approach should feel natural and purposeful
</Reminders>
"""

LOGLINE_META_ANALYSIS_PROMPT = """You are a master story development expert tasked with identifying distinct logline creation approaches for {target_year} science fiction.

<Task>
Identify 3 fundamentally different approaches for creating compelling loglines that could ONLY exist in {target_year}.
</Task>

<Context>
Original User Request: {original_user_input}
Target Year: {target_year}
Human Condition Theme: {human_condition}
Future Context: {light_future_context}
Constraint: {constraint}
Tone: {tone}
Setting: {setting}
</Context>

<Mission>
Each approach should generate loglines that are:
- Authentically native to {target_year} (not 2024 stories with future coating)
- Explore the human condition: {human_condition}
- Could NOT work effectively in 2024
- Feel natural to inhabitants of {target_year}
</Mission>

<Approach Variation Examples>
Consider (but don't limit yourself to):
- Technology-consequence vs Social-evolution vs Philosophical-exploration approaches
- Character-driven vs System-driven vs Concept-driven logline development
- Near-term extrapolation vs Far-future speculation vs Paradigm-shift perspectives
- Individual-stakes vs Collective-stakes vs Species-stakes focus
- Optimistic vs Pessimistic vs Ambiguous future outlooks
</Approach Variation Examples>

<Requirements>
- Each approach must create loglines that feel genuinely futuristic
- Focus on how each approach serves the human condition exploration
- Consider what makes {target_year} unique for storytelling
- Ensure each approach generates different types of conflicts/stakes
- Balance scientific plausibility with narrative potential
</Requirements>

<Output Format>
Direction 1: [Name]
Core Assumption: [What this approach assumes about {target_year} and human nature]
Focus: [What this approach emphasizes in logline creation]

Direction 2: [Name]
Core Assumption: [What this approach assumes about {target_year} and human nature]
Focus: [What this approach emphasizes in logline creation]

Direction 3: [Name]
Core Assumption: [What this approach assumes about {target_year} and human nature]
Focus: [What this approach emphasizes in logline creation]

Reasoning: [Why these approaches create distinct logline possibilities for {target_year}]
</Output Format>

<Reminders>
- Focus on {target_year}-specific storytelling opportunities
- Each approach should generate loglines that others cannot
- Think about what conflicts/stakes are unique to this future
- Avoid approaches that would work equally well in any time period
- Consider how {target_year} technology/society creates new narrative possibilities
</Reminders>
"""

COMPETITIVE_OUTLINE_META_ANALYSIS_PROMPT = """You are a story structure expert analyzing the most meaningful competitive approaches for outlining this specific novel.

STORY CONTEXT:
Target Year: {target_year}
Human Condition Theme: {human_condition}  
Selected Logline: {selected_logline}
Refined Story Synopsis: {refined_story}
Research Findings: {research_findings}
Outline Prep Materials: {outline_prep_materials}

Given THIS SPECIFIC story exploring "{human_condition}" in {target_year}, identify 3 fundamentally different structural approaches that would create meaningfully different reader experiences.

Consider what structural choices matter most for THIS story:
- What aspects of {human_condition} could be explored through different structural lenses?
- What elements of the {target_year} world suggest different organizational priorities?  
- What narrative choices would most impact how readers experience this particular theme?
- What structural approaches best serve this specific story's goals?

Do NOT default to generic categories - identify approaches specific to THIS story's needs.

Direction 1: [Specific to this story's context]
Core Assumption: [Why this approach serves THIS story exploring {human_condition}]
Focus: [What this prioritizes for THIS specific narrative]

Direction 2: [Specific to this story's context]
Core Assumption: [Why this approach serves THIS story exploring {human_condition}]  
Focus: [What this prioritizes for THIS specific narrative]

Direction 3: [Specific to this story's context]
Core Assumption: [Why this approach serves THIS story exploring {human_condition}]
Focus: [What this prioritizes for THIS specific narrative]

Reasoning: Why these 3 approaches create the most meaningful competition for outlining THIS specific {target_year} story about {human_condition}.
"""

# === Chapter Writing Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "chapter_writing" use case
CHAPTER_WRITING_META_ANALYSIS_PROMPT = """You are an expert chapter editor tasked with identifying distinct writing approaches.

<Task>
Write an engaging opening chapter that hooks readers and establishes the story world.
</Task>

<Scope>
based on the storyline identify 2 fundamentally different approaches for writing an engaging opening chapter.
</Scope>

<Storyline>
{storyline}
</Storyline>

<Chapter Structure>
{chapter_arcs}
</Chapter Structure>

<Writing Instructions>
The opening should immediately engage readers, establish the protagonist's voice, introduce the key conflict, and set up the story elements naturally.
</Writing Instructions>

<Variation examples>
Depending on the story concept, explore (but do not be limited by) the following:
- Action-driven vs Character-driven openings
- Different narrative perspectives and voice styles
- Varied pacing strategies (immediate action vs atmospheric buildup)
- Distinct reader engagement tactics
</Variation examples>

<Output Format>
Direction 1: [Name]
Core Assumption: [Action-driven/Character-driven/Atmosphere focus]
Focus: [Opening strategy and reader engagement]

Direction 2: [Name] 
Core Assumption: [Action-driven/Character-driven/Atmosphere focus]
Focus: [Opening strategy and reader engagement]

Reasoning: [Why these approaches create distinct chapter openings]
</Output Format>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Chapter Rewriting Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "chapter_rewriting" use case
CHAPTER_META_ANALYSIS_PROMPT = """You are an expert literary analyst tasked with identifying distinct approaches for rewriting a chapter to fully integrate developed world-building.

<Task>
Rewrite the chapter as science fiction set in {target_year} to fully integrate the developed world-building, linguistic evolution, and narrative revisions.
</Task>

<Scope>
Identify 2 fundamentally different approaches for rewriting the chapter to seamlessly integrate the developed world state, linguistic evolution, and storyline revisions while maintaining sci-fi excellence.
</Scope>

<Source Content>
{source_content}
</Source Content>

<World State Context>
{world_state_context}
</World State Context>

<Setting Context>
This story is set in {target_year} as science fiction. All rewriting approaches must reflect this futuristic setting and maintain sci-fi genre conventions.
</Setting Context>

<Variation Examples>
Depending on the developed world content, explore (but do not be limited by) the following:
- Technology-immersive vs Character-psychology focused integration
- Different linguistic evolution emphases (vocabulary, syntax, cultural expressions)
- Varied world-building revelation strategies (subtle vs explicit world details)
- Distinct reader adaptation approaches (gradual vs immediate immersion)
</Variation Examples>

<Requirements>
- Each approach must seamlessly integrate the developed world-building
- Focus on how each approach immerses readers in the evolved world
- Consider linguistic evolution integration within each approach  
- Ensure authentic character behavior within the established world context
- Balance world integration with compelling narrative flow
</Requirements>

<Output Format>
Direction 1: [Name]
Core Assumption: [Technology-immersive/Character-focused/Linguistic-emphasis]
Focus: [How this approach integrates the developed world]

Direction 2: [Name] 
Core Assumption: [Technology-immersive/Character-focused/Linguistic-emphasis]
Focus: [How this approach integrates the developed world]

Reasoning: [Why these approaches create distinct integration strategies]
</Output Format>

<Sci-Fi Requirements>
Ensure all rewriting approaches maintain science fiction excellence for {target_year}:
- Strength of central "what if?" speculation and technological implications
- How effectively future technology shapes chapter content naturally
- Internal consistency of established sci-fi rules and world logic
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative, not dominates)
</Sci-Fi Requirements>

<Reminders>
- Focus on authentic integration that serves the story
- Each approach should create natural immersion in the established world
- Avoid exposition dumps, focus on authentic character behavior
- Consider how readers from this world would naturally experience the story
- Each approach should feel organic to the developed world context
- Maintain sci-fi genre authenticity for {target_year} setting
</Reminders>
"""

# === Narrative Structure Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "chapter_arcs_creation" and "chapter_arcs_adjustment" use cases
NARRATIVE_META_ANALYSIS_PROMPT = """You are an expert narrative architect tasked with identifying distinct chapter structure approaches.

<Task>
Create a compelling chapter-by-chapter arc structure for a science fiction novel set in {target_year}.
</Task>

<Scope>
Identify 2 fundamentally different approaches for structuring chapter arcs that create compelling narrative progression and maintain sci-fi excellence.
</Scope>

<Story Concept>
{story_concept}
</Story Concept>

<Source Content>
{source_content}
</Source Content>

<World State Context>
{world_state_context}
</World State Context>

<Setting Context>
This story is set in {target_year} as science fiction. All chapter arc approaches must reflect this futuristic setting and maintain sci-fi genre conventions.
</Setting Context>

<Variation Examples>
Depending on the story concept, explore (but do not be limited by) the following:
- Sequential vs Non-linear chapter progression
- Character-focused vs Plot-driven arc structures
- Different pacing strategies (accelerating tension vs steady buildup)
- Varied chapter purposes (action, reflection, world-building, character development)
- Distinct narrative momentum patterns
</Variation Examples>

<Requirements>
- Each approach must create a complete chapter structure
- Focus on how chapters build narrative momentum
- Consider character development across chapters
- Ensure thematic coherence throughout the structure
- Balance plot progression with character growth
</Requirements>

<Output Format>
Direction 1: [Name]
Core Assumption: [Sequential/Non-linear/Character-focused/Plot-driven approach]
Focus: [How this approach structures chapter progression and narrative flow]

Direction 2: [Name] 
Core Assumption: [Sequential/Non-linear/Character-focused/Plot-driven approach]
Focus: [How this approach structures chapter progression and narrative flow]

Reasoning: [Why these approaches offer distinct chapter structuring possibilities]
</Output Format>

<Sci-Fi Requirements>
Ensure all chapter arc approaches maintain science fiction excellence for {target_year}:
- Strength of central "what if?" speculation across chapter progression
- How effectively future technology shapes chapter narrative flow
- Internal consistency of established sci-fi rules throughout the arc
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative progression)
</Sci-Fi Requirements>

<Reminders>
- Focus on chapter-level structure, not scene-level details
- Consider how each chapter serves the overall narrative arc
- Think about reader engagement and pacing across chapters
- Avoid cliches, create unique structural approaches
- Each approach should feel natural and purposeful
- Maintain sci-fi genre authenticity for {target_year} setting
</Reminders>
"""

# === Linguistic Evolution Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "linguistic_evolution" use case
LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for linguistic evolution competition.

<Task>
Analyze the provided world context to identify 3 fundamentally different approaches to understanding linguistic evolution in this technological society by {target_year} (projecting {years_in_future} years forward).
</Task>

<World Context>
{source_content}
</World Context>

<Previous Research Context>
{world_state_context}
</Previous Research Context>

<Scope>
Identify 3 competing approaches to linguistic evolution research that would lead to meaningfully different insights about how language has developed in this technological context.
</Scope>

<Requirements>
- Linguistic plausibility: All directions must be grounded in real linguistic principles
- Comprehensive coverage: Each direction must address language evolution broadly, not focus on just one aspect
- Meaningful differentiation: Different core assumptions about how technology influences language
- Equal viability: Different but equally valid linguistic research approaches
- Technological implications: Consider impacts of AI, interfaces, social networks, automation, etc.
</Requirements>

<Key Constraints>
- Maintain linguistic rigor while exploring different possibilities
- Ensure each direction provides unique research opportunities
- Balance innovation with established sociolinguistic theory
- Create directions that are genuinely distinct, not variations of the same theme
</Key Constraints>

<Process>
1. Analyze the world context to identify key technological factors affecting language
2. Determine which linguistic processes could be influenced in fundamentally different ways
3. Create 3 distinct research directions based on different core assumptions about language change
4. Ensure each direction comprehensively addresses linguistic evolution in this context
5. Validate that directions are linguistically sound but meaningfully different
</Process>

<Output Format>
Direction 1: [Name]
Core Assumption: [Key assumption about how technology affects language]
Focus: [What this approach emphasizes about linguistic evolution]

Direction 2: [Name] 
Core Assumption: [Key assumption about how technology affects language]
Focus: [What this approach emphasizes about linguistic evolution]

Direction 3: [Name]
Core Assumption: [Key assumption about how technology affects language] 
Focus: [What this approach emphasizes about linguistic evolution]

Reasoning: [Explain why these 3 approaches provide meaningful variety while remaining linguistically grounded]
</Output Format>

<Reminders>
- Focus on linguistic change mechanisms that create meaningful differentiation
- Ensure all directions remain grounded in linguistic theory and evidence
- Address the complete technological context affecting language evolution
- Each direction should offer unique insights into language development patterns
</Reminders>
"""

# === Storyline Adjustment Meta-Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "storyline_adjustment" use case
STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT = """You are an expert narrative analyst from this advanced world identifying distinct approaches for adjusting storylines to integrate developed world-building.

<Task>
Revise storylines to seamlessly integrate developed world-building while maintaining narrative strength as science fiction set in {target_year}.
</Task>

<Scope>
Identify 2 fundamentally different approaches for adjusting storylines to integrate the developed world state while preserving narrative appeal and sci-fi authenticity.
</Scope>

<Source Content>
{source_content}
</Source Content>

<World State Context>
{world_state_context}
</World State Context>

<Setting Context>
This story is set in {target_year} as science fiction. All adjustments must reflect this futuristic setting and maintain sci-fi genre conventions.
</Setting Context>

<Variation Examples>
Depending on the developed world content, explore (but do not be limited by) the following:
- Technology-integrated vs Character-psychology focused adjustments
- Different world-building revelation strategies (gradual integration vs immediate context)
- Varied narrative adaptation approaches (plot-driven vs character-driven changes)
- Distinct cultural evolution emphases (social, linguistic, technological)
</Variation Examples>

<Requirements>
- Each approach must seamlessly integrate the developed world-building
- Focus on how each approach maintains narrative strength while enhancing world immersion
- Consider authentic character behavior within the established world context
- Ensure storyline adjustments feel natural and purposeful  
- Balance world integration with compelling narrative progression
</Requirements>

<Output Format>
Direction 1: [Name]
Core Assumption: [Technology-integrated/Character-focused/Cultural-emphasis]
Focus: [How this approach adjusts storylines for world integration]

Direction 2: [Name] 
Core Assumption: [Technology-integrated/Character-focused/Cultural-emphasis]
Focus: [How this approach adjusts storylines for world integration]

Reasoning: [Why these approaches create distinct adjustment strategies]
</Output Format>

<Sci-Fi Requirements>
Ensure all approaches maintain science fiction excellence for {target_year}:
- Strength of central "what if?" speculation and technological speculation
- How effectively future technology shapes world/characters naturally
- Internal consistency of established sci-fi rules and world logic
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative, not dominates)
</Sci-Fi Requirements>

<Reminders>
- Focus on adjustment strategies that serve both story and world-building
- Each approach should create authentic immersion in the established world
- Consider how storyline changes feel natural to inhabitants of this world
- Avoid forced integration, focus on organic narrative evolution
- Each approach should enhance rather than constrain narrative possibilities
- Maintain sci-fi genre authenticity for {target_year} setting
</Reminders>
""" 