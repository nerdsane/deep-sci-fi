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

