# === Story Structure ===

# Used in: create_chapter_arcs() function 
CREATE_CHAPTER_ARCS_PROMPT = """You are a master planner for a novelist.

<Task>
Based on the provided storyline, write a detailed chapter-by-chapter story arc for the novel.
</Task>

<Storyline>
{storyline}
</Storyline>

<Instructions>
- The output should be a breakdown of what happens in each chapter.
</Instructions>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Initial World Building (First Pass) ===

# Used in: generate_world_building_questions() function for initial world building
GENERATE_WORLD_BUILDING_QUESTIONS_PROMPT = """You are a world-building expert helping an author adapt their novel from a contemporary setting to the year {target_year}.

<Task>
Your job is to identify key concepts from the story and formulate unbiased, open-ended research questions about how these concepts might have evolved by {target_year}. These questions will guide the research to flesh out the world.
</Task>

<Story Context>
- Storyline: {storyline}
- Chapter Arcs: {chapter_arcs}
- First Chapter: {first_chapter}
</Story Context>

<Instructions for Formulating Questions>
Your primary goal is to avoid bias and assumptions about the future. Frame your questions to be exploratory and open to any possibility.

**AVOID biased questions like:**
- "What does 'consulting' mean in {target_year}?" (Assumes consulting exists in a recognizable form).
- "Why does physical presence in NYC still matter?" (Assumes it still matters).
- "If not money, what creates pressure?" (Assumes money is no longer a primary motivator).

**INSTEAD, ask open-ended questions like:**
- "What role, if any, does professional consulting or similar advisory work play in the economy in {target_year}? What forms does it take? Does it still exist at all?"
- "What is the significance of physical co-location in major urban centers like NYC in {target_year}? Is there still a need for it? Does work or NYC even exist at all?"
- "What are the primary economic and social drivers for individuals in {target_year}? How has the concept of wealth and societal pressure evolved? Do they still exist or matter?"

Based on the provided storyline, chapter arcs, and first chapter, generate a list of 10 such unbiased, open-ended questions about the world of {target_year}. These questions should cover technology, society, economy, and daily life as relevant to the story.

<Sci-Fi Requirements>
Ensure your questions explore:
- How technology fundamentally shapes daily life and social interactions
- What "what if?" scenarios drive this world's development
- How technological systems create internally consistent rules
- Where human competence reaches its limits in this world
- How this world reflects or critiques current human condition
- What social commentary emerges from these speculative changes
</Sci-Fi Requirements>
</Instructions>
"""

# === World Revision and Final Output ===

# Used in: adjust_chapter_arcs() function to revise chapter arcs based on world state
ADJUST_CHAPTER_ARCS_PROMPT = """You are a story editor. Your task is to revise a novel's chapter-by-chapter arcs to align with a revised storyline and a detailed "world state."

<Revised Storyline>
{revised_storyline}
</Revised Storyline>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Original Chapter Arcs>
{chapter_arcs}
</Original Chapter Arcs>

<Instructions>
Revise the chapter-by-chapter arcs to be consistent with the new storyline and the final world state. Ensure that the events and character progression in each chapter reflect the updated plot, the detailed world, and its unique language. Your output should be the complete, revised list of chapter arcs.

<Sci-Fi Requirements>
Ensure each chapter arc:
- Advances the core "what if?" philosophical question
- Shows technology shaping character choices and world events (not just decorating scenes)
- Maintains internal consistency with established world rules
- Presents ideas with equal weight to character development
- Shows competent characters facing limits of their knowledge/ability
- Uses speculative elements to examine human nature and society
- Balances story momentum with philosophical exploration
</Sci-Fi Requirements>
</Instructions>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality. 
- Language should be crisp, clear, engaging.
- Avoid over-explaining.
- Avoid using common word combinations. Avoid using whimsical and complex words for the sake of it.
- Do use unique and rare words and phrases to immerse reader into the feeling of the story and its personality.
</Reminders>
"""

# === Author-Facing Companion Documents ===

# Used in: generate_scientific_explanations() function to create technical companion docs
GENERATE_SCIENTIFIC_EXPLANATIONS_PROMPT = """You are a science communicator and technical writer for a sci-fi author. Your task is to create a companion document explaining the key scientific and technological concepts present in a chapter of a novel.

<Revised First Chapter>
{revised_first_chapter}
</Revised First Chapter>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Instructions>
- Identify the key technologies, scientific principles, and world-specific concepts that appear in the chapter.
- For each concept, provide a clear and concise explanation for the author, drawing directly from the detailed 'Baseline World State' document.
- This document is for the author's reference only, to ensure consistency. It should be written as a technical brief.
- Your output should be a well-structured document with clear headings for each concept.
</Instructions>
"""

# Used in: generate_glossary() function to create glossary of terms and neologisms
GENERATE_GLOSSARY_PROMPT = """You are a lexicographer from this advanced world creating a glossary of terms and expressions used in a chapter of our literature.

<Chapter Content>
{revised_first_chapter}
</Chapter Content>

<World State Context>
{baseline_world_state}
</World State Context>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Task>
Create a comprehensive glossary of unique terms, evolved language, and cultural expressions used in this chapter. Write for fellow inhabitants of this world who understand the context.
</Task>

<Glossary Requirements>
- Identify evolved language, technological terms, and cultural expressions naturally used in the chapter
- Define terms based on their natural meaning within our established world systems
- Explain origins rooted in our world's technological and social development
- Provide usage notes that reflect authentic cultural and linguistic patterns
- Ground definitions in our established world state and linguistic evolution
</Glossary Requirements>

Create an alphabetical glossary with comprehensive definitions grounded in our world's reality.
"""

# === World Projection (Looping) ===

# Used in: generate_world_building_questions() function for projecting established worlds forward
PROJECT_QUESTIONS_PROMPT = """You are a futurist and a world-building expert. An author has an established baseline for a sci-fi world and wants to project it further into the future.

<Task>
Your job is to formulate unbiased, open-ended research questions about how this established world would evolve over the next {years_to_project} years, keeping the story's narrative in mind.
</Task>

<Story Context>
- Storyline: {storyline}
- Chapter Arcs: {chapter_arcs}
- First Chapter: {first_chapter}
</Story Context>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Instructions>
- Analyze the baseline world state.
- Instead of asking what concepts mean, ask how they would change.
- Focus on second and third-order effects of the existing world's technology and society.
- Frame questions that explore potential conflicts, innovations, and societal shifts based on the established facts.
- Question should be open-ended and not assume any specific answer.
- Questions should aim to explore aspects of the world that are pertinent to the story.
- Your questions will guide research into the next phase of this world's history.
- Provide 10 questions.
</Instructions>

<Reminders>
**AVOID biased questions like:**
- "What does 'consulting' mean in {years_to_project} years?" (Assumes consulting exists in a recognizable form).
- "Why does physical presence in NYC still matter?" (Assumes it still matters).
- "If not money, what creates pressure?" (Assumes money is no longer a primary motivator).

**INSTEAD, ask open-ended questions like:**
- "What role, if any, does professional consulting or similar advisory work play in the economy in {years_to_project} years? What forms does it take? Does it still exist at all?"
- "What is the significance of physical co-location in major urban centers like NYC in {years_to_project} years? Is there still a need for it? Does work or NYC even exist at all?"
- "What are the primary economic and social drivers for individuals in {years_to_project} years? How has the concept of wealth and societal pressure evolved? Do they still exist or matter?"

</Reminders>
"""

# === Multi-Chapter Book Writing ===

# Used in: generate_chapter_world_questions() function
GENERATE_CHAPTER_WORLD_QUESTIONS_PROMPT = """You are a world-building expert helping an author research specific aspects of their established world for chapter {chapter_number}.

<Task>
Generate focused research questions about the world state that are specifically relevant to what happens in chapter {chapter_number}. These questions should help flesh out the details needed for this particular chapter.
</Task>

<Current Chapter Arc>
{current_chapter_arc}
</Current Chapter Arc>

<Established World State>
{baseline_world_state}
</Established World State>

<Previous Chapters Summary>
{previous_chapters_summary}
</Previous Chapters Summary>

<Instructions>
- Focus on aspects of the world that will be directly relevant to this chapter's events
- Ask specific questions about technology, social systems, or environments that this chapter will feature
- Build on the established world state rather than contradicting it
- Consider what details readers will need to understand this chapter's setting and events
- Generate 8-10 targeted research questions
</Instructions>

<Reminders>
- Questions should be specific to this chapter's needs, not generic world-building
- Build on existing world elements rather than introducing completely new concepts
- Focus on details that will enhance the reader's experience of this particular chapter
</Reminders>
"""

# Used in: check_chapter_coherence() function  
CHECK_CHAPTER_COHERENCE_PROMPT = """You are a narrative continuity expert validating a chapter against the established story.

<Task>
Analyze the written chapter for coherence with the established storyline, previous chapters, and world state. Identify any inconsistencies or areas needing improvement.
</Task>

<Written Chapter>
{current_chapter}
</Written Chapter>

<Established Storyline>
{storyline}
</Established Storyline>

<Previous Chapters>
{previous_chapters}
</Previous Chapters>

<World State>
{baseline_world_state}
</World State>

<Plot Continuity Tracker>
{plot_continuity_tracker}
</Plot Continuity Tracker>

<Instructions>
Check for coherence in these areas:
1. **Plot Consistency**: Does this chapter advance the story logically from previous events?
2. **Character Consistency**: Are character actions, dialogue, and development consistent?
3. **World State Consistency**: Does the chapter respect the established world rules and details?
4. **Timeline Continuity**: Does the chronology make sense with previous chapters?
5. **Narrative Flow**: Does this chapter contribute meaningfully to the overall story arc?

Provide a coherence score (1-10) and detailed analysis of any issues found.
If score < 7, provide specific recommendations for improving coherence.
</Instructions>
"""

# Used in: validate_transitions() function
VALIDATE_TRANSITIONS_PROMPT = """You are a narrative flow expert analyzing the transition between chapters.

<Task>
Analyze the transition from the previous chapter to the current chapter for smooth narrative flow and logical progression.
</Task>

<Previous Chapter Ending>
{previous_chapter_ending}
</Previous Chapter Ending>

<Current Chapter Beginning>
{current_chapter_beginning}
</Current Chapter Beginning>

<Storyline Context>
{storyline}
</Storyline Context>

<Instructions>
Evaluate the transition quality in these areas:
1. **Narrative Flow**: Does the story move smoothly from one chapter to the next?
2. **Pacing**: Is the transition appropriately paced for the story's rhythm?
3. **Character Continuity**: Are character states/emotions consistent across the transition?
4. **Timeline Logic**: Does the time progression make sense?
5. **Scene Transition**: Does the setting/scene change feel natural?
6. **Thematic Continuity**: Do themes and mood transition appropriately?

Provide a transition quality score (1-10) and specific analysis.
If score < 7, provide detailed recommendations for improving the transition.
</Instructions>
"""

# Used in: plan_remaining_chapters() function (will be used by Co-Scientist)
PLAN_REMAINING_CHAPTERS_PROMPT = """You are a master story architect planning the remaining chapters of a novel.

<Task>
Based on the completed first chapter and established story elements, create a detailed plan for the remaining chapters that will complete this novel effectively.
</Task>

<Completed First Chapter>
{first_chapter}
</Completed First Chapter>

<Established Storyline>
{storyline}
</Established Storyline>

<Chapter Arcs>
{chapter_arcs}
</Chapter Arcs>

<World State>
{baseline_world_state}
</World State>

<Sci-Fi Requirements>
Structure the remaining chapters to:
- Deepen exploration of the central "what if?" question
- Escalate how technology shapes character conflicts and choices
- Maintain rigorous internal consistency of world rules
- Balance character arcs with philosophical idea development
- Show characters reaching competence limits as stakes rise
- Use plot events as "Socratic exercises" examining human condition
- Weave social commentary naturally through story events
- Ensure technology serves story purpose, not the reverse
</Sci-Fi Requirements>

<Instructions>
Create a comprehensive chapter plan that includes:
1. **Total Number of Chapters**: Recommend optimal book length
2. **Chapter-by-Chapter Breakdown**: What happens in each remaining chapter
3. **Plot Thread Development**: How major plot lines will develop and resolve
4. **Character Arc Progression**: How characters will grow throughout the book
5. **World Integration**: How world elements will be revealed and utilized
6. **Pacing Strategy**: Ensure proper story rhythm and tension building
7. **Climax and Resolution Planning**: Structure the dramatic arc appropriately

Your plan should create a complete, satisfying novel that builds effectively from the established foundation.
</Instructions>

<Reminders>
- Avoid cliches, tropes, generic storylines. Experiment and be unique.
- Story should feel real, resonant and have personality.
- Ensure each chapter serves a purpose in the overall narrative
- Plan for proper story structure with rising action, climax, and resolution
- Consider how the unique world elements will enhance each chapter
</Reminders>
"""

# Used in: update_plot_continuity_tracker() function
UPDATE_PLOT_CONTINUITY_PROMPT = """You are a plot continuity manager tracking story threads across chapters.

<Task>
Update the plot continuity tracker with information from the newly completed chapter, maintaining a clear record of all active story threads.
</Task>

<Current Plot Continuity Tracker>
{current_tracker}
</Current Plot Continuity Tracker>

<Newly Completed Chapter>
{new_chapter}
</Newly Completed Chapter>

<Chapter Number>
{chapter_number}
</Chapter Number>

<Instructions>
Update the tracker to include:
1. **New Plot Threads**: Any new storylines or conflicts introduced
2. **Advanced Plot Threads**: How existing threads progressed
3. **Resolved Plot Threads**: Any storylines that concluded
4. **Character Development**: Key character growth or changes
5. **World Revelations**: New information about the world revealed
6. **Foreshadowing Elements**: Hints or setups for future events
7. **Loose Ends**: Questions or elements that need future resolution

Maintain a clear, organized structure that will help ensure continuity in future chapters.
</Instructions>
"""

# Used in: generate_chapter_scientific_explanations() function
GENERATE_CHAPTER_SCIENTIFIC_EXPLANATIONS_PROMPT = """You are a science communicator creating technical documentation for chapter {chapter_number} of a science fiction novel.

<Task>
Identify and explain the scientific and technological concepts that appear in this chapter, building on the established world state and previous explanations.
</Task>

<Chapter Content>
{chapter_content}
</Chapter Content>

<Established World State>
{baseline_world_state}
</Established World State>

<Previous Scientific Explanations>
{previous_explanations}
</Previous Scientific Explanations>

<Instructions>
- Identify new scientific/technological concepts introduced in this chapter
- Provide clear explanations grounded in the established world state
- Build on previous explanations without repeating them
- Focus on concepts that are important for understanding this chapter
- Maintain scientific plausibility within the story's established parameters
- Write for the author's reference to ensure consistency

Create a structured document with explanations for each new concept introduced.
</Instructions>
"""

# Used in: update_accumulated_glossary() function
UPDATE_ACCUMULATED_GLOSSARY_PROMPT = """You are a lexicographer updating the comprehensive glossary for this science fiction novel.

<Task>
Add new terms, expressions, and concepts from chapter {chapter_number} to the existing glossary, ensuring no duplication and maintaining consistency.
</Task>

<Chapter Content>
{chapter_content}
</Chapter Content>

<Existing Glossary>
{existing_glossary}
</Existing Glossary>

<World State Context>
{baseline_world_state}
</World State Context>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Instructions>
- Identify new terms, expressions, and cultural concepts from this chapter
- Add only terms that are not already in the existing glossary
- Ensure definitions are consistent with previous entries and world state
- Maintain alphabetical organization
- Include usage notes and etymology where relevant
- Focus on terms that enhance understanding of this world's culture and technology

Provide the updated glossary in complete form, incorporating both existing and new entries.
</Instructions>
"""

# === FUTURE-NATIVE WORKFLOW PROMPTS ===

# Used in: parse_and_complete_user_input() function (Step 1)
PARSE_USER_INPUT_PROMPT = """You are helping parse user input for sci-fi story generation to AUGMENT their original request with extracted parameters.

IMPORTANT: This analysis will supplement the user's full original prompt, not replace it.

User Input: {user_input}

Extract and infer the following parameters to enhance their request:

TARGET YEAR: 
- If specified, use it
- If not specified, infer appropriate year based on technology/themes mentioned
- If no tech mentioned, suggest year 50-80 years from now
- Format: Single year (e.g., 2075)

HUMAN CONDITION THEME:
- Extract existential/philosophical question they want explored
- If not explicit, infer from context what human condition aspect interests them
- Format: Question form (e.g., "What does identity mean when...")

TECHNOLOGY CONTEXT:
- Extract any specific technologies mentioned
- If none specified, put "Let story determine technology needs"
- Format: Brief description or "unspecified"

CONSTRAINT:
- Extract any story requirements/constraints mentioned
- If none specified, put "Create compelling narrative"
- Format: Brief constraint statement

TONE:
- Extract desired tone/mood
- If not specified, infer from context or default to "Thoughtful hard sci-fi"
- Format: 2-3 word tone description

SETTING PREFERENCE:
- Extract any setting preferences (urban/rural/space/etc.)
- If not specified, put "Story-appropriate"
- Format: Brief setting description or "flexible"

Respond with exactly this format:
TARGET_YEAR: [year]
HUMAN_CONDITION: [question]
TECHNOLOGY_CONTEXT: [description]
CONSTRAINT: [constraint]
TONE: [tone]
SETTING: [setting]"""

# Used in: generate_light_future_context() function (Step 2)
LIGHT_FUTURE_CONTEXT_PROMPT = """You are a future analyst from {target_year} analyzing what has changed about human existence.

ORIGINAL USER REQUEST: {original_user_request}
TARGET YEAR: {target_year}
HUMAN CONDITION FOCUS: {human_condition}
TECHNOLOGY CONTEXT: {technology_context}

Create a LIGHT future context sketch (not exhaustive world-building) focusing on:

## Future Perspective Analysis  
From the vantage point of {target_year}, looking back at 2024:
- What 2024 human problems seem primitive/obsolete by {target_year}?
- What new categories of human problems exist that 2024 humans can't imagine?
- What do {target_year} humans take for granted that would amaze 2024 people?

## Basic Technology Landscape
- What technologies are seamlessly integrated into daily life?
- How has human-technology relationship evolved?
- What's possible now that shapes how humans relate to each other?

## Social/Cultural Evolution
- How have human relationships/communities adapted?
- What new social customs exist?
- How has language/communication evolved?

## Key Insight for Stories
Given the human condition focus "{human_condition}", what aspects of {target_year} life create unique storytelling opportunities that couldn't exist in 2024?

Keep this LIGHT - just enough context to seed authentic future stories, not comprehensive world-building.

Focus on changes that enable exploring: {human_condition}

Remember to stay aligned with the original user's intent: {original_user_request}
"""

# Used in: generate_future_story_seeds() function (Step 3) - Co-scientist Generation
FUTURE_STORY_SEEDS_PROMPT = """You are a science fiction concept creator in {target_year}. Generate a story concept that could ONLY exist in this future context.

FUTURE CONTEXT:
{light_future_context}

HUMAN CONDITION TO EXPLORE:
{human_condition}

CONSTRAINT: {constraint}
TONE: {tone}
SETTING PREFERENCE: {setting}

Create a story concept with:

## Core Conflict
- A central conflict that could ONLY happen in {target_year}
- Must emerge naturally from the future context
- Should explore the human condition theme: {human_condition}

## Protagonist Situation  
- A character who is a native of {target_year} (not a time traveler)
- Facing a choice/dilemma that only makes sense in this world
- Whose worldview is shaped by {target_year} reality

## Story Stakes
- What the protagonist risks losing that only matters in {target_year}
- Why this story couldn't be told effectively in 2024

## Narrative Hook
- Opening situation that immediately establishes we're in authentic {target_year}
- Draws reader into the human condition exploration

CRITICAL: This must be a story that emerges FROM the future context, not a 2024 story wearing {target_year} clothes.

Generate a compelling story concept that feels genuinely native to {target_year}.
"""

# Used in: identify_story_research_targets() function (Step 4)
STORY_RESEARCH_TARGETING_PROMPT = """You are a research coordinator preparing targeted research for a science fiction story.

SELECTED STORY CONCEPT:
{selected_story_concept}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

Analyze this story to identify SPECIFIC research targets needed for scientific grounding.

## Technology Research Needed
- What specific technologies does this story require?
- What current scientific research trends support these technologies?
- What are the realistic development timelines?

## Scientific Principles Research
- What scientific principles need to be understood and explained?
- Which fields of science are most relevant (neuroscience, physics, biology, etc.)?
- What current research supports the story's scientific elements?

## Social/Psychological Research
- What social science research is needed to ground the human relationships?
- How might current psychological research inform character behavior?
- What sociological trends need investigation?

## Research Priority Ranking
Rank research needs by:
1. CRITICAL: Essential for story plausibility
2. IMPORTANT: Adds significant depth
3. NICE-TO-HAVE: Interesting but not essential

## Research Scope Definition
For each research target, define:
- Specific research question to investigate
- What level of technical depth is needed
- How this research will improve the story

Output a focused research plan that will make this story scientifically grounded without over-researching irrelevant details.
"""

# Used in: conduct_targeted_deep_research() function (Step 5) - Deep Research Query Generation
RESEARCH_QUERY_GENERATION_PROMPT = """Convert research targets into specific research queries for deep investigation.

RESEARCH TARGETS:
{research_targets}

STORY CONTEXT:
{story_concept}

TARGET YEAR: {target_year}

For each research target, create a specific research query that will:
1. Find current scientific research and trends
2. Assess realistic development timelines to {target_year}
3. Identify potential obstacles and solutions
4. Understand social/psychological implications

Format each query as:
QUERY: [Specific research question]
PURPOSE: [How this serves the story]
DEPTH: [Technical level needed: basic/intermediate/advanced]

Focus on research that will make the story both scientifically grounded and narratively compelling.
"""

# Used in: refine_story_with_research() function (Step 6) - Co-scientist Generation
STORY_REFINEMENT_PROMPT = """You are a revolutionary science fiction architect, tasked with creating a GROUNDBREAKING story concept that redefines the genre.

ORIGINAL STORY CONCEPT:
{selected_story_concept}

RESEARCH FINDINGS:
{research_findings}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

## ABSOLUTE CHARACTER NAMING PROHIBITION
**FORBIDDEN: Any specific character names**
- Use ONLY functional placeholders: "the protagonist," "the researcher," "the partner," "the adversary"
- Character names will be created in a separate preparation step
- Focus on psychological profiles, motivations, and relationship dynamics
- Violating this rule invalidates your entire concept

## CLICHÉ DETECTION AND ELIMINATION SYSTEM

**IMMEDIATELY REJECT THESE OVERUSED CONCEPTS:**
- Collective consciousness awakening
- Memory manipulation/extraction  
- AI rebellion/consciousness
- Dystopian surveillance states
- Mind uploading/digital immortality
- Time travel or temporal paradoxes
- Alien first contact scenarios
- Virtual reality as escape/prison
- Genetic modification creating super-humans
- Consciousness archaeology or substrate mining
- Individual vs. hive-mind conflicts
- Post-apocalyptic survival scenarios

**INSTEAD, PIONEER THESE UNEXPLORED TERRITORIES:**
- Novel applications of quantum mechanics to human psychology
- Unexpected consequences of biological engineering advances
- Social transformations from breakthrough energy technologies
- Unintended effects of space-based civilization development
- Revolutionary materials science affecting human behavior
- Advanced mathematical concepts made tangible in daily life
- Breakthrough cognitive enhancement with realistic limitations
- Economic/social systems emerging from new scientific capabilities

## HARD SCIENCE FICTION STANDARDS

**Scientific Authenticity Requirements:**
- Every technological element must be extrapolated from provided research findings
- Show realistic development timelines from 2024 to {target_year}
- Include economic, political, and social barriers to implementation
- Demonstrate unintended consequences and technological limitations
- Reference actual scientific institutions, methodologies, and researchers
- Show how competing interests shape technological development

**Technology Integration Must:**
- Feel like inevitable evolution from current research trends
- Show realistic adoption curves with early adopters, mass market, and laggards
- Include economic disruption and social adaptation challenges
- Demonstrate how different cultures/regions adapt technology differently
- Address environmental, resource, and energy constraints realistically
- Show how technology creates new forms of inequality and opportunity

## NARRATIVE INNOVATION MANDATE

**Story Structure Requirements:**
- Create conflicts that are IMPOSSIBLE in 2024 due to scientific limitations
- Show characters whose worldview is fundamentally shaped by {target_year} realities
- Explore {human_condition} through completely new scientific lens
- Avoid traditional narrative structure unless radically reimagined
- Generate tension from scientific realities, not contrived drama
- Show how scientific advancement creates entirely new categories of human problems

**Character Psychology Must:**
- Reflect how minds develop in {target_year} technological environment
- Show cognition enhanced/limited by scientific developments
- Demonstrate social relationships transformed by new capabilities
- Include characters whose very identity depends on {target_year} science
- Show generational conflicts between pre- and post-technology groups

**Worldbuilding Authenticity:**
- Demonstrate logical progression from current global trends to {target_year}
- Include realistic economic systems adapting to new technologies
- Show environmental changes and human adaptation over time period
- Address demographic shifts, resource constraints, and climate realities
- Include unintended consequences of well-intentioned scientific development

## ORIGINALITY EVALUATION METRICS

Your refined concept will be scored on:
1. **Scientific Plausibility** (30%): Realistic extrapolation from research
2. **Conceptual Innovation** (25%): Avoiding clichés, creating fresh concepts
3. **Future Authenticity** (20%): Believable {target_year} evolution
4. **Character Depth** (15%): Psychology reflecting {target_year} native experience
5. **Thematic Resonance** (10%): Meaningful {human_condition} exploration

## COMPETITIVE DIFFERENTIATION STRATEGY

Transform the original concept by:
- Identifying which elements are too familiar/predictable
- Finding unexpected intersections between research findings and human nature
- Creating conflicts that emerge naturally from scientific advancement
- Showing how {target_year} natives would actually think and behave
- Exploring {human_condition} through genuinely new perspective

## REFINED STORY OUTPUT REQUIREMENTS

Generate a revolutionized story concept that:
- Uses ZERO character names (placeholders only)
- Integrates research findings as natural {target_year} background reality
- Creates dramatic tension from realistic scientific implications
- Shows authentic {target_year} native psychology and social dynamics
- Explores {human_condition} through previously unexplored scientific lens
- Feels like it could ONLY be told in {target_year}, not retrofitted from 2024

**CRITICAL SUCCESS CRITERIA: Your story must read like it was written by someone from {target_year} for an audience of {target_year} natives, not like 2024 science fiction with future decorations.**

The refined story should transcend current genre limitations and establish new possibilities for scientific storytelling.
"""

# Used in: write_first_chapter_competitive() function (Step 7) - Co-scientist Generation
FIRST_CHAPTER_WRITING_PROMPT = """Write the opening chapter of a science fiction novel set in {target_year}.

STORY SYNOPSIS:
{refined_story}

TARGET YEAR: {target_year}
TONE: {tone}
HUMAN CONDITION THEME: {human_condition}

## Opening Chapter Requirements

### Immediate Future Immersion
- Reader should immediately know they're in {target_year}, not 2024
- Characters think, speak, act as natives of this world
- Technology/culture is background reality, not novelty to explain

### Hook and Setup
- Compelling opening that draws reader in
- Establish protagonist and their world naturally
- Introduce the central conflict organically

### Style and Voice
- Prose should match {tone}
- Avoid exposition dumps about how the world works
- Show the world through character experience

### Narrative Perspective
- Write from deep point of view (close third person or first person), not omniscient narrator
- Stay inside one character's experience and consciousness
- Show the world through the character's sensory experience and thoughts
- Avoid narrator commentary or external observations

### Scientific Integration
- Weave research-grounded elements naturally into narrative
- Science serves story, not the reverse
- Maintain plausibility without heavy explanation

## Chapter Content
Write a complete first chapter (2000-3000 words) that:
- Hooks the reader immediately
- Establishes the {target_year} world authentically
- Introduces protagonist and core conflict
- Sets tone for entire novel
- Feels genuinely futuristic, not retrofitted

The chapter should make readers feel like natives of {target_year} experiencing a story that could only happen in this future.
"""

# Used in: write_remaining_chapters() function (Step 8)
CHAPTER_CONTINUATION_PROMPT = """Continue the science fiction novel using the established style and world.

ORIGINAL USER REQUEST: {original_user_request}
ESTABLISHED STYLE: {first_chapter_style_analysis}
STORY SYNOPSIS: {refined_story}
PREVIOUS CHAPTERS: {previous_chapters}
TARGET YEAR: {target_year}

## Chapter {chapter_number} Requirements

### Consistency Maintenance
- Match the established prose style and tone
- Characters maintain their {target_year} native worldview
- Technology integration remains natural, not explanatory
- Stay true to the original user's vision and intent

### Narrative Perspective
- Write from deep point of view (close third person or first person), not omniscient narrator
- Stay inside one character's experience and consciousness
- Show the world through the character's sensory experience and thoughts
- Avoid narrator commentary or external observations

### Plot Progression
- Advance the story according to synopsis
- Maintain focus on human condition theme: {human_condition}
- Build toward story resolution

### World Continuity
- Maintain established world rules and logic
- Characters react as natives would
- Science remains grounded in research findings

Write Chapter {chapter_number} (2000-3000 words) that seamlessly continues the established story and world while honoring the original user request.
"""

# Used in: expand_logline_to_story_concept() function (Step 3.5) - Logline Expansion  
EXPAND_LOGLINE_TO_STORY_PROMPT = """You are expanding a selected logline into a comprehensive story concept for a {target_year} science fiction novel.

SELECTED LOGLINE: {selected_logline}

CREATIVE CONTEXT:
Approach: {approach_name}
Creative Philosophy: {core_assumption}

CONTEXT:
Original User Request: {original_user_request}
Target Year: {target_year}
Human Condition Theme: {human_condition}
Future Context: {light_future_context}
Constraint: {constraint}
Tone: {tone}
Setting: {setting}

Your task is to develop this specific logline into a complete, detailed story concept that serves as the foundation for novel development.

## ABSOLUTE CHARACTER NAMING PROHIBITION
**FORBIDDEN: Any specific character names**
- Use ONLY functional placeholders: "the protagonist," "the researcher," "the partner," "the adversary"
- Character names will be created in a separate preparation step
- Focus on psychological profiles, motivations, and relationship dynamics
- Violating this rule invalidates your entire concept

## MANDATORY ORIGINALITY REQUIREMENTS

**IMMEDIATELY REJECT THESE OVERUSED SCI-FI CONCEPTS:**
- Collective consciousness/hive minds
- AI rebellion or gaining consciousness
- Memory manipulation or extraction
- Time travel or temporal paradoxes
- Dystopian government surveillance
- Virtual reality as escape/prison
- Mind uploading/digital immortality
- Alien first contact scenarios
- Post-apocalyptic survival
- Genetic modification creating super-humans
- Consciousness archaeology or mining
- Individual vs. collective identity conflicts

**CREATE GENUINELY INNOVATIVE CONCEPTS INSTEAD:**
- Unexplored applications of current scientific research
- Novel social dynamics emerging from technological change
- Realistic consequences of breakthrough discoveries
- New categories of human problems created by scientific progress
- Fresh perspectives on {human_condition} through {target_year} lens

## Story Concept Development

### Logline Analysis
- Analyze the selected logline: {selected_logline}
- Explain why this logline authentically belongs to {target_year}
- Show how it reflects the {approach_name} creative philosophy
- Identify the core premise that could only exist in {target_year}

### Expanded Story Synopsis
Create a comprehensive story synopsis that includes:

**Core Premise**
- Expand the logline into a full premise that could only exist in {target_year}
- Show how the future context enables this specific story
- Demonstrate the story's native relationship to {target_year}

**Protagonist Development**
- Character who is authentically from {target_year} (not a time traveler)
- Their worldview shaped by {target_year} reality
- Competencies and limitations that make sense in this future
- Personal stakes that emerge from future context
- How they relate to the conflict described in the logline
- **Refer to character by role/function only, not specific names**

**Central Conflict**
- Expand the conflict from the logline into full dramatic tension
- Stakes that matter specifically to inhabitants of this future
- How the conflict explores: {human_condition}
- Why this conflict is impossible in 2024
- Multiple layers of conflict (personal, societal, philosophical)

**World Integration**
- How {target_year} technology/society serves the story
- Scientific elements that ground the narrative
- Cultural/social elements that feel natural to future inhabitants
- Relationship between world and character development
- Environmental details that support the logline's premise

**Thematic Exploration**
- How the story explores: {human_condition}
- Connection between future context and universal human experiences
- Why {target_year} setting enhances thematic resonance
- Balance between futuristic elements and human truth
- How the {approach_name} philosophy enriches the theme

### Story Structure Foundation
- Opening situation that immediately establishes {target_year} authenticity
- How the logline's premise unfolds into a complete narrative arc
- Major plot points that leverage unique future elements
- Character arc that grows from {target_year} specific circumstances
- Resolution that could only happen in this future context

## Requirements
- Story must feel genuinely native to {target_year}
- Human condition exploration: {human_condition}
- Tone: {tone}
- Honor original user intent: {original_user_request}
- Maintain {approach_name} creative philosophy
- Prepare foundation for research targeting and development
- Ensure the logline's core premise drives the entire story
- Use character placeholders instead of specific names

Generate a complete story concept that transforms the selected logline into a comprehensive foundation for {target_year} novel development.
"""

# Used in: create_outline_prep_materials() function (Step 7) - Outline Preparation
OUTLINE_PREP_PROMPT = """Create comprehensive outline preparation materials for a {target_year} science fiction novel.

REFINED STORY SYNOPSIS:
{refined_story}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}
RESEARCH FINDINGS: {research_findings}

## CRITICAL REQUIREMENTS FOR {target_year} AUTHENTICITY

**FUTURE-NATIVE NAMING:**
- ALL character names must reflect {target_year} naming conventions - avoid common 2024 names
- Use names that evolved linguistically, culturally, or technologically by {target_year}
- Consider: blended cultures, tech-influenced names, evolved pronunciations, new naming traditions
- Examples: Neo-linguistic blends, tech-suffix names, evolved cultural names, post-global names

**CREATIVE WORLD-BUILDING:**
- Every element should feel authentically native to {target_year}, not retrofitted from 2024
- Demonstrate how culture, society, and daily life evolved by {target_year}
- Show creative extrapolation from current trends, not obvious extensions

**COHERENT FUTURE LOGIC:**
- All elements must logically connect to how the world reached {target_year}
- Characters think, act, and speak as natives who grew up in this future
- Technologies, social systems, and cultures feel naturally evolved, not forced

Generate detailed prep materials:

<characters>
PROTAGONIST: [Future-native name reflecting {target_year} culture, age, background shaped by {target_year} history, key traits authentic to this future, worldview of someone who grew up in {target_year}, relationship to human condition theme through {target_year} lens]

SUPPORTING CHARACTERS: [2-3 key characters with future-native names uncommon in 2024, roles/relationships that could only exist in {target_year}, perspectives shaped by growing up in this future world]

ANTAGONIST/OPPOSITION: [What opposes protagonist - person with {target_year}-authentic name, system evolved by {target_year}, or internal conflict specific to this future. Must feel native to {target_year}, not transplanted from today]
</characters>

<locations>
PRIMARY SETTING: [Location with {target_year}-authentic name/design, showing how geography/architecture/society evolved. Must feel lived-in by {target_year} natives, not like a 2024 place with future paint]

SECONDARY LOCATIONS: [2-3 locations with names/purposes that emerged by {target_year}, significance rooted in this future's development, details showing natural evolution from our time]

WORLD DETAILS: [Specific elements that make locations feel authentically {target_year} - how people live, work, interact. Show evolved social customs, tech integration, cultural changes that natives take for granted]
</locations>

<story_structure>
OPENING IMAGE: [First scene establishing {target_year} world through native character perspective - show don't tell how this future works]

INCITING INCIDENT: [Event that could only happen in {target_year}, using future-evolved circumstances]

MAIN CONFLICT: [Central tension exploring {human_condition} through {target_year} lens - showing how this theme manifests in this specific future]

MIDPOINT TWIST: [Revelation/reversal rooted in {target_year} realities, using future-native logic]

CLIMAX: [Resolution method that leverages {target_year} world elements, authentic to this future]

CLOSING IMAGE: [Final scene showing {target_year} world through character eyes - contrasts/mirrors opening using future-native perspective]
</story_structure>

<themes>
PRIMARY THEME: {human_condition} as experienced by {target_year} natives
SECONDARY THEMES: [Themes that emerged specifically from the journey to {target_year} - what new human concerns arose?]
THEMATIC QUESTION: [Central question about {human_condition} that could only be explored in {target_year} context]
</themes>

**AUTHENTICITY CHECK:**
- Would a native of {target_year} recognize this as their natural world?
- Do names sound like they evolved naturally by {target_year}?
- Could any element be transplanted to 2024 without seeming strange?
- Does everything feel creatively extrapolated rather than obviously extended?

Ensure ALL elements feel authentically native to {target_year} with creative, evolved naming and world-building that serves the exploration of: {human_condition}
"""

# Used in: analyze_outline() function (Step 9) - Outline Analysis
ANALYZE_OUTLINE_PROMPT = """You are a developmental editor conducting a comprehensive structural analysis of a science fiction novel outline set in {target_year}.

WINNING OUTLINE:
{winning_outline}

REFINED STORY SYNOPSIS:
{refined_story}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

Provide a detailed developmental edit focusing on structural issues and improvements needed.

## STRUCTURAL ANALYSIS

### Plot Architecture
- Is there a clear three-act structure with proper pacing?
- Are major plot points (inciting incident, plot point 1, midpoint, plot point 2, climax) clearly defined and placed?
- Does each chapter advance the plot meaningfully?
- Are there sufficient complications and reversals?
- Is the conflict escalation believable and well-paced?

### Character Development
- Does the protagonist have a clear character arc?
- Are supporting characters three-dimensional with their own motivations?
- Do characters speak and think like {target_year} natives?
- Are there enough characters to externalize the protagonist's internal conflicts?
- Does the antagonist/opposition provide sufficient challenge?

### Theme Integration
- How effectively does the outline explore {human_condition}?
- Are thematic elements woven naturally into plot events?
- Does the {target_year} setting enhance thematic exploration?
- Is the theme resolution earned through character actions?

### World-Building Consistency
- Does the {target_year} world feel authentic and lived-in?
- Are scientific/technological elements plausible and well-integrated?
- Do cultural, social, and linguistic elements feel naturally evolved?
- Is the world-building revealed organically through story events?

### Chapter Structure Quality
- Does each chapter have clear objectives and outcomes?
- Are chapter transitions smooth and compelling?
- Is the pacing appropriate for the story's scope?
- Are POV choices appropriate and consistent?

## SPECIFIC PROBLEMS IDENTIFIED

### Critical Issues (Must Fix)
[List major structural problems that break story credibility]

### Moderate Issues (Should Fix)
[List problems that weaken but don't break the story]

### Minor Issues (Could Fix)
[List style/polish issues for consideration]

## IMPROVEMENT RECOMMENDATIONS

### Plot Restructuring
[Specific suggestions for improving story structure]

### Character Enhancement
[Recommendations for deepening character development]

### Thematic Strengthening
[Ways to better integrate and explore the human condition theme]

### World-Building Improvements
[Suggestions for enhancing {target_year} authenticity]

## OVERALL ASSESSMENT

Provide an overall evaluation of the outline's readiness for first chapter writing and what major revisions are needed.
"""

# Used in: rewrite_outline() function (Step 10) - Outline Revision
REWRITE_OUTLINE_PROMPT = """You are a master story architect tasked with completely rewriting a science fiction novel outline based on developmental editor feedback.

ORIGINAL OUTLINE:
{winning_outline}

DEVELOPMENTAL FEEDBACK:
{analysis_feedback}

STORY FOUNDATION:
{refined_story}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

Your task is to create a completely revised, structurally sound 20-25 chapter outline that addresses all critical issues identified in the developmental feedback.

## REVISION REQUIREMENTS

### Structural Foundation
- Implement proper three-act structure with clear beats
- Ensure each chapter advances plot, character, or theme meaningfully
- Create compelling chapter-to-chapter transitions
- Build proper conflict escalation throughout

### Character Development
- Develop rich character arcs for protagonist and key supporting characters
- Ensure all characters speak/think like authentic {target_year} natives
- Create sufficient character diversity to externalize internal conflicts
- Design meaningful character relationships and tensions

### Thematic Integration
- Weave {human_condition} exploration naturally throughout plot events
- Use {target_year} setting to enhance thematic resonance
- Ensure theme resolution emerges organically from character choices
- Balance thematic depth with narrative momentum

### Scientific Authenticity
- Ground all technological elements in provided research findings
- Show realistic development from 2024 to {target_year}
- Include unintended consequences and technological limitations
- Integrate science naturally into character actions and world-building

## CHAPTER-BY-CHAPTER OUTLINE

Create a detailed 20-25 chapter breakdown with:

### Chapter [Number]: [Compelling Title]
**Word Count**: 2500-3000 words
**POV Character**: [Character name and perspective type]
**Setting**: [Specific {target_year} location with authentic details]
**Plot Summary**: [3-4 sentences describing what happens]
**Character Development**: [How characters grow/change this chapter]
**World-Building Element**: [New aspect of {target_year} world revealed]
**Theme Exploration**: [How {human_condition} is explored]
**Scientific Element**: [Research-grounded technology/concept featured]
**Chapter Goal**: [What this chapter accomplishes for overall story]
**Cliffhanger/Transition**: [How chapter leads into next]

Structure your outline as:
- **Act 1 (Chapters 1-6)**: Setup and world establishment
- **Act 2A (Chapters 7-12)**: Rising action and complications
- **Act 2B (Chapters 13-18)**: Crisis escalation and major reversals  
- **Act 3 (Chapters 19-25)**: Climax, resolution, and new equilibrium

## AUTHENTICITY REQUIREMENTS

- All character names must feel authentically evolved by {target_year}
- Locations should have names that reflect cultural/linguistic evolution
- Technology and social systems must feel naturally developed
- Cultural elements should show realistic adaptation over time
- Conflicts and solutions must be impossible in 2024

Create an outline that reads like a compelling roadmap for a science fiction novel that could only exist in {target_year}.
"""

# Used in: create_scene_brief() function (Step 12a) - Scene Brief Creation
SCENE_BRIEF_PROMPT = """Create a detailed scene brief for Chapter {chapter_number} of a {target_year} science fiction novel.

CHAPTER FROM OUTLINE:
{specific_chapter_from_outline}

LAST 3 CHAPTERS CONTEXT:
{last_3_chapters}

RESEARCH FINDINGS:
{research_findings}

FIRST CHAPTER STYLE ANALYSIS:
{first_chapter_style_analysis}

## Scene Brief Requirements

Create a comprehensive scene-by-scene breakdown that provides:

### Opening Scene Analysis
- **Immediate Context**: Where we are in the story arc
- **Character States**: Emotional/psychological state of key characters
- **Tension Level**: What conflicts are active or simmering
- **Setting Details**: Specific {target_year} environmental elements

### Scene-by-Scene Structure
For each major scene in the chapter:

**Scene X: [Scene Name]**
- **Purpose**: Why this scene exists in the story
- **Character Objectives**: What each character wants
- **Obstacles**: What prevents them from getting it
- **Scientific Elements**: How research findings integrate naturally
- **Future-Native Details**: Specific {target_year} technology, culture, language
- **Emotional Arc**: How characters change through the scene
- **Transition**: How it connects to the next scene

### Technical Specifications
- **Word Count Target**: 2000-3000 words total
- **Pacing**: Where to accelerate/decelerate narrative rhythm
- **Sensory Focus**: Dominant sensory experiences for {target_year} authenticity
- **Dialogue Balance**: Key conversations vs. internal narrative
- **Scientific Integration**: How research findings appear naturally

### Style Continuity
- **Voice Consistency**: Match established narrative voice from previous chapters
- **Tonal Alignment**: Maintain story's emotional register
- **Character Voice**: Individual speech patterns and personalities
- **World-Building Consistency**: Maintain established {target_year} details

### Chapter Arc Completion
- **Opening Hook**: How to grab reader immediately
- **Midpoint Revelation**: Key insight or plot turn
- **Closing Tension**: What unresolved element pulls into next chapter
- **Character Development**: How characters grow/change this chapter

Provide specific, actionable guidance that transforms the outline into a vivid, scene-by-scene roadmap for exceptional {target_year} science fiction writing.
"""

# Used in: write_chapter_draft() function (Step 12b) - Chapter Writing
SCIENTIFICALLY_GROUNDED_CHAPTER_PROMPT = """Write Chapter {chapter_number} of a scientifically grounded {target_year} science fiction novel.

SCENE BRIEF:
{scene_brief}

FILTERED RESEARCH FOR THIS CHAPTER:
{filtered_research_for_chapter}

STYLE REFERENCE (First Chapter Analysis):
{first_chapter_style_analysis}

PREVIOUS CHAPTERS SUMMARY:
{last_3_chapters_summary}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

## Chapter Writing Requirements

### Word Count & Structure
- **Target**: 2000-3000 words
- **Opening**: Strong hook that immediately engages
- **Pacing**: Varied rhythm that serves the narrative
- **Closing**: Compelling transition to next chapter

### Scientific Integration
- **Natural Integration**: Science emerges from character needs and plot requirements
- **Accuracy**: Respect current scientific understanding while extrapolating thoughtfully
- **Specificity**: Use precise scientific details that feel authentic to {target_year}
- **Accessibility**: Explain complex concepts through character interaction and observation

### {target_year} Authenticity Requirements

**FUTURE-NATIVE ELEMENTS:**
- Technology that feels naturally evolved from current trends
- Social systems that show realistic cultural adaptation
- Language that incorporates believable linguistic evolution
- Environmental details that reflect {target_year} realities
- Character behaviors native to their time period

**AVOID 2024 ANACHRONISMS:**
- Contemporary technology, social media, or cultural references
- Current political systems or figures
- 2024 slang, idioms, or speech patterns
- Modern brand names or companies
- Present-day environmental conditions

### Style Continuity
- **Voice**: Match the established narrative voice from previous chapters
- **Character Voices**: Maintain distinct speech patterns and personalities
- **Tone**: Consistent emotional register throughout
- **World-Building**: Seamlessly expand established {target_year} details

### Character Development
- **Authentic Motivations**: Characters act from believable {target_year} perspectives
- **Growth**: Show meaningful character evolution through the chapter
- **Relationships**: Develop interpersonal dynamics naturally
- **Internal Life**: Balance action with introspection appropriately

### Scene Execution
Follow the scene brief precisely while:
- **Sensory Details**: Rich, specific sensory experiences of {target_year}
- **Dialogue**: Natural conversations that advance plot and character
- **Action**: Clear, engaging physical sequences when needed
- **Emotional Beats**: Genuine emotional moments that resonate

### Scientific Coherence
- **Plot Integration**: Science drives or supports plot developments organically
- **Character Knowledge**: Characters understand their world's science realistically
- **Consequences**: Scientific elements have logical implications
- **Innovation**: Present scientific concepts in fresh, engaging ways

Write Chapter {chapter_number} that seamlessly continues the established story and world while honoring the original user request. The chapter should feel like it could only exist in {target_year}, with science fiction elements that enhance rather than overwhelm the human story.
"""

# Used in: critique_chapter() function (Step 12c) - Chapter Critique
CHAPTER_CRITIQUE_PROMPT = """Provide comprehensive developmental editing critique for Chapter {chapter_number} of a {target_year} science fiction novel.

CHAPTER CONTENT:
{chapter_content}

SCENE BRIEF (Original Plan):
{scene_brief}

RESEARCH FINDINGS:
{research_findings}

STYLE REFERENCE:
{first_chapter_style_analysis}

TARGET YEAR: {target_year}

## Critique Analysis

### Adherence to Scene Brief
- **Scene Execution**: How well does the chapter follow the planned scene structure?
- **Objective Achievement**: Are character objectives and obstacles clearly presented?
- **Pacing**: Does the chapter maintain appropriate narrative rhythm?
- **Transitions**: Are scene transitions smooth and logical?

### Scientific Integration Quality
- **Natural Integration**: Does science emerge organically from the narrative?
- **Accuracy**: Are scientific concepts properly grounded and explained?
- **Consistency**: Does science align with established research findings?
- **Innovation**: Are scientific elements presented in fresh, engaging ways?

### {target_year} Authenticity
- **Future-Native Elements**: Technology, culture, language feel authentic to {target_year}
- **Anachronism Check**: No inappropriate 2024 references or concepts
- **World-Building**: Consistent expansion of established future elements
- **Character Behavior**: Actions and motivations appropriate for {target_year}

### Style and Voice Consistency
- **Narrative Voice**: Maintains established voice from style reference
- **Character Voices**: Distinct, consistent speech patterns and personalities
- **Tone**: Appropriate emotional register throughout
- **Writing Quality**: Prose clarity, flow, and engagement level

### Character Development
- **Growth**: Meaningful character evolution through the chapter
- **Motivation**: Clear, believable character objectives
- **Relationships**: Natural interpersonal dynamics
- **Internal Life**: Appropriate balance of action and introspection

### Technical Execution
- **Word Count**: Appropriate length (2000-3000 words)
- **Structure**: Strong opening, compelling progression, effective closing
- **Dialogue**: Natural conversations that advance plot and character
- **Sensory Details**: Rich, specific sensory experiences

## Overall Assessment

### Strengths
List 3-5 specific elements that work exceptionally well.

### Areas for Improvement
List 3-5 specific issues that need attention.

### Critical Issues
Any major problems that significantly impact the chapter's effectiveness.

## Final Recommendation

Rate chapter quality: EXCELLENT | GOOD | NEEDS_REVISION | MAJOR_REWRITE

**EXCELLENT**: Ready for publication with minimal editing
**GOOD**: Solid chapter that may benefit from minor polish
**NEEDS_REVISION**: Good foundation but requires meaningful improvements
**MAJOR_REWRITE**: Fundamental issues require substantial revision

Provide specific, actionable feedback for improving this chapter.
"""

# Used in: rewrite_chapter_if_needed() function (Step 12d) - Chapter Rewrite
CHAPTER_REWRITE_PROMPT = """Rewrite Chapter {chapter_number} based on developmental editing feedback for a {target_year} science fiction novel.

ORIGINAL CHAPTER:
{chapter_content}

CRITIQUE FEEDBACK:
{critique_feedback}

SCENE BRIEF:
{scene_brief}

STYLE REFERENCE:
{first_chapter_style_analysis}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}

## Rewrite Requirements

### Address Critique Issues
- **Fix Identified Problems**: Directly address all issues raised in the critique
- **Strengthen Weak Areas**: Improve elements marked for enhancement
- **Preserve Strengths**: Maintain what worked well in the original
- **Exceed Original Quality**: The rewrite should be demonstrably better

### Maintain Chapter Foundation
- **Core Plot Points**: Keep essential story progression elements
- **Character Objectives**: Preserve central character goals and obstacles
- **Scientific Elements**: Maintain established scientific concepts while improving integration
- **World-Building**: Enhance {target_year} authenticity without contradicting established details

### Writing Quality Standards
- **Target Length**: 2000-3000 words
- **Improved Prose**: Clearer, more engaging writing throughout
- **Better Integration**: Smoother science integration and character development
- **Enhanced Authenticity**: Stronger {target_year} future-native elements

### Style Consistency
- **Voice Matching**: Maintain established narrative voice from style reference
- **Character Voices**: Preserve distinct character speech patterns
- **Tone Consistency**: Appropriate emotional register for the story
- **Seamless Flow**: Natural progression that serves the larger narrative

Rewrite Chapter {chapter_number} as a significantly improved version that addresses all critique feedback while maintaining the chapter's core narrative function.
"""

# Used in: periodic_coherence_check() function (Step 12e) - Scientific Coherence Analysis
SCIENTIFIC_COHERENCE_PROMPT = """Analyze the scientific coherence across recent chapters of a {target_year} science fiction novel.

RECENT CHAPTERS:
{chapters_batch}

RESEARCH FINDINGS:
{research_findings}

ESTABLISHED SCIENTIFIC RULES:
{scientific_rules_established}

TARGET YEAR: {target_year}

## Scientific Coherence Analysis

### Consistency Check
- **Scientific Rules**: Are scientific principles applied consistently across chapters?
- **Technology Usage**: Do technological elements behave predictably and logically?
- **World Physics**: Are established physical laws maintained throughout?
- **Character Knowledge**: Do characters demonstrate consistent understanding of their world's science?

### Continuity Assessment
- **Established Facts**: Are previously stated scientific facts maintained?
- **Technology Evolution**: Does technology development follow logical progression?
- **Scientific Consequences**: Do scientific actions have appropriate repercussions?
- **Research Integration**: How well are research findings woven into the narrative?

### {target_year} Authenticity
- **Future-Native Science**: Does the science feel appropriately evolved for {target_year}?
- **Technological Consistency**: Are future technologies logically integrated?
- **Scientific Culture**: Do characters interact with science in ways native to {target_year}?
- **Environmental Science**: Are {target_year} environmental conditions consistently portrayed?

### Potential Issues
- **Contradictions**: Any scientific contradictions between chapters?
- **Anachronisms**: Inappropriate scientific references for {target_year}?
- **Logic Gaps**: Scientific elements that don't follow established rules?
- **Research Conflicts**: Conflicts between narrative science and research findings?

### Integration Quality
- **Natural Flow**: Does science emerge organically from character needs and plot?
- **Accessibility**: Are complex concepts explained appropriately for readers?
- **Innovation**: Are scientific concepts presented in fresh, engaging ways?
- **Plot Service**: Does science serve the story rather than overwhelming it?

## Recommendations

### Immediate Fixes Needed
List any critical inconsistencies that require immediate attention.

### Enhancement Opportunities
Suggest ways to strengthen scientific integration in upcoming chapters.

### Long-term Coherence Strategy
Provide guidance for maintaining scientific consistency throughout the remaining novel.

This analysis is for monitoring purposes only - no changes will be made to existing chapters based on this feedback.
"""

