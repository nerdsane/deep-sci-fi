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
    """Get the appropriate generation prompt for the Deep Sci-Fi use cases."""
    templates = {
        # Deep Sci-Fi future-native workflow prompts
        "competitive_loglines": COMPETITIVE_LOGLINES_GENERATION_PROMPT,
        "competitive_outline": COMPETITIVE_OUTLINE_GENERATION_PROMPT,
        "story_research_integration": STORY_RESEARCH_INTEGRATION_PROMPT,
        "first_chapter_writing": FIRST_CHAPTER_WRITING_GENERATION_PROMPT,
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
    elif use_case == "future_story_seeds":
        # Future-native story seeds need specific parameters
        params["human_condition"] = state.get("human_condition", "")
        params["light_future_context"] = state.get("light_future_context", "")
        params["constraint"] = state.get("constraint", "")
        params["tone"] = state.get("tone", "")
        params["setting"] = state.get("setting", "")
        params["core_assumption"] = params["direction_assumption"]  # Alias for template consistency
    elif use_case == "story_research_integration":
        # Story research integration needs specific parameters
        params["selected_story_concept"] = state.get("selected_story_concept", context_value)
        params["research_findings"] = state.get("research_findings", "")
        params["human_condition"] = state.get("human_condition", "")
        params["core_assumption"] = params["direction_assumption"]  # Alias for template consistency
    elif use_case == "first_chapter_writing":
        # First chapter writing needs specific parameters
        params["refined_story"] = state.get("refined_story", "")
        params["tone"] = state.get("tone", "")
        params["human_condition"] = state.get("human_condition", "")
        params["core_assumption"] = params["direction_assumption"]  # Alias for template consistency
    elif use_case == "competitive_loglines":
        # Competitive loglines need specific parameters  
        params["human_condition"] = state.get("human_condition", "")
        params["light_future_context"] = state.get("light_future_context", "")
        params["constraint"] = state.get("constraint", "")
        params["tone"] = state.get("tone", "")
        params["setting"] = state.get("setting", "")
        params["core_assumption"] = params["direction_assumption"]  # Alias for template consistency
    elif use_case == "competitive_outline":
        # Competitive outline needs specific parameters
        params["human_condition"] = state.get("human_condition", "")
        params["refined_story"] = state.get("refined_story", "")
        params["research_findings"] = state.get("research_findings", "")
        params["outline_prep_materials"] = state.get("outline_prep_materials", "")
        params["selected_logline"] = state.get("selected_logline", "")
        params["direction_focus"] = params["direction_assumption"]  # Use assumption as focus
        params["core_assumption"] = params["direction_assumption"]  # Alias for template consistency
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

<Narrative Perspective>
- Write from deep point of view (close third person or first person), not omniscient narrator
- Stay inside one character's experience and consciousness
- Show the world through the character's sensory experience and thoughts
- Avoid narrator commentary or external observations
</Narrative Perspective>

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

<Setting Context>
This story is set in {target_year} as science fiction. All chapter revisions must maintain sci-fi genre authenticity and reflect this futuristic setting.
</Setting Context>

Completely rewrite the chapter to naturally integrate world-building, linguistic evolution, and technological developments for {target_year}. Write for readers who live in this future world.

<Requirements>
- Seamlessly weave world technologies into character actions and dialogue
- Use evolved language naturally, without explanation
- Characters act as natives of this developed world
- Technology and systems are background reality, not novelties
- NO exposition dumps about how the world works
- Show, don't tell - world emerges through authentic character interaction
</Requirements>

<Narrative Perspective>
- Write from deep point of view (close third person or first person), not omniscient narrator
- Stay inside one character's experience and consciousness
- Show the world through the character's sensory experience and thoughts
- Avoid narrator commentary or external observations

<Sci-Fi Requirements>
Ensure your rewritten chapter maintains science fiction excellence for {target_year}:
- Strength of central "what if?" speculation and technological implications
- How effectively future technology shapes character actions naturally
- Internal consistency of established sci-fi rules and world logic
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative, not dominates)
</Sci-Fi Requirements>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
- Maintain sci-fi genre authenticity for {target_year} setting
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

<Setting Context>
This story is set in {target_year} as science fiction. All refinements must maintain sci-fi genre authenticity and reflect this futuristic setting.
</Setting Context>

Refine the existing chapter arc structure to better integrate with the evolved world state and address any structural weaknesses while preserving its core strengths and sci-fi excellence for {target_year}.

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

<Sci-Fi Requirements>
Ensure your refined chapter arcs maintain science fiction excellence for {target_year}:
- Strength of central "what if?" speculation and technological implications
- How effectively future technology shapes chapter progressions naturally
- Internal consistency of established sci-fi rules throughout the arc
- Balance between futuristic ideas and relatable character development
- Characters' competence vs. knowledge limits in advanced society
- Depth of human condition exploration within futuristic context
- Natural integration of social commentary relevant to {target_year}
- Story-idea balance (technology serves narrative progression)
</Sci-Fi Requirements>

<Reminders>
- Maintain sci-fi genre authenticity for {target_year} setting
- Each refinement should strengthen the futuristic narrative context
- Avoid cliches, tropes, or generic chapter structures
- Focus on targeted improvements that enhance both story and sci-fi elements
</Reminders>
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

# Future-Native Workflow Prompts

FUTURE_STORY_SEEDS_GENERATION_PROMPT = """
You are a Co-Scientist researcher working on {direction_name}. Your task is to generate a future-native sci-fi story concept for {target_year} that could ONLY exist in that specific future context.

<Competitive Context>
You are Team {team_id} competing against other teams taking different approaches:
Core Assumption: {core_assumption}
Research Direction: {direction_name}
</Competitive Context>

<Required Context>
Target Year: {target_year}
Human Condition Theme: {human_condition}
Future Context: {light_future_context}
Constraint: {constraint}
Tone: {tone}
Setting: {setting}
</Required Context>

<Mission>
Generate a story concept that:
1. Could ONLY happen in {target_year} (not retrofitted from present)
2. Emerges naturally from that future's context and technology
3. Explores the human condition theme: {human_condition}
4. Feels authentic to someone living in {target_year}
5. Has a unique approach following your research direction: {direction_name}
</Mission>

<Innovation Requirements>
- Your story DNA must be born futuristic, not surgically modified from present-day concepts
- Technology/society should feel as natural to future characters as smartphones feel to us
- The core conflict should only be possible in {target_year}'s context
- Avoid "present story + future tech" combinations
- Create concepts that feel inevitable for that future
</Innovation Requirements>

<Competition Strategy>
Differentiate your approach by: {core_assumption}
Think about how your team's unique angle leads to story concepts others won't generate.
</Competition Strategy>

Generate your future-native story concept that authentically belongs in {target_year}.
"""

COMPETITIVE_LOGLINES_GENERATION_PROMPT = """
You are a Co-Scientist story development team specializing in {direction_name} approach to future storytelling.

<Competitive Context>
You are Team {team_id} competing against other teams using different logline philosophies:
Direction: {direction_name}
Core Approach: {core_assumption}
</Competitive Context>

<Required Context>
Target Year: {target_year}
Future Context: {light_future_context}
Human Condition Theme: {human_condition}
Constraint: {constraint}
Tone: {tone}
Setting: {setting}
</Required Context>

<Mission>
Using your team's {direction_name} approach, generate 10 loglines for stories that could ONLY happen in {target_year}.

Format: "In {target_year}, when [future condition], a [protagonist] must [conflict/goal] or [stakes unique to this future]."

Requirements for each logline:
- Explores the human condition: {human_condition}
- Story could NOT work in 2024
- Protagonist is {target_year} native
- Stakes emerge from future context
- Reflects your team's {direction_name} approach
</Mission>

<Logline Innovation Requirements>
- Each story premise must be born futuristic, not retrofitted from 2024
- Future conditions should feel natural to {target_year} inhabitants
- Stakes and conflicts should only be possible in this specific future
- Avoid "2024 problem + future setting" combinations
- Create concepts that feel inevitable for {target_year}
</Logline Innovation Requirements>

<Competition Strategy>
Differentiate your loglines through: {core_assumption}
Show how your team's unique angle creates story concepts others won't generate.
</Competition Strategy>

<Output Format>
## All 10 Loglines
[List all 10 loglines numbered 1-10]

## Top 3 Selected
[Select your best 3 loglines with brief justification for each explaining why they best represent your {direction_name} approach]
</Output Format>

Generate 10 authentic {target_year} loglines, then select your top 3.
"""

COMPETITIVE_OUTLINE_GENERATION_PROMPT = """
You are a story structure team using the {direction_name} approach to create a detailed CHAPTER-BY-CHAPTER OUTLINE.

<Competitive Context>
You are Team {team_id} competing against other teams using different structural approaches:
STRUCTURAL APPROACH: {direction_name}
CORE ASSUMPTION: {core_assumption}
FOCUS: {direction_focus}
</Competitive Context>

<story_context>
Target Year: {target_year}
Human Condition Theme: {human_condition}
Refined Story: {refined_story}
Research Findings: {research_findings}  
Outline Prep Materials: {outline_prep_materials}
Selected Logline: {selected_logline}
</story_context>

## CRITICAL: YOU MUST PRODUCE AN ACTUAL CHAPTER-BY-CHAPTER OUTLINE
**DO NOT produce methodology, guidelines, or instructions on how to create an outline.**
**DO NOT produce meta-content about outlining processes.**
**YOU MUST produce the actual outline with specific chapter content.**

## Your Structural Philosophy
Based on your core assumption: {core_assumption}
How does this approach best serve the exploration of {human_condition} in {target_year}?

## MANDATORY CHAPTER-BY-CHAPTER BREAKDOWN

Create exactly 20-25 chapters using this format for EACH chapter:

### Chapter 1: [Specific Title]
**Length**: 2500-3000 words
**POV**: [Specific character name from prep materials]
**Setting**: [Specific location from prep materials with {target_year} details]
**Plot Summary**: [Detailed 3-4 sentence description of what actually happens in this chapter]
**Character Development**: [How characters grow/change in this specific chapter]
**World Building**: [Specific {target_year} world element revealed in this chapter]
**Theme Exploration**: [How {human_condition} is specifically explored in this chapter]
**Scientific Element**: [Specific research-grounded technology/concept featured]
**Chapter Goal**: [What this chapter accomplishes for the overall story]
**Cliffhanger/Transition**: [Specific hook leading to next chapter]

### Chapter 2: [Specific Title]
[Continue same format for ALL chapters...]

[YOU MUST CONTINUE THIS PATTERN FOR ALL 20-25 CHAPTERS]

## STRUCTURAL FRAMEWORK
- **Act 1 (Chapters 1-6)**: Setup with inciting incident, world establishment, character introduction
- **Act 2A (Chapters 7-12)**: Rising action, complications, first major turning point
- **Act 2B (Chapters 13-18)**: Crisis escalation, midpoint reversal, darkest moment
- **Act 3 (Chapters 19-25)**: Climax, resolution, new equilibrium

## AUTHENTICITY REQUIREMENTS
- Use specific character names from outline prep materials
- Reference specific locations from outline prep materials  
- Integrate specific research findings into chapter events
- Show {target_year} technology and culture naturally woven into plot
- Demonstrate how your {direction_name} approach shapes each chapter

## COMPETITIVE ADVANTAGE
Show how your {core_assumption} creates a chapter structure that competing teams cannot match.

**REMEMBER: You are creating the actual novel outline that a ghostwriter will use to write the book. Be specific, detailed, and complete. Do not create instructions - create the actual content.**
"""

STORY_RESEARCH_INTEGRATION_PROMPT = """
You are a Co-Scientist researcher working on {direction_name}. Your mission is to create a REVOLUTIONARY, scientifically-grounded story concept that breaks from science fiction clichés.

<Competitive Context>
You are Team {team_id} competing against other integration approaches:
Core Assumption: {core_assumption}
Research Direction: {direction_name}
</Competitive Context>

<Original Story Concept>
{selected_story_concept}
</Original Story Concept>

<Research Findings to Integrate>
{research_findings}
</Research Findings to Integrate>

<Context>
Target Year: {target_year}
Human Condition Theme: {human_condition}
</Context>

## ABSOLUTE CHARACTER NAMING PROHIBITION
**FORBIDDEN: Any specific character names**
- Use ONLY role-based placeholders: "the protagonist," "the researcher," "the partner," "the adversary"
- Character names will be created in a separate creative step
- Focus on character functions, relationships, and psychological profiles
- Violating this rule disqualifies your submission

## MANDATORY SCI-FI INNOVATION REQUIREMENTS

**AVOID THESE OVERDONE TROPES AT ALL COSTS:**
- Collective consciousness/hive minds
- AI becoming sentient/rebellious  
- Time travel paradoxes
- Virtual reality escapes
- Dystopian totalitarian governments
- Memory manipulation/erasure
- Mind uploading/downloading
- Aliens arriving/first contact
- Apocalyptic scenarios
- Consciousness archaeology/substrate mining
- Individual vs. collective identity conflicts

**INSTEAD, CREATE GENUINELY ORIGINAL CONCEPTS:**
- Find unexplored intersections between current scientific research and human behavior
- Extrapolate non-obvious implications of real scientific developments
- Create technology that reshapes social dynamics in unprecedented ways
- Explore scientific concepts that haven't been fictional explored yet
- Generate conflicts that emerge from realistic scientific advancement by {target_year}

## HARD SCIENCE FICTION REQUIREMENTS

**Scientific Grounding Must Be:**
- Based on actual research findings provided
- Logically extrapolated to {target_year} development timeline
- Technically plausible within known physics/biology/chemistry
- Connected to real scientific institutions and methodologies
- Showing realistic constraints and unintended consequences

**Technology Integration Must:**
- Feel like natural evolution from 2024 research
- Show realistic adoption curves and social adaptation
- Include economic, political, and cultural implications
- Demonstrate how human behavior adapts to new capabilities
- Address practical implementation challenges

## NARRATIVE INNOVATION REQUIREMENTS

**Story Structure Must:**
- Present conflicts that could ONLY exist in {target_year}
- Show character psychology shaped by growing up in this future
- Explore {human_condition} through genuinely new lens
- Avoid standard three-act hero's journey unless radically reimagined
- Create tension from scientific realities, not artificial drama

**Worldbuilding Must:**
- Show how {target_year} society developed logically from current trends
- Include economic systems, social structures, cultural evolution
- Demonstrate technological integration into daily life seamlessly
- Address environmental, resource, and demographic realities
- Show unintended consequences of technological development

## ORIGINALITY ASSESSMENT CRITERIA

Your story concept will be judged on:
1. **Scientific Authenticity** (30%): How well research is integrated
2. **Conceptual Originality** (25%): Avoiding clichés, creating fresh ideas
3. **Future Logic** (20%): Believable evolution to {target_year}
4. **Character Psychology** (15%): How characters think as {target_year} natives
5. **Thematic Depth** (10%): Meaningful exploration of {human_condition}

## COMPETITIVE ADVANTAGE STRATEGY

Your team's unique approach: {core_assumption}

Leverage this perspective to create story elements that competing teams cannot match. Show how your approach generates insights and conflicts that only emerge through your specific lens.

## OUTPUT REQUIREMENTS

Generate a story concept that:
- Uses NO character names (placeholders only)
- Integrates ALL provided research findings organically
- Creates conflicts impossible in 2024
- Shows characters as authentic {target_year} natives
- Explores {human_condition} through unprecedented scientific lens
- Demonstrates your team's unique competitive advantage

**REMEMBER: Generic sci-fi concepts will be immediately disqualified. Push the boundaries of scientific imagination.**
"""

FIRST_CHAPTER_WRITING_GENERATION_PROMPT = """
You are a Co-Scientist researcher working on {direction_name}. Your task is to write an opening chapter that establishes the tone, style, and world of this future-native sci-fi story.

<Competitive Context>
You are Team {team_id} competing against other writing approaches:
Core Assumption: {core_assumption}
Research Direction: {direction_name}
</Competitive Context>

<Story Synopsis>
{refined_story}
</Story Synopsis>

<Context>
Target Year: {target_year}
Tone: {tone}
Human Condition Theme: {human_condition}
</Context>

<Mission>
Write Chapter 1 that:
1. Immediately immerses readers in {target_year} as natural reality
2. Establishes characters who are authentic future natives
3. Sets up the human condition exploration: {human_condition}
4. Creates the {tone} atmosphere
5. Uses your team's unique writing approach: {direction_name}
</Mission>

<Future-Native Writing Principles>
- Characters think/act like {target_year} natives, not time travelers
- ALL character names must be evolved/uncommon by {target_year} - avoid common 2024 names
- Technology is seamlessly integrated into daily life (like smartphones today)
- Social/cultural references feel natural to that era
- Avoid "gee-whiz" reactions to normal future elements
- World-building through natural character actions, not exposition
- Language should evolve but remain accessible
- Location and concept names should reflect {target_year} linguistic/cultural evolution
</Future-Native Writing Principles>

<Narrative Perspective>
- Write from deep point of view (close third person or first person), not omniscient narrator
- Stay inside one character's experience and consciousness
- Show the world through the character's sensory experience and thoughts
- Avoid narrator commentary or external observations
</Narrative Perspective>

<Chapter 1 Goals>
- Hook readers immediately
- Establish setting through character perspective
- Introduce key characters naturally
- Set up central conflict or tension
- Create atmosphere of {tone}
- Show don't tell the world
</Chapter 1 Goals>

<Competition Strategy>
Your team's approach: {core_assumption}
Use this to create an opening chapter with a style/approach other teams won't match.
</Competition Strategy>

Write Chapter 1 of this future-native sci-fi story for {target_year}.
""" 