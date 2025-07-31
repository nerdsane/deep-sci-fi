# Tournament Phase Prompts
# Following the methodology from Google's AI co-scientist paper


def get_pairwise_prompt(use_case: str, baseline_world_state: str = None, years_in_future: int = None, storyline: str = None, chapter_arc: str = None) -> str:
    """Get the appropriate pairwise comparison prompt for the use case."""
    
    templates = {
        "scenario_generation": PAIRWISE_RANKING_PROMPT,
        "storyline_creation": STORYLINE_PAIRWISE_PROMPT,
        "storyline_adjustment": STORYLINE_PAIRWISE_PROMPT,
        "chapter_writing": CHAPTER_PAIRWISE_PROMPT,
        "chapter_rewriting": CHAPTER_PAIRWISE_PROMPT,
        "chapter_arcs_creation": CHAPTER_PAIRWISE_PROMPT,
        "chapter_arcs_adjustment": CHAPTER_PAIRWISE_PROMPT,
        "linguistic_evolution": RESEARCH_PAIRWISE_PROMPT
    }
    
    template = templates.get(use_case, PAIRWISE_RANKING_PROMPT)
    
    # Different templates need different parameters
    if use_case == "scenario_generation":
        # PAIRWISE_RANKING_PROMPT needs baseline_world_state and years_in_future
        if baseline_world_state and years_in_future:
            return template
        else:
            return template
    elif use_case in ["storyline_creation", "storyline_adjustment"]:
        # STORYLINE_PAIRWISE_PROMPT needs storyline
        return template
    elif use_case in ["chapter_writing", "chapter_rewriting", "chapter_arcs_creation", "chapter_arcs_adjustment"]:
        # CHAPTER_PAIRWISE_PROMPT needs storyline and chapter_arc
        return template
    elif use_case == "linguistic_evolution":
        # RESEARCH_PAIRWISE_PROMPT
        return template
    
    return template


# === Pairwise Tournament Prompts ===

# Used in: pairwise_comparison() function for head-to-head scenario tournaments
PAIRWISE_RANKING_PROMPT = """You are an expert comparative analyst evaluating two competing world-building scenarios for scientific rigor and narrative potential.

<Scenario 1>
{scenario1_content}
Research Direction: {direction1}
</Scenario 1>

<Scenario 2>
{scenario2_content}
Research Direction: {direction2}
</Scenario 2>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

Evaluate systematically by answering:

1. **World-Building Coherence**: Which has more coherent world-building and why?
2. **Internal Consistency**: Which maintains better consistency and why?
3. **Scientific Grounding**: Which feels more scientifically grounded and why?
4. **Baseline Evolution**: Which presents more reasonable evolution from baseline over {years_in_future} years and why?

Provide conclusive judgment: **Which scenario presents a more scientifically reasonable and feasible projection from baseline over {years_in_future} years?**

Finally indicate: "better scenario: 1" or "better scenario: 2"

<Reminders>
- Provide thorough comparative analysis before making a decision
- **Focus especially on projection realism and timeline feasibility**
- Evaluate how well each scenario builds logically on the baseline world state
- Consider whether the proposed changes are achievable within {years_in_future} years
- Give clear reasoning for your final judgment
</Reminders>
"""

# Used for storyline creation and narrative development comparisons
STORYLINE_PAIRWISE_PROMPT = """You are an expert in narrative analysis, evaluating two competing storyline approaches for their storytelling potential and creative merit.

<Task>
Determine which storyline approach offers superior narrative foundation for compelling science fiction storytelling.
</Task>

<Storyline 1>
{scenario1_content}
Narrative Approach: {direction1}
</Storyline 1>

<Storyline 2>
{scenario2_content}
Narrative Approach: {direction2}
</Storyline 2>

<Baseline World State>
{baseline_world_state}
</Baseline World State>

<Evaluation Criteria>
- Narrative structure and plot coherence
- Character development potential
- Thematic depth and resonance
- Reader engagement and emotional impact
- Originality and creative uniqueness
- Practical storytelling potential
</Evaluation Criteria>

<Sci-Fi Requirements>
Also evaluate based on sci-fi excellence:
- Strength of central "what if?" speculation (1-10)
- How effectively technology shapes world/characters (1-10)  
- Internal consistency of established rules (1-10)
- Balance between ideas and character development (1-10)
- Character competence vs. knowledge limits (1-10)
- Depth of human condition exploration (1-10)
- Natural integration of social commentary (1-10)
- Story-idea balance (technology serves narrative) (1-10)
</Sci-Fi Requirements>

<Process>
Conduct a structured evaluation by answering these key questions:

1. **Narrative Strength**: Which storyline has stronger narrative architecture? Storyline 1 or Storyline 2?
   - Evaluate plot coherence and story structure
   - Assess character development and arc progression
   - Consider thematic consistency and depth

2. **Reader Engagement**: Which maintains better reader engagement potential?
   - Check for compelling hooks and momentum
   - Evaluate emotional resonance and investment factors
   - Assess pacing and tension development

3. **Creative Merit**: Which demonstrates superior creative achievement?
   - Evaluate originality and genre innovation
   - Assess thematic sophistication and depth
   - Consider unique storytelling approaches

4. **Storytelling Viability**: How effectively does each translate into compelling narrative?
   - Compare practical storytelling potential
   - Evaluate character authenticity and development opportunities
   - Consider plot sustainability and resolution strength
</Process>

<Output Format>
Answer each of the four evaluation questions systematically:

1. Narrative Strength: [Answer which storyline has stronger architecture and why]
2. Reader Engagement: [Answer which maintains better engagement and why]  
3. Creative Merit: [Answer which demonstrates superior creativity and why]
4. Storytelling Viability: [Answer which offers better storytelling potential and why]

Then provide a conclusive judgment: **Which storyline offers superior foundation for compelling science fiction storytelling?**

Finally, indicate the superior storyline by writing: "better scenario: 1" or "better scenario: 2"
</Output Format>

<Reminders>
- Provide thorough comparative analysis before making a decision
- Focus especially on narrative potential and reader engagement
- Evaluate how well each storyline serves the science fiction genre
- Consider both immediate appeal and long-term storytelling sustainability
- Give clear reasoning for your final judgment
</Reminders>
"""

# Used for chapter writing and creative content comparisons
CHAPTER_PAIRWISE_PROMPT = """You are an expert in creative writing and prose analysis, evaluating two competing chapter approaches for their literary merit and storytelling effectiveness.

<Task>
Determine which chapter approach demonstrates superior prose craft and reader engagement for science fiction literature.
</Task>

<Chapter 1>
{scenario1_content}
Writing Approach: {direction1}
</Chapter 1>

<Chapter 2>
{scenario2_content}
Writing Approach: {direction2}
</Chapter 2>

<Storyline Context>
{storyline}
</Storyline Context>

<Chapter Arc Context>
{chapter_arc}
</Chapter Arc Context>

<Evaluation Criteria>
- Prose quality and literary craftsmanship
- World integration and immersion effectiveness
- Character voice and authenticity
- Pacing and narrative flow
- Reader engagement and atmospheric creation
- Dialogue naturalness and effectiveness
</Evaluation Criteria>

<Sci-Fi Requirements>
Also evaluate based on sci-fi excellence:
- Strength of central "what if?" speculation (1-10)
- How effectively technology shapes world/characters (1-10)  
- Internal consistency of established rules (1-10)
- Balance between ideas and character development (1-10)
- Character competence vs. knowledge limits (1-10)
- Depth of human condition exploration (1-10)
- Natural integration of social commentary (1-10)
- Story-idea balance (technology serves narrative) (1-10)
</Sci-Fi Requirements>

<Process>
Conduct a structured evaluation by answering these key questions:

1. **Prose Craftsmanship**: Which chapter demonstrates superior writing quality? Chapter 1 or Chapter 2?
   - Evaluate literary skill and technical proficiency
   - Assess style consistency and voice authenticity
   - Consider language precision and effectiveness

2. **World Integration**: Which achieves better world-building integration?
   - Check for seamless setting immersion
   - Evaluate character authenticity within world context
   - Assess technology/culture integration naturalness

3. **Reader Experience**: Which creates more engaging reader experience?
   - Evaluate pacing effectiveness and narrative flow
   - Assess atmospheric creation and sensory richness
   - Consider dialogue quality and character voice distinction

4. **Literary Merit**: How effectively does each achieve literary excellence?
   - Compare overall prose achievement and craft mastery
   - Evaluate unique voice development and style innovation
   - Consider long-term reader impact and memorability
</Process>

<Output Format>
Answer each of the four evaluation questions systematically:

1. Prose Craftsmanship: [Answer which chapter has superior writing quality and why]
2. World Integration: [Answer which achieves better integration and why]  
3. Reader Experience: [Answer which creates more engaging experience and why]
4. Literary Merit: [Answer which demonstrates superior literary achievement and why]

Then provide a conclusive judgment: **Which chapter approach demonstrates superior prose craft and storytelling effectiveness?**

Finally, indicate the superior chapter by writing: "better scenario: 1" or "better scenario: 2"
</Output Format>

<Reminders>
- Provide thorough comparative analysis before making a decision
- Focus especially on prose quality and reader engagement
- Evaluate how well each chapter serves both literary and genre expectations
- Consider both immediate impact and long-term literary value
- Give clear reasoning for your final judgment
</Reminders>
"""

# Used for linguistic evolution and research comparisons
RESEARCH_PAIRWISE_PROMPT = """You are an expert linguist and academic reviewer evaluating two competing linguistic evolution approaches for their scholarly rigor and evolutionary plausibility.

<Task>
Determine which linguistic analysis demonstrates superior academic rigor and evolutionary insights for understanding language development in technological contexts.
</Task>

<Analysis 1>
{scenario1_content}
Research Approach: {direction1}
</Analysis 1>

<Analysis 2>
{scenario2_content}
Research Approach: {direction2}
</Analysis 2>

<World Context>
{baseline_world_state}
</World Context>

<Evaluation Criteria>
- Academic rigor and methodological soundness
- Linguistic theory grounding and evidence quality
- Evolutionary plausibility and timeline realism
- Interdisciplinary integration effectiveness
- Innovation factor and scholarly contribution
- Practical application and real-world relevance
</Evaluation Criteria>

<Sci-Fi Requirements>
Also evaluate based on sci-fi excellence:
- Strength of central "what if?" speculation (1-10)
- How effectively technology shapes world/characters (1-10)  
- Internal consistency of established rules (1-10)
- Balance between ideas and character development (1-10)
- Character competence vs. knowledge limits (1-10)
- Depth of human condition exploration (1-10)
- Natural integration of social commentary (1-10)
- Story-idea balance (technology serves narrative) (1-10)
</Sci-Fi Requirements>

<Process>
Conduct a structured evaluation by answering these key questions:

1. **Academic Rigor**: Which analysis demonstrates superior scholarly methodology? Analysis 1 or Analysis 2?
   - Evaluate theoretical foundation and evidence quality
   - Assess methodological sophistication and logical reasoning
   - Consider citation quality and academic writing standards

2. **Evolutionary Plausibility**: Which presents more convincing language evolution?
   - Check for realistic linguistic change patterns
   - Evaluate timeline feasibility and developmental pathways
   - Assess consistency with established linguistic principles

3. **Interdisciplinary Integration**: Which achieves better cross-field synthesis?
   - Evaluate technology-language interaction analysis
   - Assess cultural and social factor integration
   - Consider holistic understanding demonstration

4. **Scholarly Contribution**: How effectively does each advance linguistic understanding?
   - Compare innovation factor and novel insights
   - Evaluate practical application and real-world relevance
   - Consider potential impact on the field
</Process>

<Output Format>
Answer each of the four evaluation questions systematically:

1. Academic Rigor: [Answer which analysis has superior methodology and why]
2. Evolutionary Plausibility: [Answer which presents more convincing evolution and why]  
3. Interdisciplinary Integration: [Answer which achieves better synthesis and why]
4. Scholarly Contribution: [Answer which offers superior contribution and why]

Then provide a conclusive judgment: **Which linguistic analysis demonstrates superior academic rigor and evolutionary insights?**

Finally, indicate the superior analysis by writing: "better scenario: 1" or "better scenario: 2"
</Output Format>

<Reminders>
- Provide thorough comparative analysis before making a decision
- Focus especially on academic rigor and evolutionary plausibility
- Evaluate how well each analysis integrates linguistic theory with technological context
- Consider both methodological soundness and innovative insights
- Give clear reasoning for your final judgment
</Reminders>
""" 