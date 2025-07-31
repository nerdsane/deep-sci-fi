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

