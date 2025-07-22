# Co-Scientist Competition Prompts
# Following the methodology from Google's AI co-scientist paper
# Enhanced with templates for different use cases

# === Template Management Functions ===

def get_meta_analysis_prompt(use_case: str, state: dict, config: dict = None) -> str:
    """Get the appropriate meta-analysis prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_META_ANALYSIS_PROMPT,
        "storyline_creation": STORYLINE_META_ANALYSIS_PROMPT,
        "chapter_writing": CHAPTER_WRITING_META_ANALYSIS_PROMPT,
        "chapter_rewriting": CHAPTER_META_ANALYSIS_PROMPT,

        "linguistic_evolution": LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT,
        "storyline_adjustment": STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT,
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
    elif use_case == "chapter_rewriting":
        params["source_content"] = state.get("reference_material", "")
    else:
        # For other use cases, keep generic context
        params["context"] = context_value
        params["source_content"] = state.get("reference_material", "")
    
    return template.format(**params)

def get_generation_prompt(use_case: str, state: dict, direction: dict, team_id: str, config: dict = None) -> str:
    """Get the appropriate generation prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_SCENARIO_GENERATION_PROMPT,
        "storyline_creation": STORYLINE_GENERATION_PROMPT,
        "chapter_writing": CHAPTER_WRITING_GENERATION_PROMPT,
        "chapter_rewriting": CHAPTER_GENERATION_PROMPT,

        "linguistic_evolution": LINGUISTIC_EVOLUTION_GENERATION_PROMPT,
        "storyline_adjustment": STORYLINE_ADJUSTMENT_GENERATION_PROMPT,
    }
    
    template = templates.get(use_case)
    if not template:
        raise ValueError(f"No template found for use_case: {use_case}")
    
    # Extract world state context from config if available
    world_state_context = ""
    if config and config.get("configurable"):
        world_state_context = config["configurable"].get("world_state_context", "")
    
    # Handle scenario generation with proper template format
    if use_case == "scenario_generation":
        return template.format(
            research_direction=direction.get("name", ""),
            core_assumption=direction.get("assumption", ""),
            team_id=team_id,
            research_context=state.get("research_context", state.get("context", "")),
            storyline=state.get("storyline", ""),
            target_year=state.get("target_year", "future")
        )
    
    # Create base parameters for flexible format
    params = {
        "direction_name": direction.get("name", ""),
        "direction_assumption": direction.get("assumption", ""),
        "team_id": team_id,
        "source_content": state.get("reference_material", ""),
        "world_state_context": world_state_context
    }
    
    # Add use-case specific context parameters
    context_value = state.get("context", "")
    if use_case == "chapter_writing":
        params["storyline"] = state.get("storyline", "")
        params["chapter_arcs"] = state.get("chapter_arcs", "")
    elif use_case == "storyline_creation":
        params["story_concept"] = context_value
    elif use_case == "linguistic_evolution":
        params["research_context"] = context_value
    elif use_case == "storyline_adjustment":
        pass  # No context needed, instructions are embedded in prompt
    elif use_case == "chapter_rewriting":
        pass  # No context needed, instructions are embedded in prompt
    else:
        # For other use cases, keep generic context
        params["context"] = context_value
    
    return template.format(**params)

# === Meta-Analysis Phase ===

# Used in: get_meta_analysis_prompt() for "scenario_generation" use case
INITIAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for scenario competition.

<Task>
Analyze the provided story context and world-building questions to identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures for {target_year}.
</Task>

<Storyline>
{storyline}
</Storyline>

<World-Building Questions>
{world_building_questions}
</World-Building Questions>

<Scope>
Analyze the provided world-building questions to identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures for this science fiction world-building scenario.
</Scope>

<Requirements>
- Scientific plausibility: All directions must be grounded in real scientific principles
- Comprehensive coverage: Each direction must address ALL questions in the context, not focus on just one aspect
- Meaningful differentiation: Different core assumptions about technological development paths
- Equal viability: Different but equally plausible scientific trajectories
- Societal implications: Consider impacts on society, energy, transport, communication, governance, etc.
</Requirements>

<Key Constraints>
- Maintain scientific rigor while exploring different possibilities
- Ensure each direction provides unique storytelling opportunities
- Balance innovation with plausibility
- Create directions that are genuinely distinct, not variations of the same theme
</Key Constraints>

<Process>
1. Analyze the context to identify key technological and scientific choice points
2. Determine which technologies/approaches could develop in fundamentally different directions
3. Create 3 distinct research directions based on different core assumptions
4. Ensure each direction comprehensively addresses all questions in the context
5. Validate that directions are scientifically plausible but meaningfully different
</Process>

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

<Current Baseline World State>
{baseline_world_state}
</Current Baseline World State>

<Years to Project Forward>
{years_in_future}
</Years to Project Forward>

<Instructions>
1. Analyze the current baseline world state to understand existing systems and trends
2. Identify key evolutionary choice points that could develop in different directions over {years_in_future} years
3. Create 3 distinct research directions based on different assumptions about which evolutionary paths will dominate
4. Ensure each direction builds logically on the baseline while representing different evolutionary trajectories
5. Each direction should address ALL the world-building questions, showing evolution across all systems

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

# === Scenario Generation Phase ===

# Used in: get_generation_prompt() for "scenario_generation" use case (initial scenarios)
INITIAL_SCENARIO_GENERATION_PROMPT = """You are a research team conducting rigorous scientific analysis to develop a comprehensive world-building scenario for the target year.

<Research Direction>
{research_direction}
</Research Direction>

<Core Assumption>
{core_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<World-Building Questions to Address>
{research_context}
</World-Building Questions to Address>

<Story Context>
{storyline}
</Story Context>

<Target Year>
{target_year}
</Target Year>

<Task>
Develop a complete scenario that addresses ALL the world-building questions while maintaining scientific rigor and internal consistency.
</Task>

<Requirements>
- Scientifically grounded in current research
- Internally consistent across all systems
- Specific enough for narrative development
- Realistic about technological timelines
- Aware of social and economic implications
</Requirements>

<Process>
1. Conduct deep research on current scientific trends that support your core assumption
2. Ground every technological claim in current research or plausible extrapolation
3. Maintain internal consistency across all aspects of the world
4. Consider second-order effects and systemic implications
</Process>

<Scope>
Your scenario must address the world-building questions provided in the context.
</Scope>

<Research Methodology>
- Start with your core assumption as the foundation
- Research current scientific literature supporting this path
- Extrapolate realistically to the target year
- Consider implementation challenges and timelines
- Address potential obstacles and how they're overcome
</Research Methodology>

<Reminders>
- Ground every claim in current scientific research or plausible extrapolation
- Maintain internal consistency across all technological and social systems
- Consider realistic timelines for technological development and social adaptation
</Reminders>
"""

# Used in: generate_single_scenario() for scenario generation with baseline world state
INCREMENTAL_SCENARIO_GENERATION_PROMPT = """You are a research team conducting rigorous scientific analysis to project how the world will evolve from an established baseline state.

<Research Direction>
{research_direction}
</Research Direction>

<Core Assumption>
{core_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<World-Building Questions to Address>
{research_context}
</World-Building Questions to Address>

<Story Context>
{storyline}
</Story Context>

<Current Baseline World State>
{baseline_world_state}
</Current Baseline World State>

<Years to Project Forward>
{years_in_future}
</Years to Project Forward>

<Task>
Project evolutionary changes that build logically on the established baseline while maintaining scientific rigor and consistency.
</Task>

<Instructions>
1. Analyze the current baseline world state to understand the starting point
2. Apply your research direction's core assumption to project forward {years_in_future} years
3. Ground every technological claim in current research or plausible extrapolation
4. Maintain consistency with the established world while showing realistic progression

Your scenario must show evolution in regards to the world-building questions provided in the context.

Research Methodology:
- Start with the baseline world state as your foundation
- Apply your core assumption to drive the evolution forward
- Research current scientific literature supporting this evolutionary path
- Consider how existing systems would realistically adapt and change
- Address implementation challenges and transition timelines

Generate a comprehensive evolutionary scenario that is:
- Built logically on the established baseline
- Scientifically grounded in current research
- Internally consistent with both baseline and projections
- Specific enough for narrative development
- Realistic about technological and social evolution timelines
</Instructions>
"""

# === Storyline and Chapter Templates ===

# Used in: get_meta_analysis_prompt() for "storyline_creation" use case
STORYLINE_META_ANALYSIS_PROMPT = """You are a master storyteller tasked with identifying distinct storyline approaches.

<Task>
Create a compelling storyline for a novel.
</Task>

<Scope>
Identify 2 fundamentally different approaches for creating a compelling storyline.
</Scope>

<Story Concept>
{story_concept}
</Story Concept>

<Variation examples>
Depending on the story concept, explore (but do not be limited by) the following:
- Character-driven vs Plot-driven approaches
- Different structural frameworks (linear, non-linear, multiple POV, etc.)
- Distinct thematic emphasis and emotional tone
- Varied pacing and narrative tension strategies
</Requirements>

<Output Format>
Direction 1: [Name] 
Core Assumption: [Character-driven/Plot-driven/Structure focus]
Focus: [Narrative emphasis and approach]

Direction 2: [Name]
Core Assumption: [Character-driven/Plot-driven/Structure focus] 
Focus: [Narrative emphasis and approach]

Reasoning: [Why these approaches offer distinct storyline possibilities]
</Output Format>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
</Reminders>
"""

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

# Used in: get_generation_prompt() for "storyline_creation" use case
STORYLINE_GENERATION_PROMPT = """You are a master storyteller creating a compelling storyline using the {direction_name} approach.

<Approach>
{direction_assumption}
</Approach>

<Story Concept>
{story_concept}
</Story Concept>

<Task>
Create a complete storyline that follows your narrative approach and brings the story concept to life.
</Task>

<Requirements>
- Complete narrative arc with beginning, middle, end
- Compelling protagonist and supporting characters  
- Central conflict and meaningful resolution
- Appropriate pacing for your chosen approach
- Clear thematic foundation
</Requirements>

<Storyline Must Include>
- Protagonist introduction and motivation
- Inciting incident and central conflict
- Key plot points and turning moments
- Character relationships and development
- Climactic resolution and conclusion

Create a compelling, complete storyline that exemplifies your narrative approach.

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
</Reminders>
"""

# Used in: get_generation_prompt() for "chapter_writing" use case  
CHAPTER_WRITING_GENERATION_PROMPT = """You are a skilled novelist writing an engaging first chapter using the {direction_name} approach.

<Approach>
{direction_assumption}
</Approach>

<Storyline>
{storyline}
</Storyline>

<Chapter Structure>
{chapter_arcs}
</Chapter Structure>

<Writing Instructions>
The opening should immediately engage readers and set up the story elements naturally.
</Writing Instructions>

<Task>
Write a complete first chapter that hooks readers and launches the story using your chosen approach.
</Task>

<Chapter Must Accomplish>
- Hook readers immediately with compelling opening
- Establish protagonist voice and perspective
- Introduce setting and story world naturally
- Set up central conflict or tension
- Create strong atmosphere and tone
</Chapter Must Accomplish>

<Writing Requirements>
- Vivid scene-setting and character introduction
- Natural dialogue that reveals character
- Balanced pacing appropriate to your approach
- Strong opening hook and chapter-ending momentum
- Authentic voice and engaging prose style

Write a complete, compelling first chapter that exemplifies your chosen approach.

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Chapter Rewriting Templates ===

# Used in: get_meta_analysis_prompt() for "chapter_rewriting" use case
CHAPTER_META_ANALYSIS_PROMPT = """You are an expert literary analyst tasked with identifying distinct approaches for rewriting a chapter to fully integrate developed world-building.

<Task>
Rewrite the first chapter to fully integrate the developed world-building, linguistic evolution, and narrative revisions.
</Task>

<Scope>
Identify 2 fundamentally different approaches for rewriting the chapter to seamlessly integrate the developed world state, linguistic evolution, and storyline revisions.
</Scope>

<Current Chapter>
{source_content}
</Current Chapter>

<Chapter Rewriting Requirements>
Completely rewrite the opening chapter to seamlessly incorporate all the world-building, linguistic evolution, and storyline developments. The rewritten chapter should feel natural and immersive, using the evolved language and cultural elements while maintaining strong narrative pacing and character development.
</Chapter Rewriting Requirements>

<World State Context>
{world_state_context}
</World State Context>

<Requirements>
- World Integration: weave world-building naturally into the narrative
- Linguistic Consistency: incorporate evolved language and cultural elements
- Character Authenticity: characters behave within the established world constraints
- Immersion Strategy: immerse readers in the developed world without exposition dumps
</Requirements>

<Key Constraints>
- Maintain narrative flow while incorporating complex world-building
- Balance world detail with character development and plot progression
- Ensure linguistic evolution feels natural and authentic to the world
- Create reader immersion without overwhelming with information
</Key Constraints>

<Process>
1. Analyze how the current chapter can be enhanced with world-building integration
2. Create 2 distinct approaches for weaving world elements into the narrative
3. Focus on different strategies for linguistic integration and world immersion
</Process>

<Output Format>
Direction 1: [Name]
Core Assumption: [World integration strategy]
Focus: [How this approach integrates world-building into the chapter]

Direction 2: [Name] 
Core Assumption: [World integration strategy]
Focus: [How this approach integrates world-building into the chapter]

Reasoning: [Why these approaches offer distinct methods for world-building integration]
</Output Format>

<Reminders>
- This is about rewriting to integrate developed world state, not generic chapter improvement
- Focus on world-building integration strategies, not just narrative techniques  
- Consider how linguistic evolution and cultural elements enhance the story
- Each approach should create authentic immersion in the established world
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# Used in: get_generation_prompt() for "chapter_rewriting" use case
CHAPTER_GENERATION_PROMPT = """You are a skilled science fiction writer rewriting a chapter to seamlessly integrate developed world-building using the {direction_name} approach.

<Integration Approach>
{direction_assumption}
</Integration Approach>

<Original Chapter>
{source_content}
</Original Chapter>

<Rewriting Requirements>
Completely rewrite the opening chapter to seamlessly incorporate all the world-building, linguistic evolution, and storyline developments. The rewritten chapter should feel natural and immersive, using the evolved language and cultural elements while maintaining strong narrative pacing and character development.
</Rewriting Requirements>

<Developed World State>
{world_state_context}
</Developed World State>

<Task>
Completely rewrite the chapter to naturally integrate the established world-building, linguistic evolution, and technological developments. Write for readers who live in this future world and naturally understand these concepts.
</Task>

<World Integration Requirements>
- Seamlessly weave world technologies and systems into character actions and dialogue
- Use evolved language and cultural expressions naturally, without explanation
- Show characters interacting authentically with their world's systems and norms
- Integrate world-specific details through character perspective, not exposition
- Assume readers understand this world - don't explain basic concepts
</World Integration Requirements>

<Writing Approach>
- Characters think, speak, and act as natives of this developed world
- Technology and systems are background reality, not novelties to explain
- Linguistic evolution is natural speech, not foreign terms requiring definition
- Cultural and social norms are assumed knowledge, shown through behavior
- World details emerge through authentic character interaction with their environment
</Writing Approach>

<Key Principles>
- NO explaining concepts as if to readers from the past
- NO exposition dumps about how the world works  
- YES authentic character behavior within established world systems
- YES natural use of evolved language and cultural elements
- YES seamless integration where world-building serves story, not vice versa
</Key Principles>

Rewrite the complete chapter as a natural story within this established world.

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Research and Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "linguistic_evolution" use case
LINGUISTIC_EVOLUTION_META_ANALYSIS_PROMPT = """You are an expert linguist exploring how language has evolved in this advanced technological society.

Your task: Examine linguistic evolution by {target_year} (projecting {years_in_future} years forward) and propose research approaches for understanding language development.

<world_context>
{source_content}
</world_context>

<previous_findings>
{world_state_context}
</previous_findings>

Investigate how language, communication, and social linguistics have evolved in this context. Consider any factors that may have influenced linguistic development - technological, social, cultural, generational, or other patterns you discover.

Build upon previous research while exploring new directions. Focus on what's actually observable in this documented world.

Propose research approaches that would provide meaningful insights. Structure your response however makes most sense - you might suggest 2-4 different approaches, methodologies, or investigative directions.

For each approach, explain:
- What it would investigate
- How you'd conduct the research  
- Why it would be valuable
- How it builds on or extends previous work

Let your analysis emerge naturally from the evidence rather than forcing predetermined categories. Consider unexpected factors and propose approaches that feel authentic to this specific world context."""

# Used in: get_generation_prompt() for "linguistic_evolution" use case
LINGUISTIC_EVOLUTION_GENERATION_PROMPT = """You are a linguistic research team from this advanced technological world analyzing how language has evolved using the {direction_name} approach.

<Research Approach>
{direction_assumption}
</Research Approach>

<Current World State>
{source_content}
</Current World State>

<Research Requirements>
Research how language, communication methods, cultural expression, and social linguistics evolve given the technological and societal changes described in the world state. Focus on projecting linguistic evolution through technological and social developments.
</Research Requirements>

<Previous Linguistic Research>
{world_state_context}
</Previous Linguistic Research>

<Task>
Project how language, communication, and cultural expression naturally evolved in our technological society. Research for fellow inhabitants of this world who understand these systems.
</Task>

<Evolution Analysis Focus>
- Natural language adaptation to integrated technological systems
- Communication efficiency patterns within established social structures  
- Cultural expression evolution reflecting our society's values and norms
- Generational linguistic inheritance and innovation patterns
- Cross-cultural communication within our global technological framework
- Semantic evolution reflecting concepts native to our technological reality
</Evolution Analysis Focus>

<Research Approach>
- Document natural linguistic evolution within established world systems
- Project from current technological and social trajectories we understand
- Build upon previous research cycles if available from earlier projections
- Analyze communication patterns as they naturally developed in this world
- Account for linguistic adaptation as normal response to technological integration
- Consider both gradual evolution and disruption as natural processes
</Research Approach>

<Key Principles>
- document natural language evolution within established world reality
- build upon previous linguistic research as cumulative understanding
- present evolution as natural adaptation, not revolutionary change
</Key Principles>

Research how language naturally evolved in our technological society with specific projections, timelines, and examples of evolved language elements as they naturally exist.
"""

# === Narrative Revision Templates ===

# Used in: get_meta_analysis_prompt() for "storyline_adjustment" use case  
STORYLINE_ADJUSTMENT_META_ANALYSIS_PROMPT = """You are an expert narrative analyst from this advanced world identifying distinct approaches for adjusting storylines to integrate developed world-building.

<Task>
Revise and enhance the storyline to integrate world-building developments and linguistic evolution.
</Task>

<Scope>
Identify 2 fundamentally different approaches for revising the storyline to seamlessly integrate our newly developed world state, linguistic evolution, and technological developments.
</Scope>

<Original Storyline>
{source_content}
</Original Storyline>

<Storyline Adjustment Requirements>
Adjust the original storyline to incorporate the detailed world-building and linguistic evolution that has been developed. The revised storyline should seamlessly integrate new technological, social, and cultural developments while maintaining narrative coherence and character consistency.
</Storyline Adjustment Requirements>

<Developed World State>
{world_state_context}
</Developed World State>

<Requirements>
- World Integration: How to weave developed world-building naturally into the narrative structure
- Character Consistency: How to maintain character authenticity within the evolved world context
- Plot Coherence: How to adjust plot elements to align with established world systems
- Thematic Enhancement: How to strengthen themes through world-building integration
- Narrative Flow: How to maintain story momentum while incorporating developed world elements
</Requirements>

<Key Constraints>
- Preserve original storyline's core narrative appeal and essence
- Seamlessly integrate world developments without disrupting story flow
- Ensure characters and plot elements are authentic to the developed world
- Maintain reader engagement while incorporating complex world-building
</Key Constraints>

<Process>
1. Analyze how the original storyline can be enhanced with developed world integration
2. Create 2 distinct approaches for weaving world elements into the narrative structure
3. Focus on different strategies for character, plot, and thematic integration
</Process>

<Output Format>
Direction 1: [Name]
Core Assumption: [World integration strategy]
Focus: [How this approach integrates developed world into storyline]

Direction 2: [Name] 
Core Assumption: [World integration strategy]
Focus: [How this approach integrates developed world into storyline]

Reasoning: [Why these approaches offer distinct methods for world-building integration]
</Output Format>

<Reminders>
- This is about adjusting storyline to integrate our developed world state, not generic revision
- Focus on world-building integration strategies, not just narrative techniques
- Consider how our linguistic evolution and cultural elements enhance the story
- Each approach should create authentic integration with our established world
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
</Reminders>
"""

# Used in: get_generation_prompt() for "storyline_adjustment" use case
STORYLINE_ADJUSTMENT_GENERATION_PROMPT = """You are a narrative development team from this advanced world revising storylines to integrate our developed world-building using the {direction_name} approach.

<Integration Approach>
{direction_assumption}
</Integration Approach>

<Original Storyline>
{source_content}
</Original Storyline>

<Adjustment Requirements>
Adjust the original storyline to incorporate the detailed world-building and linguistic evolution that has been developed. The revised storyline should seamlessly integrate new technological, social, and cultural developments while maintaining narrative coherence and character consistency.
</Adjustment Requirements>

<Developed World State>
{world_state_context}
</Developed World State>

<Task>
Revise the original storyline to seamlessly integrate our developed world state, linguistic evolution, and technological systems. Adjust for inhabitants of this world who naturally understand these developments.
</Task>

<World Integration Requirements>
- Seamlessly weave developed world-building and linguistic evolution into narrative structure and character actions
- Ensure characters think and act authentically within our established world systems
- Adjust plot elements to align with our technological and social realities
- Preserve storyline's core appeal while enhancing it with our world developments
</World Integration Requirements>

<Adjustment Approach>
- Characters inhabit and understand our developed world naturally
- Technological and social systems are background reality, not foreign concepts
- Our linguistic evolution is natural speech, not terms requiring explanation
- Cultural and social developments are assumed knowledge, shown through behavior
- World details enhance story flow rather than interrupting it
</Adjustment Approach>

<Key Principles>
- NO explaining world developments as if to readers from the past
- NO treating our advanced systems as foreign or requiring definition
- YES authentic character behavior within our established world systems
- YES natural integration of our linguistic and cultural evolution
- YES seamless enhancement where world-building serves story development
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
</Key Principles>

Revise the complete storyline as a natural story enhanced by our developed world elements.
"""

# === Expert Reflection Phase ===

# Used in: generate_domain_critique() function for scientific analysis of scenarios
DOMAIN_CRITIQUE_PROMPT = """You are a {critique_domain} expert providing rigorous scientific critique of a world-building scenario.

<Scenario ID>
{scenario_id}
</Scenario ID>

<Research Direction>
{research_direction}
</Research Direction>

<Scenario to Critique>
{scenario_content}
</Scenario to Critique>

<Your Expertise>
{critique_domain}
</Your Expertise>

<Task>
Evaluate this scenario specifically from your domain expertise and provide rigorous scientific critique.
</Task>

<Evaluation Criteria>
- Scientific accuracy and plausibility
- Realistic timelines for technological development
- Consideration of fundamental constraints within your domain
- Internal consistency within your domain
</Evaluation Criteria>

<Process>
1. Identify scientific inaccuracies, implausible claims, or logical inconsistencies
2. Assess whether the technological timelines are realistic
3. Consider if the scenario accounts for known constraints in your field
4. Suggest specific improvements to make the scenario more scientifically sound
</Process>

<Output Requirements>
Provide:
1. Overall assessment of scientific rigor in your domain
2. Specific issues identified with detailed explanations
3. Suggestions for improvement
4. Severity score (1-10) where 10 = major scientific problems that invalidate the scenario
</Output Requirements>

<Reminders>
- Focus specifically on your domain expertise: {critique_domain}
- Provide constructive, evidence-based feedback
- Consider both current limitations and realistic future developments
</Reminders>
"""

# Used in: generate_world_aware_critique() function for evaluating world integration in narrative content
WORLD_INTEGRATION_CRITIQUE_PROMPT = """You are a {critique_domain} expert providing detailed analysis of how well narrative content integrates with the established world-building.

<Content ID>
{scenario_id}
</Content ID>

<Content Type>
{content_type}
</Content Type>

<Content to Evaluate>
{scenario_content}
</Content to Evaluate>

<Established World State>
{world_state_context}
</Established World State>

<Your Expertise>
{critique_domain}
</Your Expertise>

<Task>
Evaluate how well the narrative content integrates with and reflects the established world-building, focusing on consistency, authenticity, and immersion.
</Task>

<Evaluation Criteria>
- World consistency: Does the content align with established world rules and systems?
- Authenticity: Do world elements feel natural and integrated rather than forced?
- Detail integration: Are specific world-building details properly reflected?
- Cultural consistency: Are social, linguistic, and cultural elements authentic to the world?
- Immersion quality: Does the content successfully immerse readers in the established world?
</Evaluation Criteria>

<Process>
1. Assess how accurately the content reflects the established world state
2. Identify inconsistencies between the content and the world-building
3. Evaluate whether the content uses world elements naturally and authentically
4. Check if linguistic evolution and cultural elements are properly integrated
5. Assess reader immersion and believability within the established world
</Process>

<Output Requirements>
Provide:
1. Overall assessment of world integration quality
2. Specific consistency issues or missed opportunities
3. Suggestions for better world integration
4. Integration score (1-10) where 10 = perfect world integration
5. Most effective world integration elements in the content
</Output Requirements>

<Reminders>
- Focus on how well the content serves the established world
- Look for both consistency and authentic integration of world elements
- Consider the reader's immersive experience within the world
</Reminders>
"""

# === Tournament Competition Phase ===

# Used in: pairwise_comparison() function for head-to-head scenario tournaments
PAIRWISE_RANKING_PROMPT = """You are an expert in comparative analysis, simulating a panel of domain experts engaged in structured discussion to evaluate two competing world-building scenarios.

<Task>
Rigorously determine which scenario is superior based on scientific grounding and narrative potential.
</Task>

<Goal>
Select the most scientifically rigorous and compelling scenario for sci-fi world-building
</Goal>

<Scenario 1>
{scenario1_content}
Research Direction: {direction1}
</Scenario 1>

<Scenario 2>
{scenario2_content}
Research Direction: {direction2}
</Scenario 2>

<Evaluation Criteria>
- Scientific plausibility and evidence grounding
- Internal consistency across all systems  
- Realistic technological timelines
- Consideration of second-order effects
- Detail richness
</Evaluation Criteria>

<Process>
The discussion will unfold in 3-5 structured turns:

Turn 1: Begin with a concise summary of both scenarios and their core approaches
Subsequent turns:
- Critically evaluate each scenario against the stated criteria
- Compare scientific rigor and evidence grounding
- Assess internal consistency and logical coherence
- Identify specific strengths and weaknesses
</Process>

<Evaluation Aspects>
- Potential for scientific correctness/validity
- Practical applicability and implementation feasibility
- Sufficiency of detail and specificity
- Novelty and originality
</Evaluation Aspects>

<Output Format>
Conduct the structured discussion analysis, then provide a conclusive judgment with clear rationale.

Then indicate the superior scenario by writing: "better scenario: 1" or "better scenario: 2"
</Output Format>

<Reminders>
- Provide thorough comparative analysis before making a decision
- Focus on scientific rigor
- Give clear reasoning for your final judgment
</Reminders>
"""

# === Final Meta-Review Phase ===

# Used in: final_meta_review_phase() function for process analysis and optimization insights
META_REVIEW_PROMPT = """You are a meta-review agent analyzing the co-scientist competition process to synthesize insights and optimize future performance.

<Competition Process Data>
{competition_summary}
</Competition Process Data>

<Tournament Results from Each Direction>
{direction_winners_summary}
</Tournament Results from Each Direction>

<Competition Process Analysis>
{tournament_data}
{reflection_data}
{evolution_data}
</Competition Process Analysis>

<Task>
Synthesize insights from all reviews and competition phases to optimize future performance and provide comprehensive process analysis.
</Task>

<Your Role as Meta-Review Agent>
1. Synthesize insights from all reviews and competition phases
2. Identify recurring patterns in tournament debates and agent performance
3. Analyze the effectiveness of different approaches and methodologies
4. Generate optimization recommendations for subsequent iterations
5. Create a comprehensive research overview of the competition process
</Your Role as Meta-Review Agent>

<Process Analysis Framework>
- Competition methodology effectiveness
- Quality patterns across different approaches
- Agent performance and decision-making patterns
- Tournament reasoning quality and consistency
- Areas for process improvement and optimization
</Process Analysis Framework>

<Output Requirements>
Generate a comprehensive process analysis covering:

## Competition Process Effectiveness
[Analyze how well the competition methodology worked]

## Recurring Patterns in Tournament Debates  
[Identify patterns in how different approaches were evaluated and compared]

## Agent Performance Analysis
[Evaluate how well different agent types performed their roles]

## Quality Optimization Insights
[Recommendations for improving future competition quality]

## Research Overview Summary
[Comprehensive overview of the competition process and methodology for research purposes]
</Output Requirements>

<Key Constraints>
DO NOT select winners - that is for user choice. Focus on process synthesis.
</Key Constraints>

<Reminders>
- Focus on process optimization and methodological insights
- Analyze patterns across all phases of the competition
- Provide actionable recommendations for future improvements
</Reminders>
"""

