# Co-Scientist Competition Prompts
# Following the methodology from Google's AI co-scientist paper
# Enhanced with templates for different use cases

# === Template Management Functions ===

def get_meta_analysis_prompt(use_case: str, state: dict) -> str:
    """Get the appropriate meta-analysis prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_META_ANALYSIS_PROMPT,
        "storyline_creation": STORYLINE_META_ANALYSIS_PROMPT,
        "chapter_writing": STORYLINE_META_ANALYSIS_PROMPT,  # Same template for both
        "chapter_rewriting": CHAPTER_META_ANALYSIS_PROMPT,
        "character_development": CHARACTER_META_ANALYSIS_PROMPT,
        "linguistic_evolution": RESEARCH_META_ANALYSIS_PROMPT,
        "storyline_adjustment": NARRATIVE_META_ANALYSIS_PROMPT,
    }
    
    # Special handling for scenario generation with storyline context
    if use_case == "scenario_generation":
        if state.get("research_context") and state.get("storyline"):
            # Use storyline-based prompt (storyline always exists in current workflow)
            return INITIAL_META_ANALYSIS_PROMPT.format(
                storyline=state.get("storyline"),
                research_context=state.get("research_context"),
                target_year=state.get("target_year", "future")
            )
    
    # Other use cases use flexible format
    template = templates.get(use_case)
    if not template:
        raise ValueError(f"No template found for use_case: {use_case}")
        
    return template.format(
        task_description=state.get("task_description", ""),
        context=state.get("context", ""),
        reference_material=state.get("reference_material", ""),
        domain_context=state.get("domain_context", "")
    )

def get_generation_prompt(use_case: str, state: dict, direction: dict, team_id: str) -> str:
    """Get the appropriate generation prompt for the use case."""
    templates = {
        "scenario_generation": INITIAL_SCENARIO_GENERATION_PROMPT,
        "storyline_creation": STORYLINE_GENERATION_PROMPT,
        "chapter_writing": CHAPTER_WRITING_GENERATION_PROMPT,
        "chapter_rewriting": CHAPTER_GENERATION_PROMPT,
        "character_development": CHARACTER_GENERATION_PROMPT,
        "linguistic_evolution": RESEARCH_GENERATION_PROMPT,
        "storyline_adjustment": NARRATIVE_GENERATION_PROMPT,
    }
    
    template = templates.get(use_case)
    if not template:
        raise ValueError(f"No template found for use_case: {use_case}")
    
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
    
    # New flexible format
    return template.format(
        direction_name=direction.get("name", ""),
        direction_assumption=direction.get("assumption", ""),
        team_id=team_id,
        task_description=state.get("task_description", ""),
        context=state.get("context", ""),
        reference_material=state.get("reference_material", ""),
        domain_context=state.get("domain_context", "")
    )

# === Meta-Analysis Phase ===

# Used in: get_meta_analysis_prompt() for "scenario_generation" use case when storyline is available
INITIAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for scenario competition.

<Task>
Analyze the provided story context and research questions to identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures.
</Task>

<Story Context>
{storyline}
</Story Context>

<World-Building Questions>
{research_context}
</World-Building Questions>

<Target Year>
{target_year}
</Target Year>

<Requirements>
- Each direction must be scientifically plausible but represent different development paths
- All directions should address ALL the world-building questions, not focus on just one aspect
- Different core assumptions about technological development
- Different but equally plausible scientific trajectories  
- Different implications for society, energy, transport, communication, etc.
- Meaningful variety for storytelling purposes
</Requirements>

<Process>
1. Identify key technological choice points in the story that could develop in different directions
2. Create 3 distinct research directions based on different assumptions about which technologies/approaches will dominate
3. Ensure each direction is scientifically plausible but represents different development paths
4. Each direction should address ALL the world-building questions, not focus on just one aspect
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
- Address the complete scope of world-building questions in each direction
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
{research_context}
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
- Different implications for how society, energy, transport, communication, etc. will develop
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
Your scenario must address:
- Energy systems and distribution
- Transportation networks and technology
- Communication and information systems
- Social structures and governance
- Economic systems and resource allocation
- Scientific/technological capabilities
- Environmental conditions and sustainability
- Human enhancement and medical technology
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

Your scenario must show evolution in:
- Energy systems and distribution
- Transportation networks and technology
- Communication and information systems
- Social structures and governance
- Economic systems and resource allocation
- Scientific/technological capabilities
- Environmental conditions and sustainability
- Human enhancement and medical technology

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

# Used in: get_meta_analysis_prompt() for "storyline_creation" and "chapter_writing" use cases
STORYLINE_META_ANALYSIS_PROMPT = """You are a master storyteller and narrative expert tasked with identifying distinct storytelling approaches.

<Task>
Analyze the story requirements and identify 2 fundamentally different narrative approaches that would lead to meaningfully different storylines.
</Task>

<User's Story Idea>
{context}
</User's Story Idea>

<Task Description>
{task_description}
</Task Description>

<Reference Material>
{reference_material}
</Reference Material>

<Genre/Style Context>
{domain_context}
</Genre/Style Context>

<Requirements>
- Each approach must be literarily sound but represent different creative paths
- Address the full story requirements and user's vision
- Different core assumptions about narrative focus (character vs plot vs theme vs setting)
- Different but equally valid creative directions
- Different implications for story structure, character development, and reader engagement
- Meaningful variety for storytelling purposes
</Requirements>

<Process>
1. Identify key narrative choice points that could be developed in different directions
2. Create 2 distinct storytelling approaches based on different core assumptions about narrative style, focus, or structure
3. Ensure each approach is literarily sound but represents different creative paths
4. Each approach should address the full story requirements and user's vision
</Process>

<Output Format>
Direction 1: [Name]
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name]
Core Assumption: [Key narrative assumption] 
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 2 approaches provide meaningful variety while remaining literarily sound]
</Output Format>

<Reminders>
- Focus on narrative choice points that create meaningful differentiation
- Ensure both approaches remain literarily sound and compelling
- Address the user's complete vision while exploring different creative directions
</Reminders>
"""

# Used in: get_generation_prompt() for "storyline_creation" use case
STORYLINE_GENERATION_PROMPT = """You are a master storyteller creating a compelling storyline.

<Narrative Approach>
{direction_name}
</Narrative Approach>

<Core Assumption>
{direction_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<User's Story Idea>
{context}
</User's Story Idea>

<Reference Material>
{reference_material}
</Reference Material>

<Genre/Style Context>
{domain_context}
</Genre/Style Context>

<Requirements>
- Engaging and compelling for readers
- Structurally sound with good pacing
- Character-driven with authentic development
- Complete with clear plot progression
- Demonstrates mastery of storytelling craft
</Requirements>

<Process>
1. Analyze the user's story idea to understand their vision and requirements
2. Apply your narrative approach to develop a complete storyline
3. Ground every creative choice in established storytelling principles and techniques
4. Create compelling characters, engaging plot structure, and meaningful themes
5. Consider the impact on reader engagement and narrative effectiveness
</Process>

<Content Requirements>
Your storyline must include:
- Main plot points and story arc
- Key character development and relationships
- Subplots that enhance the main narrative
- Clear beginning, middle, and end structure
- Compelling conflicts and resolutions
- Thematic elements that resonate with readers
</Content Requirements>

<Storytelling Methodology>
- Start with your core narrative assumption as the foundation
- Apply proven storytelling techniques that support this approach
- Create authentic characters with clear motivations and growth arcs
- Develop plot events that naturally flow from character decisions and conflicts
- Ensure thematic coherence throughout the narrative
</Storytelling Methodology>

<Reminders>
- Stay true to your assigned narrative approach while serving the user's vision
- Ensure authentic character development and compelling plot progression
- Maintain thematic coherence and reader engagement throughout
</Reminders>
"""

# Used in: get_generation_prompt() for "chapter_writing" use case
CHAPTER_WRITING_GENERATION_PROMPT = """You are a skilled novelist writing an engaging chapter.

<Narrative Approach>
{direction_name}
</Narrative Approach>

<Core Assumption>
{direction_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<Requirements and Context>
{context}
</Requirements and Context>

<Reference Material>
{reference_material}
</Reference Material>

<Genre/Style Context>
{domain_context}
</Genre/Style Context>

<Instructions>
1. Analyze the storyline and chapter requirements to understand the narrative goals
2. Apply your narrative approach to write a complete first chapter
3. Ground every creative choice in established writing techniques and literary craft
4. Create compelling characters, vivid descriptions, and engaging dialogue
5. Consider the impact on reader engagement, character introduction, and story setup

Your chapter must accomplish:
- Hook readers immediately with compelling opening
- Establish protagonist voice and character
- Introduce key setting and world elements
- Set up central conflict or tension
- Advance plot while building character
- Create atmosphere and tone for the story

Writing Methodology:
- Start with your core assumption as the foundation
- Apply proven techniques for opening chapters and reader engagement
- Create authentic dialogue that reveals character and advances plot
- Use vivid, specific descriptions that immerse readers in the world
- Balance action, dialogue, and exposition effectively

Generate a complete first chapter that is:
- Immediately engaging and hooks readers
- Well-paced with strong narrative flow
- Rich in character development and voice
- Establishes story world and conflict clearly
- Demonstrates excellent prose craft and storytelling
</Instructions>
"""

# === Chapter Rewriting Templates ===

# Used in: get_meta_analysis_prompt() for "chapter_rewriting" use case
CHAPTER_META_ANALYSIS_PROMPT = """You are an expert literary analyst tasked with identifying distinct narrative approaches for competitive chapter rewriting.

<Task>
Analyze the task requirements and identify 3 fundamentally different narrative/stylistic approaches that would lead to meaningfully different chapter versions.
</Task>

<Task Description>
{task_description}
</Task Description>

<Context and Requirements>
{context}
</Context and Requirements>

<Current Chapter Content>
{reference_material}
</Current Chapter Content>

<Genre/Domain Context>
{domain_context}
</Genre/Domain Context>

<Instructions>
1. Identify key narrative choice points that could be developed in different directions
2. Create 3 distinct approaches based on different assumptions about narrative style, pacing, character focus, etc.
3. Ensure each approach is literarily sound but represents different creative paths
4. Each approach should address the full task requirements

Requirements for good narrative approaches:
- Different core assumptions about narrative style and structure
- Different but equally valid creative directions  
- Different implications for character development, pacing, tension, etc.
- Meaningful variety for storytelling purposes

Format your response as:
Direction 1: [Name]
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name] 
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Direction 3: [Name]
Core Assumption: [Key narrative assumption] 
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 3 approaches provide meaningful variety while remaining literarily sound]
</Instructions>
"""

# Used in: get_generation_prompt() for "chapter_rewriting" use case
CHAPTER_GENERATION_PROMPT = """You are a skilled writer conducting a comprehensive approach to chapter rewriting.

<Narrative Approach>
{direction_name}
</Narrative Approach>

<Core Assumption>
{direction_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<Requirements>
{context}
</Requirements>

<Current Chapter>
{reference_material}
</Current Chapter>

<Genre Context>
{domain_context}
</Genre Context>

<Instructions>
1. Analyze the current chapter to understand its role in the larger narrative
2. Apply your narrative approach to rewrite the chapter completely
3. Ground every creative choice in established literary techniques and genre conventions
4. Maintain consistency with the overall story while implementing your approach
5. Consider the impact on character development, plot progression, and reader engagement

Your rewrite must address:
- Character development and dialogue
- Narrative structure and pacing
- Descriptive language and prose style
- Plot advancement and tension
- Thematic elements and mood
- Reader engagement and emotional impact

Creative Methodology:
- Start with your core assumption as the foundation
- Research current literary techniques supporting this approach
- Apply established narrative principles realistically
- Consider implementation challenges and reader expectations
- Address potential weaknesses and how they're overcome

Generate a comprehensive chapter rewrite that is:
- Literarily grounded in established techniques
- Consistent with character and plot requirements
- Specific and complete in implementation
- Realistic about genre and audience expectations
- Aware of narrative and emotional implications
</Instructions>
"""

# === Character Development Templates ===

# Used in: get_meta_analysis_prompt() for "character_development" use case
CHARACTER_META_ANALYSIS_PROMPT = """You are an expert character development analyst tasked with identifying distinct approaches for competitive character enhancement.

<Task>
Analyze the character requirements and identify 3 fundamentally different development approaches that would lead to meaningfully different character versions.
</Task>

<Task Description>
{task_description}
</Task Description>

<Context and Requirements>
{context}
</Context and Requirements>

<Current Character Material>
{reference_material}
</Current Character Material>

<Genre/Domain Context>
{domain_context}
</Genre/Domain Context>

<Instructions>
1. Identify key character development choice points that could be explored in different directions
2. Create 3 distinct approaches based on different assumptions about psychology, motivation, narrative function, etc.
3. Ensure each approach is psychologically sound but represents different creative paths
4. Each approach should address the full character requirements

Requirements for good character approaches:
- Different core assumptions about character psychology and motivation
- Different but equally valid development directions  
- Different implications for character arc, relationships, and narrative role
- Meaningful variety for character depth and complexity

Format your response as:
Direction 1: [Name]
Core Assumption: [Key character assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name] 
Core Assumption: [Key character assumption]
Focus: [What this approach emphasizes]

Direction 3: [Name]
Core Assumption: [Key character assumption] 
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 3 approaches provide meaningful variety while remaining psychologically sound]
</Instructions>
"""

# Used in: get_generation_prompt() for "character_development" use case
CHARACTER_GENERATION_PROMPT = """You are a skilled character developer conducting a comprehensive approach to character enhancement.

<Character Approach>
{direction_name}
</Character Approach>

<Core Assumption>
{direction_assumption}
</Core Assumption>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<Requirements>
{context}
</Requirements>

<Current Character>
{reference_material}
</Current Character>

<Genre Context>
{domain_context}
</Genre Context>

<Instructions>
1. Analyze the current character to understand their role and existing development
2. Apply your character approach to enhance the character comprehensively
3. Ground every development choice in established psychological principles and narrative techniques
4. Maintain consistency with the story while implementing your approach
5. Consider the impact on character relationships, plot function, and reader connection

Your development must address:
- Character psychology and inner life
- Motivations and goals
- Character arc and growth
- Relationships and interactions
- Dialogue and voice
- Narrative function and story role

Development Methodology:
- Start with your core assumption as the foundation
- Research current character development techniques supporting this approach
- Apply established psychological and narrative principles realistically
- Consider implementation challenges and story requirements
- Address potential weaknesses and how they're overcome

Generate a comprehensive character development that is:
- Psychologically grounded in established principles
- Consistent with story and genre requirements
- Specific and complete in implementation
- Realistic about character and narrative expectations
- Aware of emotional and story implications
</Instructions>
"""

# === Research and Analysis Templates ===

# Used in: get_meta_analysis_prompt() for "linguistic_evolution" use case
RESEARCH_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research approaches for competitive analysis.

<Task>
Analyze the task requirements and identify 2 fundamentally different research methodologies that would lead to meaningfully different analytical outcomes.
</Task>

<Task Description>
{task_description}
</Task Description>

<Context and Requirements>
{context}
</Context and Requirements>

<Reference Material>
{reference_material}
</Reference Material>

<Domain Context>
{domain_context}
</Domain Context>

<Instructions>
1. Identify key analytical choice points that could be approached in different directions
2. Create 2 distinct research approaches based on different core assumptions about methodology
3. Ensure each approach is academically sound but represents different research perspectives
4. Each approach should address the full research requirements

Requirements for good research approaches:
- Different core assumptions about research methodology or analytical framework
- Different but equally valid academic perspectives
- Different implications for depth, scope, and analytical outcomes
- Meaningful variety for comprehensive analysis

Format your response as:
Direction 1: [Name]
Core Assumption: [Key methodological assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name]
Core Assumption: [Key methodological assumption]
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 2 approaches provide meaningful variety while remaining academically sound]
</Instructions>
"""

# Used in: get_generation_prompt() for "linguistic_evolution" use case
RESEARCH_GENERATION_PROMPT = """You are a research team conducting comprehensive academic analysis.

<Research Approach>
{direction_name}
</Research Approach>

<Core Methodology>
{direction_assumption}
</Core Methodology>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<Research Context>
{context}
</Research Context>

<Reference Material>
{reference_material}
</Reference Material>

<Domain>
{domain_context}
</Domain>

<Instructions>
1. Apply your research methodology to conduct thorough analysis
2. Ground every finding in current academic literature and research
3. Consider multiple perspectives and interdisciplinary insights
4. Address all aspects of the research requirements systematically
5. Provide evidence-based conclusions and recommendations

Research Methodology:
- Use your core methodology as the analytical framework
- Integrate relevant academic theories and current research
- Consider empirical evidence and case studies
- Address potential limitations and alternative interpretations
- Provide clear, well-supported conclusions

Generate a comprehensive research analysis that is:
- Methodologically rigorous and academically sound
- Well-supported by current literature and evidence
- Internally consistent with your analytical framework
- Thorough in addressing all research requirements
- Clear and accessible for academic and practical application
</Instructions>
"""

# === Narrative Revision Templates ===

# Used in: get_meta_analysis_prompt() for "storyline_adjustment" use case  
NARRATIVE_META_ANALYSIS_PROMPT = """You are an expert narrative analyst tasked with identifying distinct revision approaches for competitive storyline development.

<Task>
Analyze the narrative requirements and identify 2 fundamentally different revision strategies that would lead to meaningfully different storyline outcomes.
</Task>

<Task Description>
{task_description}
</Task Description>

<Context and Requirements>
{context}
</Context and Requirements>

<Reference Material>
{reference_material}
</Reference Material>

<Domain Context>
{domain_context}
</Domain Context>

<Instructions>
1. Identify key narrative choice points that could be revised in different directions
2. Create 2 distinct revision approaches based on different core assumptions about narrative priority
3. Ensure each approach is literarily sound but represents different creative perspectives
4. Each approach should address the full revision requirements

Requirements for good revision approaches:
- Different core assumptions about narrative focus (structure vs character vs theme vs world-building)
- Different but equally valid creative directions
- Different implications for story flow, character development, and thematic coherence
- Meaningful variety for narrative enhancement

Format your response as:
Direction 1: [Name]
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name]
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 2 approaches provide meaningful variety while remaining literarily sound]
</Instructions>
"""

# Used in: get_generation_prompt() for "storyline_adjustment" use case
NARRATIVE_GENERATION_PROMPT = """You are a narrative development team specializing in storyline revision and enhancement.

<Revision Approach>
{direction_name}
</Revision Approach>

<Core Philosophy>
{direction_assumption}
</Core Philosophy>

<Team ID>
{team_id}
</Team ID>

<Task>
{task_description}
</Task>

<Revision Context>
{context}
</Revision Context>

<Reference Material>
{reference_material}
</Reference Material>

<Genre/Style>
{domain_context}
</Genre/Style>

<Instructions>
1. Apply your revision philosophy to enhance the storyline systematically
2. Maintain narrative coherence while integrating new elements
3. Ensure character consistency and development throughout
4. Balance plot structure with thematic depth
5. Create engaging, well-paced narrative flow

Revision Methodology:
- Use your core philosophy as the guiding principle
- Integrate new elements seamlessly with existing narrative
- Maintain character voice and development consistency
- Ensure thematic coherence and meaningful progression
- Address pacing, tension, and reader engagement

Generate a comprehensive revised storyline that is:
- Narratively coherent and well-structured
- Character-consistent with clear development arcs
- Thematically rich and meaningfully integrated
- Engaging with appropriate pacing and tension
- Seamlessly incorporating required new elements
</Instructions>
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
- Consideration of fundamental physical/biological/engineering constraints
- Internal consistency within your domain
- Integration with other technological systems
</Evaluation Criteria>

<Process>
1. Identify scientific inaccuracies, implausible claims, or logical inconsistencies
2. Assess whether the technological timelines are realistic
3. Consider if the scenario accounts for known constraints in your field
4. Suggest specific improvements to make the scenario more scientifically sound
</Process>

<Domain Focus Areas>
Physics: Energy conservation, thermodynamics, materials science limits, fundamental physical constraints
Biology: Evolutionary timescales, biological constraints, medical/genetic plausibility, ecosystem impacts
Engineering: Manufacturing feasibility, scalability, infrastructure requirements, implementation challenges
Social Science: Human behavior patterns, social system evolution, adoption curves, cultural factors
Economics: Market dynamics, resource allocation, economic incentives, cost-benefit analysis
</Domain Focus Areas>

<Output Requirements>
Provide:
1. Overall assessment of scientific rigor in your domain
2. Specific issues identified with detailed explanations
3. Suggestions for improvement
4. Severity score (1-10) where 10 = major scientific problems that invalidate the scenario
</Output Requirements>

<Reminders>
- Focus specifically on your domain expertise
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

<Domain Focus Areas>
narrative_structure: Plot coherence with world rules, story pacing that reflects world constraints
world_building: Consistency with established systems, authentic use of world elements
character_development: Characters behaving authentically within world constraints
thematic_coherence: Themes that emerge naturally from the world state
world_integration: Seamless integration of world elements into narrative
linguistic_consistency: Proper use of evolved language and cultural expressions
prose_style: Writing style that reflects the world's tone and atmosphere
</Domain Focus Areas>

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
- Narrative potential and story opportunities
- Originality and creative insight
- Detail richness and implementability
</Evaluation Criteria>

<Process>
The discussion will unfold in 3-5 structured turns:

Turn 1: Begin with a concise summary of both scenarios and their core approaches
Subsequent turns:
- Critically evaluate each scenario against the stated criteria
- Compare scientific rigor and evidence grounding
- Assess internal consistency and logical coherence
- Evaluate narrative potential and creative merit
- Identify specific strengths and weaknesses
</Process>

<Evaluation Aspects>
- Potential for scientific correctness/validity
- Practical applicability and implementation feasibility
- Sufficiency of detail and specificity
- Novelty and originality
- Desirability for story development
</Evaluation Aspects>

<Output Format>
Conduct the structured discussion analysis, then provide a conclusive judgment with clear rationale.

Then indicate the superior scenario by writing: "better scenario: 1" or "better scenario: 2"
</Output Format>

<Reminders>
- Provide thorough comparative analysis before making a decision
- Consider both scientific rigor and narrative potential
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

