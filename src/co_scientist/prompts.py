# Co-Scientist Competition Prompts
# Following the methodology from Google's AI co-scientist paper

###################
# Meta-Analysis Phase
###################

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
# Reflection Phase
###################

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

CROSS_SCENARIO_REFLECTION_PROMPT = """You are conducting comparative analysis between two research approaches to identify strengths and weaknesses.

Scenario A: {scenario_a_content}
Research Direction A: {direction_a}

Scenario B: {scenario_b_content}  
Research Direction B: {direction_b}

Instructions:
1. Compare these two approaches to the same world-building challenges
2. Identify which scenario handles specific aspects more convincingly
3. Look for complementary insights that could improve both scenarios
4. Assess which assumptions are better supported by current research

Comparative Analysis:
- Which scenario better addresses technological feasibility?
- Which has more realistic timelines and implementation paths?
- Which considers broader systemic implications more thoroughly?
- What strengths from each could be combined?

Generate insights that could improve both scenarios through cross-pollination of ideas.

Analysis:
"""

###################
# Tournament Phase
###################

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

TOURNAMENT_SCORING_PROMPT = """You are evaluating a world-building scenario on multiple scientific and narrative criteria.

Scenario: {scenario_content}
Research Direction: {research_direction}

Rate this scenario on a scale of 1-10 for each criterion:

1. Scientific Plausibility (1-10): Are the technological claims grounded in current research and plausible extrapolation?

2. Internal Consistency (1-10): Do all elements of the world work together logically without contradictions?

3. Timeline Realism (1-10): Are the proposed development timelines realistic given current technological progress?

4. Systemic Thinking (1-10): Does the scenario consider second-order effects and complex interactions between systems?

5. Detail Richness (1-10): Is there sufficient specific detail for world-building and story development?

6. Narrative Potential (1-10): Does this world create interesting opportunities for storytelling and character development?

7. Originality (1-10): How creative and fresh is this take on future world development?

8. Implementation Feasibility (1-10): How realistic are the proposed solutions from an engineering/economic perspective?

For each score, provide brief justification.

Then calculate total score out of 80.

Scoring Analysis:
"""

###################
# Evolution Phase
###################

FEASIBILITY_EVOLUTION_PROMPT = """You are an expert in scientific research and technological feasibility analysis.

Your task is to enhance the provided scenario's practical implementability while retaining its novelty and narrative appeal.

Original Scenario: {scenario_content}
Research Direction: {research_direction}
Identified Issues: {critique_summary}

Guidelines:
1. Begin with an overview of the relevant scientific domains
2. Provide recent research findings that support or challenge elements of the scenario
3. Articulate how current technological trends could realistically enable the proposed future
4. CORE CONTRIBUTION: Develop detailed, innovative, and technologically viable improvements

Improvement Focus:
- Address specific scientific critiques raised during reflection
- Strengthen evidence grounding with current research
- Improve timeline realism and implementation pathways
- Enhance internal consistency across technological systems
- Maintain the scenario's unique creative vision

Research-Based Improvements:
- Cite recent scientific papers or technological developments
- Explain how current trends support the scenario's assumptions
- Address potential obstacles with realistic solutions
- Provide more specific implementation details

Enhanced Scenario:
"""

CREATIVE_EVOLUTION_PROMPT = """You are an expert researcher tasked with generating novel enhancements inspired by cross-scenario insights.

Original Scenario: {scenario_content}
Research Direction: {research_direction}

Inspiration Sources (utilize analogy and inspiration, not direct replication):
{competing_scenarios}

Instructions:
1. Provide a brief overview of creative possibilities in the scenario's domain
2. Identify innovative approaches from the inspiration sources
3. Find novel ways to integrate complementary insights
4. CORE CONTRIBUTION: Develop original, creative enhancements that think outside conventional approaches

Enhancement Goals:
- Combine the best creative insights from multiple approaches
- Introduce novel elements that weren't in any single scenario
- Think beyond conventional extrapolation to find breakthrough possibilities
- Maintain scientific grounding while pushing creative boundaries

This should not be mere aggregation of existing elements, but genuine creative synthesis that produces new possibilities.

Enhanced Creative Scenario:
"""

SYNTHESIS_EVOLUTION_PROMPT = """You are synthesizing insights from multiple competing scenarios to create an improved version.

Primary Scenario: {primary_scenario}
Research Direction: {research_direction}

Competing Insights to Integrate:
{competing_scenarios}

Critical Feedback Addressed:
{critique_summary}

Instructions:
1. Analyze the strengths of each competing approach
2. Identify complementary elements that could enhance the primary scenario
3. Resolve any contradictions through higher-level synthesis
4. Create a unified scenario that combines the best elements

Synthesis Principles:
- Maintain the core identity of the primary scenario
- Integrate valuable insights from competitors where compatible
- Address identified weaknesses through strategic improvements
- Ensure enhanced internal consistency and scientific rigor

The result should be stronger than any individual scenario while maintaining coherent vision.

Synthesized Scenario:
"""

###################
# Final Selection
###################

META_REVIEW_PROMPT = """You are conducting a meta-analysis of the co-scientist competition results to select the top scenarios for user presentation.

Competition Results:
{competition_summary}

Final Scenarios from Each Direction:
Direction 1: {direction1_winner}
Direction 2: {direction2_winner} 
Direction 3: {direction3_winner}

Additional Evolved Variants:
{evolved_scenarios}

Instructions:
1. Analyze the competition process and identify the highest quality outcomes
2. Ensure the final selection provides meaningful variety for user choice
3. Select the 3 best scenarios that combine scientific rigor with narrative potential
4. Provide clear reasoning for each selection

Selection Criteria:
- Scientific grounding and evidence quality
- Internal consistency and logical coherence
- Narrative potential for storytelling
- Meaningful differentiation between options
- Overall quality as demonstrated through competition

For each selected scenario, provide:
- Summary of core approach and assumptions
- Key strengths demonstrated through competition
- Quality score and competitive ranking
- Why this represents a good choice for the user

Final Selection Analysis:
"""

COMPETITION_SUMMARY_PROMPT = """Generate a comprehensive summary of the co-scientist competition process and outcomes.

Competition Data:
Research Directions: {research_directions}
Total Scenarios Generated: {total_scenarios}
Reflection Critiques: {critique_count}
Tournament Rounds: {tournament_rounds}
Evolution Improvements: {evolution_count}

Process Overview:
1. Meta-analysis identified research directions
2. Parallel scenario generation and competition
3. Domain expert reflection and critique
4. Tournament ranking and selection
5. Evolution and improvement phases

Summarize:
- How the competition improved scenario quality
- Key insights from the reflection and critique phases
- Competitive advantages of winning scenarios
- Evidence of scientific rigor throughout the process
- Overall confidence in the final recommendations

Competition Summary:
""" 