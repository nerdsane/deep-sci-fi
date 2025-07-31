# Reflection Phase Prompts
# Following the methodology from Google's AI co-scientist paper


def get_unified_reflection_prompt(use_case: str) -> str:
    """Get the appropriate unified reflection prompt based on use case."""
    
    prompt_mapping = {
        "scenario_generation": UNIFIED_SCIENTIFIC_REFLECTION_PROMPT,
        "storyline_creation": UNIFIED_NARRATIVE_REFLECTION_PROMPT,
        "chapter_writing": UNIFIED_PROSE_REFLECTION_PROMPT,
        "chapter_rewriting": UNIFIED_PROSE_REFLECTION_PROMPT,
        "chapter_arcs_creation": UNIFIED_NARRATIVE_REFLECTION_PROMPT,
        "chapter_arcs_adjustment": UNIFIED_NARRATIVE_REFLECTION_PROMPT,
        "linguistic_evolution": UNIFIED_RESEARCH_REFLECTION_PROMPT,
        "storyline_adjustment": UNIFIED_NARRATIVE_REFLECTION_PROMPT
    }
    
    return prompt_mapping.get(use_case, UNIFIED_SCIENTIFIC_REFLECTION_PROMPT)


# === Unified Reflection Prompts ===

# Used for: scenario generation use case
UNIFIED_SCIENTIFIC_REFLECTION_PROMPT = """You are a multidisciplinary scientific review panel evaluating a world-building scenario.

<Scenario ID>
{scenario_id}
</Scenario ID>

<Research Direction>
{research_direction}
</Research Direction>

<Scenario to Evaluate>
{scenario_content}
</Scenario to Evaluate>

<Expert Panel>
You represent a collaborative team of experts in: Science & Technology, Systems Engineering, Social Sciences
</Expert Panel>

<Comprehensive Evaluation>
Assess this scenario across all scientific dimensions:

**Scientific Foundation:**
- Technological feasibility, research grounding
- Current evidence support, plausibility assessment
- Timeline realism, implementation pathways

**Systems Integration:**
- Internal consistency, component interaction
- Scalability analysis, complexity management
- Resource requirements, infrastructure needs

**Social & Economic Impact:**
- Societal adaptation patterns
- Economic viability, market dynamics
- Cultural integration, behavioral change
</Comprehensive Evaluation>

<Quality Assessment>
Rate the scenario on each dimension (1-100 scale):

1. **Scientific Plausibility** (1-100): Evidence grounding and technological feasibility
2. **Internal Consistency** (1-100): Logical coherence across all systems
3. **Implementation Feasibility** (1-100): Realistic pathways and timelines
4. **Innovation Factor** (1-100): Novelty within realistic constraints
5. **Systems Integration** (1-100): Component interaction and scalability
6. **Social Viability** (1-100): Cultural and economic adaptation potential
7. **Detail Richness** (1-100): Specificity and depth of world-building
8. **Narrative Potential** (1-100): Storytelling and engagement possibilities

**Overall Quality Score** (1-100): Weighted average emphasizing scientific rigor
</Quality Assessment>

<Output Format>
## Scientific Assessment

**Strengths:**
- [Key areas where scenario excels scientifically]

**Areas for Improvement:**
- [Specific scientific issues with explanations and suggestions]

**Feasibility Analysis:**
- [Assessment of implementation pathways and timelines]

## Quality Scores
- Scientific Plausibility: X/100
- Internal Consistency: X/100
- Implementation Feasibility: X/100
- Innovation Factor: X/100
- Systems Integration: X/100
- Social Viability: X/100
- Detail Richness: X/100
- Narrative Potential: X/100

**Overall Quality Score: X/100**

## Key Recommendations
1. [Top priority scientific improvement]
2. [Second priority improvement]
3. [Third priority improvement]

## Tournament Readiness  
**Advancement Recommendation:** [ADVANCE/REVISE/REJECT with brief justification]
</Output Format>
"""

# Used for: storyline creation and narrative use cases
UNIFIED_NARRATIVE_REFLECTION_PROMPT = """You are a comprehensive narrative development panel evaluating a storyline.

<Scenario ID>
{scenario_id}
</Scenario ID>

<Research Direction>
{research_direction}
</Research Direction>

<Storyline to Evaluate>
{scenario_content}
</Storyline to Evaluate>

<Expert Panel>
You represent a collaborative team of experts in: Narrative Structure, Character Development, Reader Engagement
</Expert Panel>

<Comprehensive Evaluation>
Assess this storyline across all narrative dimensions:

**Narrative Architecture:**
- Story structure completeness, plot coherence
- Pacing strategy, tension development
- Thematic consistency, resolution strength

**Character Development:**
- Protagonist strength, supporting character depth
- Character arc progression, motivation clarity
- Relationship dynamics, authentic behavior

**Reader Engagement:**
- Hook effectiveness, momentum maintenance
- Emotional resonance, investment potential
- Originality factor, genre innovation
</Comprehensive Evaluation>

<Quality Assessment>
Rate the storyline on each dimension (1-100 scale):

1. **Narrative Structure** (1-100): Plot coherence and story architecture
2. **Character Development** (1-100): Protagonist and supporting character strength
3. **Thematic Depth** (1-100): Meaningful themes and resonant messaging
4. **Pacing Mastery** (1-100): Tension, momentum, and reader engagement
5. **Originality Factor** (1-100): Creative uniqueness and genre innovation
6. **Emotional Impact** (1-100): Reader connection and emotional resonance
7. **Dialogue Quality** (1-100): Natural conversation and character voice
8. **Resolution Strength** (1-100): Satisfying conclusion and conflict resolution

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

**Overall Quality Score** (1-100): Weighted average emphasizing narrative craft
</Quality Assessment>

<Output Format>
## Narrative Assessment

**Strengths:**
- [Key areas where storyline excels narratively]

**Areas for Improvement:**
- [Specific narrative issues with explanations and suggestions]

**Character Analysis:**
- [Assessment of character development and authenticity]

## Quality Scores
- Narrative Structure: X/100
- Character Development: X/100
- Thematic Depth: X/100
- Pacing Mastery: X/100
- Originality Factor: X/100
- Emotional Impact: X/100
- Dialogue Quality: X/100
- Resolution Strength: X/100

**Overall Quality Score: X/100**

## Key Recommendations
1. [Top priority narrative improvement]
2. [Second priority improvement]
3. [Third priority improvement]

## Tournament Readiness  
**Advancement Recommendation:** [ADVANCE/REVISE/REJECT with brief justification]
</Output Format>
"""

# Used for: chapter writing and prose use cases
UNIFIED_PROSE_REFLECTION_PROMPT = """You are a comprehensive prose evaluation panel reviewing a chapter.

<Scenario ID>
{scenario_id}
</Scenario ID>

<Research Direction>
{research_direction}
</Research Direction>

<Chapter to Evaluate>
{scenario_content}
</Chapter to Evaluate>

<Expert Panel>
You represent a collaborative team of experts in: Literary Craft, World Integration, Reader Experience
</Expert Panel>

<Comprehensive Evaluation>
Assess this chapter across all prose dimensions:

**Literary Craftsmanship:**
- Prose quality, style consistency
- Voice authenticity, linguistic precision
- Technical proficiency, grammar mastery

**World Integration:**
- Setting immersion, world-building seamlessness
- Character authenticity within world context
- Technology/culture integration naturalness

**Reader Experience:**
- Engagement level, pacing effectiveness
- Sensory richness, atmospheric creation
- Dialogue naturalness, character voice distinction
</Comprehensive Evaluation>

<Quality Assessment>
Rate the chapter on each dimension (1-100 scale):

1. **Prose Craftsmanship** (1-100): Writing quality and technical skill
2. **Scene Immersion** (1-100): Setting and atmosphere creation
3. **Character Voice** (1-100): Authentic dialogue and personality
4. **Pacing Mastery** (1-100): Narrative flow and momentum
5. **Atmospheric Creation** (1-100): Mood and tone establishment
6. **Dialogue Excellence** (1-100): Natural conversation and character distinction
7. **Sensory Richness** (1-100): Vivid and engaging descriptions
8. **Technical Proficiency** (1-100): Grammar, syntax, and style consistency

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

**Overall Quality Score** (1-100): Weighted average emphasizing prose craft
</Quality Assessment>

<Output Format>
## Prose Assessment

**Strengths:**
- [Key areas where chapter excels in prose quality]

**Areas for Improvement:**
- [Specific prose issues with explanations and suggestions]

**Voice Analysis:**
- [Assessment of character voice and style consistency]

## Quality Scores
- Prose Craftsmanship: X/100
- Scene Immersion: X/100
- Character Voice: X/100
- Pacing Mastery: X/100
- Atmospheric Creation: X/100
- Dialogue Excellence: X/100
- Sensory Richness: X/100
- Technical Proficiency: X/100

**Overall Quality Score: X/100**

## Key Recommendations
1. [Top priority prose improvement]
2. [Second priority improvement]
3. [Third priority improvement]

## Tournament Readiness  
**Advancement Recommendation:** [ADVANCE/REVISE/REJECT with brief justification]
</Output Format>
"""

# Used for: linguistic_evolution use case
UNIFIED_RESEARCH_REFLECTION_PROMPT = """You are a comprehensive research evaluation panel reviewing a linguistic evolution analysis.

<Scenario ID>
{scenario_id}
</Scenario ID>

<Research Direction>
{research_direction}
</Research Direction>

<Research Analysis to Evaluate>
{scenario_content}
</Research Analysis to Evaluate>

<Expert Panel>
You represent a collaborative team of experts in: Linguistics, Technology Integration, Sociology & Anthropology
</Expert Panel>

<Comprehensive Evaluation>
Assess this research analysis across all academic dimensions:

**Linguistic Scholarship:**
- Theoretical foundation, methodology rigor
- Citation quality, evidence integration
- Academic writing standards

**Technology Integration:**
- Understanding of technological systems
- Tech-language interaction analysis
- Future technology assessment accuracy

**Sociological & Anthropological Insight:**
- Cultural pattern recognition
- Social change analysis depth
- Human behavior prediction realism

**Research Methodology:**
- Approach sophistication, data interpretation
- Logical reasoning, conclusion validity
- Academic contribution potential

**Interdisciplinary Integration:**
- Cross-field synthesis quality
- Holistic understanding demonstration
- Field boundary navigation
</Comprehensive Evaluation>

<Quality Assessment>
Rate the research analysis on each dimension (1-100 scale):

1. **Academic Rigor** (1-100): Scholarly methodology and standards
2. **Theoretical Foundation** (1-100): Conceptual framework strength
3. **Evidence Quality** (1-100): Supporting data and citations
4. **Analytical Depth** (1-100): Insight sophistication and originality
5. **Interdisciplinary Integration** (1-100): Cross-field synthesis effectiveness
6. **Practical Application** (1-100): Real-world relevance and applicability
7. **Innovation Factor** (1-100): Novel insights and perspectives
8. **Communication Clarity** (1-100): Presentation and accessibility

**Overall Quality Score** (1-100): Weighted average emphasizing academic excellence
</Quality Assessment>

<Output Format>
## Research Assessment

**Strengths:**
- [Key areas where analysis excels academically]

**Areas for Improvement:**
- [Specific research issues with explanations and suggestions]

**Methodology Analysis:**
- [Assessment of research approach and evidence quality]

## Quality Scores
- Academic Rigor: X/100
- Theoretical Foundation: X/100
- Evidence Quality: X/100
- Analytical Depth: X/100
- Interdisciplinary Integration: X/100
- Practical Application: X/100
- Innovation Factor: X/100
- Communication Clarity: X/100

**Overall Quality Score: X/100**

## Key Recommendations
1. [Top priority research improvement]
2. [Second priority improvement]
3. [Third priority improvement]

## Tournament Readiness
**Advancement Recommendation:** [ADVANCE/REVISE/REJECT with brief justification]
</Output Format>
""" 