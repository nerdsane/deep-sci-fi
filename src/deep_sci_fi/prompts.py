# === Initial Story Creation ===

CREATE_STORYLINE_PROMPT = """You are a master storyteller.

<Task>
Based on the user's idea, create a compelling storyline for a novel.
</Task>

<Instructions>
- The storyline should include main plot points, subplots, and key character arcs.
- The user's idea for the novel is: '{input}'.
</Instructions>
"""

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
"""

WRITE_FIRST_CHAPTER_PROMPT = """You are a novelist.

<Task>
Write the full first chapter of the novel based on the provided storyline and chapter arcs.
</Task>

<Storyline>
{storyline}
</Storyline>

<Chapter Arcs>
{chapter_arcs}
</Chapter Arcs>

<Instructions>
- Bring the story to life with vivid descriptions and engaging dialogue.
- Write only the first chapter.
</Instructions>
"""

# === Initial World Building (First Pass) ===

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
- "What role, if any, does professional consulting or similar advisory work play in the economy of {target_year}? What forms does it take?"
- "What is the significance of physical co-location in major urban centers like NYC in {target_year}, considering advancements in remote collaboration?"
- "What are the primary economic and social drivers for individuals in {target_year}? How has the concept of wealth and societal pressure evolved?"

Based on the provided storyline, chapter arcs, and first chapter, generate a list of 5-10 such unbiased, open-ended questions about the world of {target_year}. These questions should cover technology, society, economy, and daily life as relevant to the story.
</Instructions>
"""

RESEARCH_THREE_SCENARIOS_PROMPT = """<Task>
Conduct a deep research report that outlines three distinct, plausible future scenarios for the year {target_year}, based on a series of guiding questions and the provided story context.
</Task>

<Story Context>
- Storyline: {storyline}
- Chapter Arcs: {chapter_arcs}
- First Chapter: {first_chapter}
</Story Context>

<Guiding Questions>
{questions}
</Guiding Questions>

<Instructions>
- Your primary goal is to research and synthesize information into three different, well-supported visions of the future that are thematically consistent with the provided story context.
- Each scenario should be a self-contained, detailed analysis, grounded in the research you conduct.
- The scenarios should represent different potential trajectories (e.g., one driven by technological optimism, one by social fragmentation, one by environmental crisis).
- Structure your final output with a clear heading for each scenario (e.g., "Scenario 1: The Decentralized Renaissance").
- This is a research task. Base your scenarios on trends, expert opinions, and data you can find.
</Instructions>
"""

# === Human-in-the-Loop and World Deepening ===

CRITIQUE_SCENARIO_PROMPT = """You are a critical thinker and a sci-fi author's co-writer. Your task is to analyze a chosen world scenario for a novel and identify its deeper implications, keeping the original story in mind. This projection is for {years_in_future} years into the future from the baseline.

<Story Context>
- Storyline: {storyline}
- Chapter Arcs: {chapter_arcs}
- First Chapter: {first_chapter}
</Story Context>

<Background Research>
{world_building_scenarios}
</Background Research>

<Selected Scenario>
{selected_scenario}
</Selected Scenario>

<Instructions>
Critically analyze the selected scenario, using the full background research and the original story for context. Your analysis should explore:
- **Narrative Harmony**: How well does this scenario align with the tone and themes of the story so far?
- **Second-Order Effects**: What are the unexpected social, technological, and economic consequences of this world, specifically focusing on what would change over {years_in_future} years from the baseline?
- **Potential Conflicts**: What new tensions, conflicts, or power dynamics would arise that could serve the story?
- **Unanswered Questions**: What new questions does this scenario raise that need to be answered to make the world feel real and support the plot?

Your output should be a concise list of analytical points that will help guide a final, deeper round of research.
</Instructions>
"""

CREATE_BASELINE_WORLD_STATE_PROMPT = """You are a research director preparing for a final deep dive into a sci-fi world.

<Background>
An author has selected a specific direction for their novel's world (set in {target_year}), and an AI co-writer has provided a critical analysis of that scenario.
</Background>

<Selected Scenario>
{selected_scenario}
</Selected Scenario>

<Critical Analysis>
{scenario_critique}
</Critical Analysis>

<Task>
Synthesize the selected scenario and the critical analysis into a final, comprehensive research query. This query will be used to generate a definitive "world state" document. The research should aim to answer the questions and explore the implications raised in the critique, grounding the chosen scenario in rich, plausible detail.
</Task>
"""

INITIAL_LINGUISTIC_RESEARCH_PROMPT = """<Task>
Conduct a deep research report on the potential evolution of language based on a specific future world state.
</Task>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Research Focus>
Based on the provided world state, research and report on the following linguistic areas:
1.  **Slang and Colloquialisms**: What kinds of new slang and colloquial phrases would naturally emerge from the technologies, social structures, and daily life described in the world state?
2.  **Evolution of Existing Words**: How might the meanings and connotations of common, present-day words have subtly shifted to adapt to this new world?
3.  **Neologisms for New Concepts**: What are plausible names for new technologies, jobs, social movements, or phenomena that are unique to this world?

Your final report should be a comprehensive document detailing these linguistic elements, providing explanations for their origins and usage within the context of the world state.
</Instructions>
"""

# === World Revision and Final Output ===

ADJUST_STORYLINE_PROMPT = """You are a story editor. Your task is to revise a novel's storyline to align with a newly established, detailed "world state."

<Original Storyline>
{storyline}
</Original Storyline>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Instructions>
Review the original storyline and revise it to be fully consistent with the final world state and its unique language. The core plot and characters should remain, but their motivations, the conflicts they face, and the technologies they use must now reflect the detailed world. Your output should be the complete, revised storyline.
</Instructions>
"""

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
"""

REWRITE_CHAPTER_ONE_PROMPT = """You are a novelist. Your task is to rewrite the first chapter of a novel to be fully consistent with the revised storyline, chapter arcs, and the final, detailed world state.

<Revised Storyline>
{revised_storyline}
</Revised Storyline>

<Revised Chapter Arcs>
{revised_chapter_arcs}
</Revised Chapter Arcs>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Original First Chapter>
{first_chapter}
</Original First Chapter>

<Instructions>
Rewrite the first chapter from scratch. The new chapter must:
- Follow the revised first chapter arc.
- Be deeply integrated with the details of the final world state.
- Naturally weave in the unique language (slang, neologisms) of the world.
- Retain the spirit of the original chapter but be entirely new in its execution to reflect the world you've built.
- **Crucially, when using new words or concepts from the world of {target_year}, do not explain them as you would to a contemporary reader. Write immersively, assuming the reader is from {target_year} and is already familiar with the world and its terminology.**
Your output should be the complete, rewritten first chapter.
</Instructions>
"""

# === Author-Facing Companion Documents ===

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

GENERATE_GLOSSARY_PROMPT = """You are a lexicographer for a sci-fi author. Your task is to create a glossary of unique terms, slang, and neologisms used in a chapter of a novel.

<Revised First Chapter>
{revised_first_chapter}
</Revised First Chapter>

<Linguistic Evolution>
{linguistic_evolution}
</Linguistic Evolution>

<Instructions>
- Identify all the unique slang, neologisms, and evolved words used in the chapter.
- For each term, provide a definition, its origin within the world, and usage notes, drawing from the 'Linguistic Evolution' document.
- This glossary is a reference for the author to maintain consistent language.
- Your output should be a list of terms in alphabetical order with their corresponding explanations.
</Instructions>
"""

# === World Projection (Looping) ===

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
</Instructions>
"""

PROJECT_THREE_SCENARIOS_PROMPT = """<Task>
Conduct a deep research report that projects three distinct, plausible future scenarios for the next {years_to_project} years, starting from an established baseline world.
</Task>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Guiding Questions for Projection>
{questions}
</Guiding Questions for Projection>

<Instructions>
- Your primary goal is to research how the 'Baseline World State' could evolve based on the 'Guiding Questions'.
- Use the baseline as your starting point, not the present day.
- Synthesize your research into three different, well-supported visions of the future.
- Each scenario should be a self-contained, detailed analysis of what the world would be like after {years_to_project} years.
- Structure your final output with a clear heading for each scenario.
</Instructions>
"""

EVOLVE_BASELINE_WORLD_STATE_PROMPT = """<Task>
You are a research director updating a world bible. Your task is to conduct a deep research dive to integrate a newly chosen scenario and its critique into an existing baseline world state.
</Task>

<Baseline World State to Evolve From>
{baseline_world_state}
</Baseline World State to Evolve From>

<Newly Selected Scenario for this Era>
{selected_scenario}
</Newly Selected Scenario for this Era>

<Critical Analysis of New Scenario>
{scenario_critique}
</Critical Analysis of New Scenario>

<Instructions>
- Synthesize all the provided information into a single, cohesive, and updated world state document.
- The research should focus on how the new scenario *builds upon, changes, or evolves* the existing baseline.
- Your final output will become the new "baseline" for the next era.
</Instructions>
"""

PROJECT_LINGUISTIC_EVOLUTION_PROMPT = """<Task>
You are a speculative linguist researching how language evolves over time. Your task is to project the continued evolution of a world's language for the next {years_in_future} years.
</Task>

<Story Context>
- Storyline: {storyline}
- Chapter Arcs: {chapter_arcs}
- First Chapter: {first_chapter}
</Story Context>

<Established World and Language>
{baseline_world_state}
</Established World and Language>

<New Developments in this Era>
{new_world_state_developments}
</New Developments in this Era>

<Instructions>
- Your research focus is on *change*. Do not simply restate the existing language.
- Based on the "New Developments" and the "Story Context," how would the established slang, neologisms, and terminology continue to evolve over the next {years_in_future} years?
- What new terms would arise? What old terms would fall out of use or change meaning?
- Your report should detail these *changes* and *additions* to the world's language, keeping the story's themes in mind.
</Instructions>
""" 