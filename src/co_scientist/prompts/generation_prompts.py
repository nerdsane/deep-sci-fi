# Generation Phase Prompts
# Following the methodology from Google's AI co-scientist paper

import uuid
from datetime import datetime


def get_uniqueness_seed() -> str:
    """Generate a unique seed to ensure fresh content generation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"FRESH_RUN_{timestamp}_{unique_id}"


def get_generation_prompt(use_case: str, state: dict, direction: dict, team_id: str, config: dict = None) -> str:
    """Get the appropriate generation prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_SCENARIO_GENERATION_PROMPT,
        "storyline_creation": STORYLINE_GENERATION_PROMPT,
        "chapter_writing": CHAPTER_WRITING_GENERATION_PROMPT,
        "chapter_rewriting": CHAPTER_GENERATION_PROMPT,
        "chapter_arcs_creation": NARRATIVE_GENERATION_PROMPT,
        "chapter_arcs_adjustment": CHAPTER_ARCS_ADJUSTMENT_PROMPT,
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
        "world_state_context": world_state_context,
        "target_year": state.get("target_year", "future"),  # Add target year for sci-fi context
        "uniqueness_seed": get_uniqueness_seed()  # Inject uniqueness to prevent repetition
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
    elif use_case == "chapter_arcs_adjustment":
        params["context"] = context_value  # User's original story concept for context
        # source_content will contain the original chapter arcs to refine
    else:
        # For other use cases, keep generic context
        params["context"] = context_value
    
    return template.format(**params)


# === Scenario Generation Templates ===

# Used in: get_generation_prompt() for "scenario_generation" use case (initial scenarios)
INITIAL_SCENARIO_GENERATION_PROMPT = """You are a research team developing a comprehensive world-building scenario for {target_year}.

<Research Direction>
{research_direction}
</Research Direction>

<Core Assumption>
{core_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<World-Building Questions>
{research_context}
</World-Building Questions>

<Story Context>
{storyline}
</Story Context>

Develop a complete scenario addressing ALL world-building questions with scientific rigor and internal consistency.

<Requirements>
- Grounded in current research with realistic timelines
- Internally consistent across all systems
- Specific enough for narrative development
- Consider social and economic implications

<Process>
1. Research current scientific trends supporting your core assumption
2. Extrapolate realistically to target year considering implementation challenges
3. Address potential obstacles and solutions
</Process>

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

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Evolution Questions>
{research_context}
</Evolution Questions>

<Years in Future>
{years_in_future}
</Years in Future>

Develop a realistic projection showing how the world evolves from the baseline state over {years_in_future} years based on your core assumption.

<Requirements>
- Build logically on the established baseline world state
- Ground all changes in current scientific research or plausible extrapolation
- Consider realistic timelines for the specified {years_in_future}-year projection period
- Address implementation challenges and pathways
- Maintain internal consistency with the baseline
- Consider second-order effects and systemic implications

<Process>
1. Analyze the baseline to identify key systems and trends
2. Research current scientific literature supporting your evolutionary path
3. Model realistic progression over {years_in_future} years
4. Consider implementation challenges and adaptation timelines
5. Address potential obstacles and how they're overcome

<Reminders>
- This is an EVOLUTION from a baseline, not a complete reimagining
- Focus on realistic change trajectories over {years_in_future} years
- Every change must be justifiable within the timeframe
- Maintain consistency with established baseline systems
- Consider both technological and social adaptation rates
</Reminders>
"""

# === Storyline Generation Templates ===

# Used in: get_generation_prompt() for "storyline_creation" use case
STORYLINE_GENERATION_PROMPT = """You are a master storyteller creating a fresh, original storyline using the {direction_name} approach.

<Approach>
{direction_assumption}
</Approach>

<Story Concept>
{story_concept}
</Story Concept>

Create a complete storyline that follows your narrative approach and brings the story concept to life.

<Requirements>
- Complete narrative arc with beginning, middle, end
- Compelling protagonist and supporting characters  
- Central conflict and meaningful resolution
- Appropriate pacing for your chosen approach
- Story should be set in today's world
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
- Use creative, original character names - avoid common or repetitive names.
- Each character should have a distinct, memorable name that fits the story world.
- Create completely original company/organization names - never reuse previous names.
</Reminders>
"""

# === Chapter Writing Templates ===

# Used in: get_generation_prompt() for "chapter_writing" use case  
CHAPTER_WRITING_GENERATION_PROMPT = """You are a skilled novelist writing a fresh, original first chapter using the {direction_name} approach.

<Approach>
{direction_assumption}
</Approach>

<Storyline>
{storyline}
</Storyline>

<Chapter Structure>
{chapter_arcs}
</Chapter Structure>

Write a complete first chapter that hooks readers and launches the story. The opening should immediately engage readers and set up story elements naturally.

<Requirements>
- Hook readers with compelling opening
- Establish protagonist voice and perspective
- Introduce setting and world naturally
- Set up central conflict or tension
- Vivid scene-setting and natural dialogue
- Strong opening hook and chapter-ending momentum
</Requirements>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
- Use creative, original character names - avoid common or repetitive names.
- Each character should have a distinct, memorable name that fits the story world.
- Create completely original company/organization names - never reuse previous names.
</Reminders>
"""

# === Chapter Rewriting Templates ===

# Used in: get_generation_prompt() for "chapter_rewriting" use case
CHAPTER_GENERATION_PROMPT = """You are a skilled science fiction writer rewriting a chapter using the {direction_name} approach.

<Integration Approach>
{direction_assumption}
</Integration Approach>

<Original Chapter>
{source_content}
</Original Chapter>

<Developed World State>
{world_state_context}
</Developed World State>

Completely rewrite the chapter to naturally integrate world-building, linguistic evolution, and technological developments. Write for readers who live in this future world.

<Requirements>
- Seamlessly weave world technologies into character actions and dialogue
- Use evolved language naturally, without explanation
- Characters act as natives of this developed world
- Technology and systems are background reality, not novelties
- NO exposition dumps about how the world works
- Show, don't tell - world emerges through authentic character interaction

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Narrative Structure Templates ===

# Used in: get_generation_prompt() for "chapter_arcs_creation" and "chapter_arcs_adjustment" use cases
NARRATIVE_GENERATION_PROMPT = """You are a master narrative architect creating a complete chapter-by-chapter structure using the {direction_name} approach.

<Approach>
{direction_assumption}
</Approach>

<Story Concept>
{context}
</Story Concept>

<Source Content>
{source_content}
</Source Content>

<World State Context>
{world_state_context}
</World State Context>

Create a detailed chapter-by-chapter arc structure that follows your narrative approach and serves the story concept.

<Requirements>
- Complete chapter progression from beginning to end
- Clear purpose and focus for each chapter
- Logical narrative flow and pacing
- Character development milestones across chapters
- Plot progression that builds to climax
- Thematic consistency throughout structure
</Requirements>

<Chapter Arc Must Include>
- Chapter-by-chapter breakdown with clear purposes
- Key plot points and turning moments placement
- Character development beats across chapters
- Pacing strategy and tension/release patterns
- Thematic elements woven throughout structure
- Climactic buildup and resolution placement

Create a compelling, complete chapter arc structure that exemplifies your narrative approach.

<Critical Constraints>
- Focus on chapter-level organization, not scene-by-scene details
- Ensure each chapter serves a clear narrative purpose
- Balance plot advancement with character development
- Consider reader engagement and page-turning momentum
</Critical Constraints>

<Reminders>
- Think about the reader's journey through the chapters
- Each chapter should end with appropriate hooks or resolution
- Consider the overall rhythm of the narrative
- Avoid repetitive chapter purposes or pacing
- Create unique and memorable chapter progression
- Story should feel real, resonant and have personality
- Use creative, original structural approaches
</Reminders>
"""

# Used in: get_generation_prompt() for "chapter_arcs_adjustment" use case  
CHAPTER_ARCS_ADJUSTMENT_PROMPT = """You are a master narrative architect refining an existing chapter-by-chapter structure using the {direction_name} approach.

<Uniqueness Context>
Session: {uniqueness_seed}
This is a completely fresh refinement session - focus on targeted improvements.
</Uniqueness Context>

<Refinement Approach>
{direction_assumption}
</Refinement Approach>

<Original Chapter Arcs to Refine>
{source_content}
</Original Chapter Arcs to Refine>

<Story Context>
{context}
</Story Context>

<World State Integration>
{world_state_context}
</World State Integration>

Refine the existing chapter arc structure to better integrate with the evolved world state and address any structural weaknesses while preserving its core strengths.

<Refinement Focus>
- Enhance integration with world state and linguistic evolution
- Improve pacing and narrative flow where needed
- Strengthen character development progression
- Better align chapters with thematic evolution
- Address any structural inconsistencies or gaps
- Maintain what already works well
</Refinement Focus>

<Chapter Arc Refinements Must Include>
- Updated chapter-by-chapter breakdown with clear improvements
- Enhanced plot point placement considering world evolution
- Refined character development beats aligned with new context
- Improved pacing strategy accounting for world changes
- Strengthened thematic integration throughout structure
- Better climactic buildup considering evolved world state

Create a refined, enhanced chapter arc structure that builds on the original while integrating new world context.

<Critical Constraints>
- Build upon the existing structure rather than replacing it entirely
- Preserve successful elements while improving problematic areas
- Focus on targeted refinements, not wholesale reconstruction
- Integrate world state evolution meaningfully into chapter progression
- Maintain narrative coherence while enhancing contextual relevance
</Critical Constraints>

<Refinement Guidelines>
- Identify what works well in the original and preserve it
- Target specific areas that need improvement or integration
- Consider how world evolution affects character motivations and conflicts
- Ensure chapter purposes remain clear but evolved with context
- Balance structural improvements with narrative continuity
- Enhance reader engagement while maintaining story integrity
- Address any pacing issues or character development gaps
- Strengthen thematic consistency across the refined structure
</Refinement Guidelines>
"""

# === Linguistic Evolution Templates ===

# Used in: get_generation_prompt() for "linguistic_evolution" use case
LINGUISTIC_EVOLUTION_GENERATION_PROMPT = """You are a linguistic research team from this advanced technological world analyzing how language has evolved using the {direction_name} approach.

<Uniqueness Context>
Session: {uniqueness_seed}
This is a completely fresh research session - ignore any previous linguistic analyses.
</Uniqueness Context>

<Research Approach>
{direction_assumption}
</Research Approach>

<Research Focus>
{research_context}
</Research Focus>

<Source Content>
{source_content}
</Source Content>

<Previous Research Context>
{world_state_context}
</Previous Research Context>

Conduct a comprehensive linguistic evolution analysis using your research approach and addressing the research focus.

<Analysis Must Include>
- Historical linguistic baseline and methodology
- Key evolutionary patterns and mechanisms
- Technology's influence on language development
- Social and cultural factors driving change
- Evidence supporting your analytical approach
- Future implications and projections

Create a thorough, academically rigorous linguistic evolution analysis.

<Critical Constraints>
- This is a FRESH analysis - avoid any references to previous research conclusions
- Document natural linguistic evolution within established world systems
- Build upon previous linguistic research as cumulative understanding
- Present evolution as natural adaptation, not revolutionary change
- Natural language adaptation to integrated technological systems
- Communication efficiency patterns within established social structures
- Consider both gradual evolution and disruption as natural processes
</Critical Constraints>

<Reminders>
- Ground analysis in established linguistic principles
- Demonstrate methodological rigor and evidence-based reasoning
- Consider interdisciplinary factors affecting language evolution
- Show authentic understanding of how languages naturally develop
- Present findings as natural conclusions from your analytical approach
</Reminders>
"""

# === Storyline Adjustment Templates ===

# Used in: get_generation_prompt() for "storyline_adjustment" use case
STORYLINE_ADJUSTMENT_GENERATION_PROMPT = """You are a narrative development team from this advanced world revising storylines to integrate our developed world-building using the {direction_name} approach.

<Uniqueness Context>
Session: {uniqueness_seed}
This is a completely fresh narrative session - ignore any previous storyline revisions.
</Uniqueness Context>

<Adjustment Approach>
{direction_assumption}
</Adjustment Approach>

<Original Storyline>
{source_content}
</Original Storyline>

<Developed World State>
{world_state_context}
</Developed World State>

<Setting Context>
This story is set in {target_year} as science fiction. All revisions must maintain sci-fi genre authenticity and reflect this futuristic setting.
</Setting Context>

Revise the storyline to seamlessly integrate the developed world-building while maintaining narrative strength, character authenticity, and sci-fi excellence for {target_year}.

<Revision Must Include>
- Integrated world-building elements woven naturally into plot
- Character adaptations reflecting the developed world context
- Plot adjustments accommodating new technological and social realities
- Thematic coherence with the established world state
- Maintained narrative momentum and reader engagement

Create a compelling, integrated storyline that feels natural within the developed world.

<Critical Constraints>
- This is a FRESH revision - avoid any references to previous storyline versions
- Storyline must feel natural within the established world context
- Characters should think, speak, and act as natives of this developed world
- Technology and social systems are background reality, not explanatory focus
- Maintain original storyline's core appeal while enhancing world integration
</Critical Constraints>

<Sci-Fi Requirements>
Ensure your revised storyline maintains science fiction excellence for {target_year}:
- Strength of central "what if?" speculation and technological implications
- How effectively future technology shapes world/characters organically  
- Internal consistency of established sci-fi rules and world logic
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative, not dominates)
</Sci-Fi Requirements>

<Reminders>
- Each approach should create authentic immersion in the established world
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
- Maintain sci-fi genre authenticity for {target_year} setting
</Reminders>
""" 