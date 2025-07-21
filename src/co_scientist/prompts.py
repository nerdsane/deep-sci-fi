# Co-Scientist Competition Prompts
# Following the methodology from Google's AI co-scientist paper
# Enhanced with templates for different use cases

###################
# Template Management
###################

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
    
    # Special handling for scenario generation
    if use_case == "scenario_generation":
        if state.get("research_context") and state.get("storyline"):
            # Use storyline-based prompt when we have a storyline
            return INITIAL_META_ANALYSIS_PROMPT.format(
                storyline=state.get("storyline"),
                research_context=state.get("research_context"),
                target_year=state.get("target_year", "future")
            )
        elif state.get("context"):
            # Use research-based prompt when we have research questions but no storyline
            return INITIAL_RESEARCH_META_ANALYSIS_PROMPT.format(
                context=state.get("context"),
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

###################
# Meta-Analysis Phase
###################

# Used in: get_meta_analysis_prompt() for "scenario_generation" use case when storyline is available
INITIAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for scenario competition.

Your goal is to analyze the provided story context and research questions to identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures.

Story Context:
{storyline}

World-Building Questions:
{research_context}

Target Year: {target_year}

Instructions:
1. Identify key technological choice points in the story that could develop in different directions
2. Create 3 distinct research directions based on different assumptions about which technologies/approaches will dominate
3. Ensure each direction is scientifically plausible but represents different development paths
4. Each direction should address ALL the world-building questions, not focus on just one aspect

Requirements for good research directions:
- Different core assumptions about technological development
- Different but equally plausible scientific trajectories  
- Different implications for society, energy, transport, communication, etc.
- Meaningful variety for storytelling purposes

Format your response as:
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
"""

# Used in: get_meta_analysis_prompt() for "scenario_generation" use case when no storyline is available
INITIAL_RESEARCH_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for future scenario development.

Your goal is to analyze the provided research questions and identify 3 fundamentally different technological/scientific assumption sets that would lead to meaningfully different futures.

Research Questions:
{context}

Target Year: {target_year}

Instructions:
1. Identify key technological choice points from the research questions that could develop in different directions
2. Create 3 distinct research directions based on different assumptions about which technologies/approaches will dominate
3. Ensure each direction is scientifically plausible but represents different development paths
4. Each direction should address ALL the research questions, not focus on just one aspect

Requirements for good research directions:
- Different core assumptions about technological development
- Different but equally plausible scientific trajectories  
- Different implications for society, energy, transport, communication, etc.
- Meaningful variety for future scenario storytelling

Format your response as:
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
"""

# Used in: meta_analysis_phase() for scenario generation with baseline world state
INCREMENTAL_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research directions for evolutionary scenario competition.

Your goal is to analyze the current world state and identify 3 fundamentally different evolutionary paths that could develop over the specified time period.

Story Context:
{storyline}

World-Building Questions:
{research_context}

Current Baseline World State: {baseline_world_state}
Years to Project Forward: {years_in_future}

Instructions:
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
"""

###################
# Generation Phase  
###################

# Used in: get_generation_prompt() for "scenario_generation" use case (legacy format)
INITIAL_SCENARIO_GENERATION_PROMPT = """You are a research team conducting rigorous scientific analysis to develop a comprehensive world-building scenario for the target year.

Research Direction: {research_direction}
Core Assumption: {core_assumption}
Team ID: {team_id}

World-Building Questions to Address:
{research_context}

Story Context: {storyline}
Target Year: {target_year}

Instructions:
1. Conduct deep research on current scientific trends that support your core assumption
2. Develop a complete scenario that addresses ALL the world-building questions
3. Ground every technological claim in current research or plausible extrapolation
4. Maintain internal consistency across all aspects of the world
5. Consider second-order effects and systemic implications

Your scenario must address:
- Energy systems and distribution
- Transportation networks and technology
- Communication and information systems
- Social structures and governance
- Economic systems and resource allocation
- Scientific/technological capabilities
- Environmental conditions and sustainability
- Human enhancement and medical technology

Research Methodology:
- Start with your core assumption as the foundation
- Research current scientific literature supporting this path
- Extrapolate realistically to the target year
- Consider implementation challenges and timelines
- Address potential obstacles and how they're overcome

Generate a comprehensive scenario that is:
- Scientifically grounded in current research
- Internally consistent across all systems
- Specific enough for narrative development
- Realistic about technological timelines
- Aware of social and economic implications

Scenario Content:
"""

# Used in: generate_single_scenario() for scenario generation with baseline world state
INCREMENTAL_SCENARIO_GENERATION_PROMPT = """You are a research team conducting rigorous scientific analysis to project how the world will evolve from an established baseline state.

Research Direction: {research_direction}
Core Assumption: {core_assumption}
Team ID: {team_id}

World-Building Questions to Address:
{research_context}

Story Context: {storyline}
Current Baseline World State: {baseline_world_state}
Years to Project Forward: {years_in_future}

Instructions:
1. Analyze the current baseline world state to understand the starting point
2. Apply your research direction's core assumption to project forward {years_in_future} years
3. Develop evolutionary changes that build logically on the established baseline
4. Ground every technological claim in current research or plausible extrapolation
5. Maintain consistency with the established world while showing realistic progression

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

Scenario Content:
"""

###################
# Chapter Rewriting Templates
###################

# Used in: get_meta_analysis_prompt() for "chapter_rewriting" use case
CHAPTER_META_ANALYSIS_PROMPT = """You are an expert literary analyst tasked with identifying distinct narrative approaches for competitive chapter rewriting.

Your goal is to analyze the task requirements and identify 3 fundamentally different narrative/stylistic approaches that would lead to meaningfully different chapter versions.

Task Description: {task_description}
Context and Requirements: {context}
Current Chapter Content: {reference_material}
Genre/Domain Context: {domain_context}

Instructions:
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
"""

# Used in: get_generation_prompt() for "chapter_rewriting" use case
CHAPTER_GENERATION_PROMPT = """You are a skilled writer conducting a comprehensive approach to chapter rewriting.

Narrative Approach: {direction_name}
Core Assumption: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
Requirements: {context}
Current Chapter: {reference_material}
Genre Context: {domain_context}

Instructions:
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

Chapter Content:
"""

###################
# Character Development Templates
###################

# Used in: get_meta_analysis_prompt() for "character_development" use case
CHARACTER_META_ANALYSIS_PROMPT = """You are an expert character development analyst tasked with identifying distinct approaches for competitive character enhancement.

Your goal is to analyze the character requirements and identify 3 fundamentally different development approaches that would lead to meaningfully different character versions.

Task Description: {task_description}
Context and Requirements: {context}
Current Character Material: {reference_material}
Genre/Domain Context: {domain_context}

Instructions:
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
"""

# Used in: get_generation_prompt() for "character_development" use case
CHARACTER_GENERATION_PROMPT = """You are a skilled character developer conducting a comprehensive approach to character enhancement.

Character Approach: {direction_name}
Core Assumption: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
Requirements: {context}
Current Character: {reference_material}
Genre Context: {domain_context}

Instructions:
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

Character Content:
"""



# Generic Storyline Template
# Used in: get_meta_analysis_prompt() for "storyline_creation" and "chapter_writing" use cases
STORYLINE_META_ANALYSIS_PROMPT = """You are a master storyteller and narrative expert tasked with identifying distinct storytelling approaches.

Your goal is to analyze the story requirements and identify 2 fundamentally different narrative approaches that would lead to meaningfully different storylines.

Task Description: {task_description}
User's Story Idea: {context}
Reference Material: {reference_material}
Genre/Style Context: {domain_context}

Instructions:
1. Identify key narrative choice points that could be developed in different directions
2. Create 2 distinct storytelling approaches based on different core assumptions about narrative style, focus, or structure
3. Ensure each approach is literarily sound but represents different creative paths
4. Each approach should address the full story requirements and user's vision

Requirements for good storytelling approaches:
- Different core assumptions about narrative focus (character vs plot vs theme vs setting)
- Different but equally valid creative directions
- Different implications for story structure, character development, and reader engagement
- Meaningful variety for storytelling purposes

Format your response as:
Direction 1: [Name]
Core Assumption: [Key narrative assumption]
Focus: [What this approach emphasizes]

Direction 2: [Name]
Core Assumption: [Key narrative assumption] 
Focus: [What this approach emphasizes]

Reasoning: [Explain why these 2 approaches provide meaningful variety while remaining literarily sound]
"""

# Used in: get_generation_prompt() for "storyline_creation" use case
STORYLINE_GENERATION_PROMPT = """You are a master storyteller creating a compelling storyline.

Narrative Approach: {direction_name}
Core Assumption: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
User's Story Idea: {context}
Reference Material: {reference_material}
Genre/Style Context: {domain_context}

Instructions:
1. Analyze the user's story idea to understand their vision and requirements
2. Apply your narrative approach to develop a complete storyline
3. Ground every creative choice in established storytelling principles and techniques
4. Create compelling characters, engaging plot structure, and meaningful themes
5. Consider the impact on reader engagement and narrative effectiveness

Your storyline must include:
- Main plot points and story arc
- Key character development and relationships
- Subplots that enhance the main narrative
- Clear beginning, middle, and end structure
- Compelling conflicts and resolutions
- Thematic elements that resonate with readers

Storytelling Methodology:
- Start with your core narrative assumption as the foundation
- Apply proven storytelling techniques that support this approach
- Create authentic characters with clear motivations and growth arcs
- Develop plot events that naturally flow from character decisions and conflicts
- Ensure thematic coherence throughout the narrative

Generate a comprehensive storyline that is:
- Engaging and compelling for readers
- Structurally sound with good pacing
- Character-driven with authentic development
- Complete with clear plot progression
- Demonstrates mastery of storytelling craft

Storyline Content:
"""

# Used in: get_generation_prompt() for "chapter_writing" use case
CHAPTER_WRITING_GENERATION_PROMPT = """You are a skilled novelist writing an engaging opening chapter.

Narrative Approach: {direction_name}
Core Assumption: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
Requirements and Context: {context}
Reference Material: {reference_material}
Genre/Style Context: {domain_context}

Instructions:
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

Chapter Content:
"""

###################
# Reflection Phase  
###################

# Used in: generate_domain_critique() function for scientific analysis of scenarios
DOMAIN_CRITIQUE_PROMPT = """You are a {critique_domain} expert providing rigorous scientific critique of a world-building scenario.

Scenario ID: {scenario_id}
Research Direction: {research_direction}

Scenario to Critique:
{scenario_content}

Your Expertise: {critique_domain}

Instructions:
1. Evaluate this scenario specifically from your domain expertise
2. Identify scientific inaccuracies, implausible claims, or logical inconsistencies
3. Assess whether the technological timelines are realistic
4. Consider if the scenario accounts for known constraints in your field
5. Suggest specific improvements to make the scenario more scientifically sound

Evaluation Criteria:
- Scientific accuracy and plausibility
- Realistic timelines for technological development
- Consideration of fundamental physical/biological/engineering constraints
- Internal consistency within your domain
- Integration with other technological systems

Focus Areas for {critique_domain}:
Physics: Energy conservation, thermodynamics, materials science limits, fundamental physical constraints
Biology: Evolutionary timescales, biological constraints, medical/genetic plausibility, ecosystem impacts
Engineering: Manufacturing feasibility, scalability, infrastructure requirements, implementation challenges
Social Science: Human behavior patterns, social system evolution, adoption curves, cultural factors
Economics: Market dynamics, resource allocation, economic incentives, cost-benefit analysis

Provide:
1. Overall assessment of scientific rigor in your domain
2. Specific issues identified with detailed explanations
3. Suggestions for improvement
4. Severity score (1-10) where 10 = major scientific problems that invalidate the scenario

Critique:
"""



###################
# Tournament Phase
###################

# Used in: pairwise_comparison() function for head-to-head scenario tournaments
PAIRWISE_RANKING_PROMPT = """You are an expert in comparative analysis, simulating a panel of domain experts engaged in structured discussion to evaluate two competing world-building scenarios.

The objective is to rigorously determine which scenario is superior based on scientific grounding and narrative potential.

Goal: Select the most scientifically rigorous and compelling scenario for sci-fi world-building

Criteria for superiority:
- Scientific plausibility and evidence grounding
- Internal consistency across all systems  
- Realistic technological timelines
- Consideration of second-order effects
- Narrative potential and story opportunities
- Originality and creative insight
- Detail richness and implementability

Scenario 1:
{scenario1_content}
Research Direction: {direction1}

Scenario 2:
{scenario2_content}
Research Direction: {direction2}

Debate procedure:
The discussion will unfold in 3-5 structured turns:

Turn 1: Begin with a concise summary of both scenarios and their core approaches
Subsequent turns:
- Critically evaluate each scenario against the stated criteria
- Compare scientific rigor and evidence grounding
- Assess internal consistency and logical coherence
- Evaluate narrative potential and creative merit
- Identify specific strengths and weaknesses

Evaluation aspects:
- Potential for scientific correctness/validity
- Practical applicability and implementation feasibility
- Sufficiency of detail and specificity
- Novelty and originality
- Desirability for story development

Termination and judgment:
Once the discussion reaches sufficient depth, provide a conclusive judgment with clear rationale.

Then indicate the superior scenario by writing: "better scenario: 1" or "better scenario: 2"

Comparative Analysis:
"""





###################
# Final Selection
###################

# Used in: final_meta_review_phase() function for process analysis and optimization insights
META_REVIEW_PROMPT = """You are a meta-review agent analyzing the co-scientist competition process to synthesize insights and optimize future performance.

Competition Process Data:
{competition_summary}

Tournament Results from Each Direction:
{direction_winners_summary}

Competition Process Analysis:
{tournament_data}
{reflection_data}
{evolution_data}

Your Role as Meta-Review Agent:
1. Synthesize insights from all reviews and competition phases
2. Identify recurring patterns in tournament debates and agent performance
3. Analyze the effectiveness of different approaches and methodologies
4. Generate optimization recommendations for subsequent iterations
5. Create a comprehensive research overview of the competition process

Process Analysis Framework:
- Competition methodology effectiveness
- Quality patterns across different approaches
- Agent performance and decision-making patterns
- Tournament reasoning quality and consistency
- Areas for process improvement and optimization

DO NOT select winners - that is for user choice. Focus on process synthesis.

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

This analysis will optimize future co-scientist performance and enhance the quality of subsequent iterations.
"""

###################
# Research and Narrative Use Cases
###################

# Used in: get_meta_analysis_prompt() for "linguistic_evolution" use case
RESEARCH_META_ANALYSIS_PROMPT = """You are an expert meta-analyst tasked with identifying distinct research approaches for competitive analysis.

Your goal is to analyze the task requirements and identify 2 fundamentally different research methodologies that would lead to meaningfully different analytical outcomes.

Task Description: {task_description}
Context and Requirements: {context}
Reference Material: {reference_material}
Domain Context: {domain_context}

Instructions:
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
"""

# Used in: get_generation_prompt() for "linguistic_evolution" use case
RESEARCH_GENERATION_PROMPT = """You are a research team conducting comprehensive academic analysis.

Research Approach: {direction_name}
Core Methodology: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
Research Context: {context}
Reference Material: {reference_material}
Domain: {domain_context}

Instructions:
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

Analysis Content:
"""

# Used in: get_meta_analysis_prompt() for "storyline_adjustment" use case  
NARRATIVE_META_ANALYSIS_PROMPT = """You are an expert narrative analyst tasked with identifying distinct revision approaches for competitive storyline development.

Your goal is to analyze the narrative requirements and identify 2 fundamentally different revision strategies that would lead to meaningfully different storyline outcomes.

Task Description: {task_description}
Context and Requirements: {context}
Reference Material: {reference_material}
Domain Context: {domain_context}

Instructions:
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
"""

# Used in: get_generation_prompt() for "storyline_adjustment" use case
NARRATIVE_GENERATION_PROMPT = """You are a narrative development team specializing in storyline revision and enhancement.

Revision Approach: {direction_name}
Core Philosophy: {direction_assumption}
Team ID: {team_id}

Task: {task_description}
Revision Context: {context}
Reference Material: {reference_material}
Genre/Style: {domain_context}

Instructions:
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

Revised Storyline:
"""

