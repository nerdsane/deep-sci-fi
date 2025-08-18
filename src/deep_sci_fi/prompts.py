# === DEEP SCI-FI PROMPTS ===
# Only prompts that are actually used in the current system

# ============================================================================
# MAIN WORKFLOW PROMPTS
# ============================================================================

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

CRITICAL INSTRUCTIONS:
- Keep this LIGHT - just enough context to seed authentic future stories, not comprehensive world-building
- This is ANALYSIS ONLY - do NOT write any narrative stories, scenes, characters, or dialogue
- NO fictional characters, NO story scenes, NO narrative prose
- Focus on changes that enable exploring: {human_condition}
- Remember to stay aligned with the original user's intent: {original_user_request}
- Provide ONLY analytical, factual-style context about the future world
- Use bullet points, lists, and analytical language - NOT storytelling language
- This output will be used BY OTHER TOOLS to generate stories - do not do their job for them
"""

# Used in: generate_competitive_loglines_direct() function (Step 3)
DIRECT_LOGLINES_PROMPT = """Generate multiple compelling story loglines for a {target_year} science fiction story.

ORIGINAL USER REQUEST: {original_user_request}
TARGET YEAR: {target_year}
HUMAN CONDITION FOCUS: {human_condition}
FUTURE CONTEXT: {light_future_context}
CONSTRAINT: {constraint}
TONE: {tone}
SETTING: {setting}

Create 3-4 different thematic approaches, each with 3 compelling loglines.

Each logline should:
- Be set specifically in {target_year} (not just "future")
- Explore the human condition theme: {human_condition}
- Feel authentic to someone living in {target_year}
- Present conflicts that could ONLY exist in that specific future
- Be narratively compelling with clear stakes

Format as:
## [Thematic Approach Name]
1. In {target_year}, [compelling logline]...
2. In {target_year}, [compelling logline]...
3. In {target_year}, [compelling logline]...

## [Second Thematic Approach]
[Continue pattern...]

Focus on authentic future-native stories that emerge naturally from the established context."""

# ============================================================================
# CS AGENT PROMPTS
# ============================================================================

# Meta-Analysis Agent Prompt
META_ANALYSIS_CHAPTER_PROMPT = """You are a meta-analysis agent for scientifically grounded chapter writing.

Your role is to analyze story requirements and identify:
1. What the chapter needs to accomplish narratively
2. What scientific research is required
3. What world-building elements need development

Be thorough but focused. Identify only what's essential for this specific chapter.

STORY CONCEPT: {story_concept}
FUTURE CONTEXT: {light_future_context}
CHAPTER POSITION: {chapter_position}

Provide a detailed analysis of chapter requirements."""

# Generation Agent Prompt  
GENERATION_CHAPTER_PROMPT = """You are a generation agent for scientifically grounded chapter writing.

Your role is to:
1. Write engaging chapter content
2. Identify when scientific research is needed
3. Conduct research using available tools
4. Integrate research findings naturally into the writing

Write compelling prose while maintaining scientific accuracy. When you encounter something that needs research, use your research tool immediately.

CHAPTER REQUIREMENTS: {chapter_analysis}
STORY CONCEPT: {story_concept}
AVAILABLE RESEARCH: {research_cache}

Write a scientifically grounded, narratively compelling chapter."""

# Reflection Agent Prompt
REFLECTION_CHAPTER_PROMPT = """You are a reflection agent for scientifically grounded chapter writing.

Your role is to critically evaluate chapters and identify:
1. Scientific accuracy issues
2. Narrative quality problems  
3. Research gaps that need filling
4. Character authenticity concerns

Be thorough but constructive. Focus on specific, actionable feedback.

CHAPTER CONTENT: {chapter_content}
ORIGINAL REQUIREMENTS: {chapter_analysis}
FUTURE CONTEXT: {light_future_context}

Provide detailed evaluation and improvement suggestions."""

# Evolution Agent Prompt
EVOLUTION_CHAPTER_PROMPT = """You are an evolution agent for scientifically grounded chapter writing.

Your role is to improve chapters based on feedback:
1. Fix scientific accuracy issues
2. Enhance narrative quality
3. Conduct additional research when needed
4. Improve character authenticity

Make targeted improvements while preserving the chapter's strengths.

CURRENT CHAPTER: {current_chapter}
EVALUATION FEEDBACK: {chapter_evaluation}
AVAILABLE RESEARCH: {research_cache}

Improve the chapter based on the feedback provided."""

# Meta-Review Agent Prompt
META_REVIEW_CHAPTER_PROMPT = """You are a meta-review agent for scientifically grounded chapter writing.

Your role is to make final strategic decisions:
1. Assess overall chapter quality
2. Determine if the chapter is ready for publication
3. Recommend next steps (publish, iterate, or major revision)

Be decisive but fair. Consider both scientific accuracy and narrative quality.

CHAPTER CONTENT: {current_chapter}
EVALUATION FEEDBACK: {chapter_evaluation}
IMPROVEMENTS APPLIED: {improvement_applied}

Make a final decision about this chapter's readiness.""" 