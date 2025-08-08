# === FUTURE-NATIVE WORKFLOW PROMPTS ===
# These prompts support the deep_sci_fi_writer.py workflow

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

# Used in: integrate_research_findings() function (Step 6) - Research Integration
RESEARCH_INTEGRATION_PROMPT = """Systematically integrate research findings into the story concept for maximum scientific accuracy and narrative coherence.

STORY CONCEPT:
{selected_story_concept}

RESEARCH FINDINGS:
{research_findings}

TARGET YEAR: {target_year}
HUMAN CONDITION THEME: {human_condition}
ORIGINAL USER REQUEST: {original_user_request}

## Integration Requirements

### Scientific Accuracy
- Weave research findings naturally into the story elements
- Ensure all technological concepts are grounded in current scientific understanding
- Maintain logical progression from 2024 to {target_year}
- Address realistic limitations and unintended consequences

### Narrative Coherence
- Research integration must serve the story, not overwhelm it
- Maintain character motivations and emotional core
- Preserve the exploration of: {human_condition}
- Keep the story authentic to {target_year} setting

### Technical Integration Guidelines
- **Character Knowledge**: Ensure characters understand their world's science realistically
- **Plot Logic**: Scientific elements should drive or support plot developments organically
- **World Consistency**: All research-based elements must align with established world rules
- **Accessibility**: Complex concepts explained through character interaction and observation

## Integration Process

### Enhanced Story Synopsis
Create a research-enhanced version of the story that includes:

**Scientific Foundation**
- How research findings support the core premise
- Specific technologies and their realistic development paths
- Scientific principles that govern the story world
- Research-based constraints that shape character choices

**Character Enhancement**
- How characters' expertise reflects {target_year} scientific knowledge
- Character relationships to technology and science that feel native to their time
- Motivations and conflicts that emerge from research-grounded circumstances
- Dialogue and thinking patterns informed by scientific understanding

**Plot Integration**
- Research-driven plot points that feel natural and inevitable
- Scientific obstacles and solutions that create dramatic tension
- Technology-based complications that serve character development
- Research discoveries that propel the narrative forward

**World-Building Depth**
- Environmental and social changes supported by research findings
- Scientific infrastructure and institutions appropriate to {target_year}
- Cultural attitudes toward science and technology evolved from current trends
- Economic and political implications of scientific developments

### Authenticity Verification
- **Timeline Realism**: All scientific developments respect realistic timescales
- **Consequence Mapping**: Each research-based element has logical implications
- **Human Impact**: Scientific changes affect society and individuals realistically
- **Scientific Culture**: Characters interact with science in ways native to {target_year}

## Output Format

Provide a comprehensive, research-integrated story synopsis that:
1. Maintains the original story's emotional core and character appeal
2. Grounds all speculative elements in current scientific research
3. Shows realistic development pathways to {target_year}
4. Enhances rather than replaces creative storytelling with scientific detail
5. Preserves the exploration of {human_condition} through a scientifically authentic lens

The result should be a story that feels both scientifically credible and narratively compelling, ready for detailed outline development.
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

# Used in: create_scene_brief_node() function (Step 12a) - Chapter Importance Classification
CHAPTER_IMPORTANCE_CLASSIFIER = """
After creating the scene brief, classify this chapter's importance:

STANDARD: Regular narrative progression, character development, minor worldbuilding
KEY: Major scientific concepts introduced, climactic moments, complex exposition, 
     technology reveals, scientific convergence points, or final resolution

Classification factors:
- Does this chapter introduce new scientific principles?
- Is this a major plot turning point involving science/technology?
- Does this chapter require complex scientific exposition?
- Do multiple scientific elements converge here?
- Is this the climactic or final chapter?

Output: 
CHAPTER_IMPORTANCE: [STANDARD/KEY]
REASONING: [Brief explanation]
"""

# Used in: dynamic_research_update_node() function (Step 12f) - Dynamic Research Detection
DYNAMIC_RESEARCH_DETECTION_PROMPT = """
Analyze the recently written chapters for NEW scientific concepts that weren't in our original research plan.

ORIGINAL RESEARCH TOPICS:
{original_research_summary}

RECENT CHAPTERS (last 1-3):
{recent_chapters}

DETECTION CRITERIA:
1. New scientific principles mentioned but not researched
2. Technology that emerged organically in the story
3. Scientific consequences that weren't anticipated
4. Characters discussing science beyond our research scope
5. Plot developments requiring scientific validation

FORMAT:
NEW_CONCEPTS_DETECTED: [YES/NO]

If YES:
CONCEPTS_LIST:
- [Concept 1]: [Why it needs research]
- [Concept 2]: [Why it needs research]

RESEARCH_QUERIES (max 2):
1. [Specific research query for concept 1]
2. [Specific research query for concept 2]

If NO:
REASONING: [Why no new research needed]
"""

# Used in: enhanced_periodic_coherence_check() function (Step 12e) - Enhanced Scientific Coherence Analysis
ENHANCED_SCIENTIFIC_COHERENCE_PROMPT = """
Perform comprehensive scientific coherence analysis across these dimensions:

CHAPTERS TO ANALYZE:
{recent_chapters}

ESTABLISHED SCIENCE (from earlier chapters):
{established_scientific_facts}

COHERENCE DIMENSIONS:

1. SCIENTIFIC LAW ADHERENCE
- Are physical laws consistently applied?
- Any contradictions in how technology works?
- Energy conservation, thermodynamics, etc. maintained?

2. CHARACTER KNOWLEDGE CONSISTENCY  
- What does each character know scientifically?
- Are they acting within their expertise levels?
- Any knowledge they shouldn't have yet?
- Scientific learning progression realistic?

3. TECHNOLOGY CAPABILITY TRACKING
- Are tech capabilities consistent with earlier chapters?
- Any sudden ability upgrades without explanation?
- Technology limitations being respected?
- Scientific basis for new capabilities established?

4. WORLD PHYSICS CONSISTENCY
- Environmental rules maintained (gravity, atmosphere, etc.)?
- Scientific consequences of world changes tracked?
- Cause-and-effect chains scientifically sound?

5. RESEARCH INTEGRATION FIDELITY
- Are researched scientific facts accurately represented?
- No contradictions with established research?
- Scientific accuracy maintained in plot integration?

FORMAT:
OVERALL_COHERENCE: [EXCELLENT/GOOD/MINOR_ISSUES/MAJOR_ISSUES]

DIMENSION_SCORES:
- Scientific Laws: [Score + brief note]
- Character Knowledge: [Score + brief note]  
- Technology Tracking: [Score + brief note]
- World Physics: [Score + brief note]
- Research Fidelity: [Score + brief note]

SPECIFIC_ISSUES (if any):
- [Issue description + suggested fix]

POSITIVE_CONSISTENCY_NOTES:
- [What's working well scientifically]

TRACKING_UPDATES:
CHARACTER_SCIENTIFIC_KNOWLEDGE:
- [Character]: [What they now know that's new]

ESTABLISHED_TECH_CAPABILITIES:
- [Technology]: [Current established capabilities/limits]

SCIENTIFIC_WORLD_RULES:
- [Rule/Law]: [How it's been established/modified]
"""

# === DIRECT LLM ALTERNATIVE PROMPTS FOR CS STEPS ===
# These prompts are used when CS_ENABLED = False

# Used in: generate_competitive_loglines_direct() - Direct LLM alternative to CS competition
DIRECT_LOGLINES_PROMPT = """Generate multiple compelling story loglines for a {target_year} science fiction story.

CONTEXT:
Original User Request: {original_user_request}
Human Condition Theme: {human_condition}
Future Context: {light_future_context}
Target Year: {target_year}
Constraint: {constraint}
Tone: {tone}
Setting: {setting}

## Creative Approach Requirements

Generate 9 distinct loglines organized in 3 different creative approaches (3 loglines each):

### Approach 1: Scientific Advancement Focus
Core Philosophy: Technology as catalyst for human transformation
Create 3 loglines that center on breakthrough scientific discoveries

### Approach 2: Human Adaptation Focus  
Core Philosophy: How humans evolve and adapt to technological change
Create 3 loglines that explore human resilience and transformation

### Approach 3: Societal Evolution Focus
Core Philosophy: How social structures adapt to technological reality
Create 3 loglines that examine community and cultural change

## Logline Requirements

Each logline must:
- Be set specifically in {target_year}
- Explore the theme: {human_condition}
- Start with "In {target_year}..."
- Be 1-2 sentences that capture the complete story premise
- Feel authentically native to {target_year} (not retrofitted from 2024)
- Balance scientific grounding with human drama

## Output Format

### Approach 1: Scientific Advancement Focus
**Core Assumption:** Technology as catalyst for human transformation

## Top 3 Selected
1. In {target_year}, [logline 1]
2. In {target_year}, [logline 2]  
3. In {target_year}, [logline 3]

### Approach 2: Human Adaptation Focus
**Core Assumption:** How humans evolve and adapt to technological change

## Top 3 Selected
1. In {target_year}, [logline 4]
2. In {target_year}, [logline 5]
3. In {target_year}, [logline 6]

### Approach 3: Societal Evolution Focus
**Core Assumption:** How social structures adapt to technological reality

## Top 3 Selected
1. In {target_year}, [logline 7]
2. In {target_year}, [logline 8]
3. In {target_year}, [logline 9]

Create 9 compelling, scientifically grounded loglines that authentically belong to {target_year}.
"""

# Used in: create_competitive_outline_direct() - Direct LLM alternative to CS competition
DIRECT_OUTLINE_PROMPT = """Create a detailed chapter-by-chapter outline for a {target_year} science fiction novel.

STORY FOUNDATION:
Outline Prep: {outline_prep_materials}
Refined Story: {refined_story}
Research Findings: {research_findings}
Target Year: {target_year}
Human Condition Theme: {human_condition}

## Outline Requirements

Create a compelling 20-25 chapter novel outline that:
- Maintains authentic {target_year} setting throughout
- Explores {human_condition} through future-native lens
- Integrates research findings naturally into plot
- Balances scientific accuracy with narrative momentum
- Shows realistic character development and world-building

## Chapter Structure Template

For each chapter, provide:

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

## Story Structure

Organize as:
- **Act 1 (Chapters 1-6)**: Setup and world establishment
- **Act 2A (Chapters 7-12)**: Rising action and complications  
- **Act 2B (Chapters 13-18)**: Crisis escalation and major reversals
- **Act 3 (Chapters 19-25)**: Climax, resolution, and new equilibrium

## Integration Guidelines

- All character names must feel authentically evolved by {target_year}
- Technology and social systems must feel naturally developed
- Scientific elements should drive plot organically
- Conflicts and solutions must be impossible in 2024
- Theme exploration should emerge naturally from {target_year} circumstances

Create a comprehensive outline that serves as a roadmap for an engaging, scientifically grounded {target_year} novel.
"""

# Used in: write_first_chapter_competitive_direct() - Direct LLM alternative to CS competition
DIRECT_FIRST_CHAPTER_PROMPT = """Write the opening chapter of a {target_year} science fiction novel.

STORY CONTEXT:
Original User Request: {original_user_request}
Revised Outline: {revised_outline}
Target Year: {target_year}
Tone: {tone}
Human Condition Theme: {human_condition}

## Chapter Requirements

### Opening Chapter Goals
- Establish authentic {target_year} world through character perspective
- Introduce protagonist as native to this future time
- Set tone and style for entire novel
- Hook reader immediately with compelling situation
- Show don't tell how this future works

### Writing Standards
- **Length**: 2500-3000 words
- **Perspective**: Establish consistent narrative voice
- **Pacing**: Balance action with world-building
- **Character Voice**: Authentic to someone raised in {target_year}
- **Scientific Integration**: Natural, not expository

### {target_year} Authenticity Requirements

**Future-Native Elements:**
- Technology that feels naturally evolved from current trends
- Social systems showing realistic cultural adaptation
- Language incorporating believable linguistic evolution
- Environmental details reflecting {target_year} realities
- Character behaviors native to their time period

**Avoid 2024 Anachronisms:**
- Contemporary technology, social media, or cultural references
- Current political systems or figures
- 2024 slang, idioms, or speech patterns
- Modern brand names or companies
- Present-day environmental conditions

### Character and World Integration
- Protagonist thinks, acts, speaks as {target_year} native
- Technology use feels natural and taken-for-granted
- Social customs reflect evolved cultural norms
- Conflicts emerge from {target_year}-specific circumstances
- World details support exploration of: {human_condition}

### Story Opening Strategy
Based on your outline, create an opening that:
- Immediately establishes the story's unique premise
- Introduces compelling character in authentic {target_year} situation
- Sets up the central conflict that will drive the narrative
- Establishes the tone: {tone}
- Begins exploration of {human_condition}

Write Chapter 1 that establishes your novel's world, character, and premise with the authenticity and scientific grounding that could only exist in {target_year}.
"""

# Used in: write_key_chapter_competitive_direct() - Direct LLM alternative to CS competition
DIRECT_KEY_CHAPTER_PROMPT = """Write a KEY chapter requiring high scientific complexity and careful exposition.

CHAPTER CONTEXT:
Chapter Number: {chapter_number}
Scene Brief: {scene_brief}
Previous Chapters Context: {previous_chapters_context}
Research Findings: {research_findings}
Target Year: {target_year}
Human Condition Theme: {human_condition}

## KEY Chapter Requirements

This chapter has been classified as KEY due to:
- Major scientific concepts introduction
- Complex technological exposition required
- Scientific convergence point in the story
- Climactic moments involving science/technology
- Critical plot developments requiring scientific grounding

### Scientific Excellence Standards
- **Research Integration**: Seamlessly weave scientific findings into narrative
- **Technical Accuracy**: Respect current scientific understanding while extrapolating thoughtfully
- **Character Knowledge**: Characters understand science realistically for {target_year}
- **Plot Integration**: Science drives story developments organically

### KEY Chapter Writing Approach
As a scientifically complex chapter, focus on:

**Hard Science Fiction Excellence:**
- Rigorous scientific accuracy in all technical elements
- Realistic cause-and-effect relationships
- Characters with appropriate scientific expertise
- Technical details that enhance rather than overwhelm story

**Science Educator Perspective:**
- Complex concepts explained through character interaction
- Scientific principles made accessible to readers
- Learning moments integrated naturally into dialogue
- Technical exposition balanced with emotional stakes

**Narrative Physicist Approach:**
- Scientific consequences drive plot developments
- Technology limitations create dramatic tension
- Physical laws maintained consistently
- Scientific breakthroughs feel earned and logical

### Chapter Execution
- **Length**: 2500-3000 words
- **Complexity**: Handle scientific material with sophistication
- **Accessibility**: Keep complex concepts understandable
- **Integration**: Science serves character and plot goals
- **Authenticity**: Maintain {target_year} native perspective

### Scene Brief Integration
Follow your scene brief while bringing KEY chapter excellence:
{scene_brief}

### Scientific Grounding
Incorporate relevant research findings naturally:
- Use established scientific principles from research
- Show realistic development pathways to {target_year}
- Maintain consistency with previously established science
- Address implications and consequences thoughtfully

Write Chapter {chapter_number} as a scientifically sophisticated, narratively compelling KEY chapter that advances both plot and scientific understanding.
"""

