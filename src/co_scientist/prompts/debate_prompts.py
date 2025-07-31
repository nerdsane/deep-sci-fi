# Debate Phase Prompts
# Following the methodology from Google's AI co-scientist paper
# Contains only the LLM vs LLM debate functions that are actively used


def get_llm_debate_meta_analysis_prompt_a(use_case: str, num_directions: int, context_value: str, source_content: str, goal: str = None, criteria: str = None) -> str:
    """Expert A starting prompt for meta-analysis LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Research Goal>\n{goal}\n</Research Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Quality Criteria>\nFocus on directions that excel in: {criteria}\n</Quality Criteria>\n"
    
    return f"""You're discussing research directions for {use_case} with another expert. Propose {num_directions} distinct research directions.{evaluation_framework}

Context: {context_value}
Reference Material: {source_content}

Propose {num_directions} different directions, explaining your reasoning. Focus on diverse approaches for high-quality results."""


def get_llm_debate_meta_analysis_prompt_b(use_case: str, num_directions: int, conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert B response prompt for meta-analysis LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Research Goal>\n{goal}\n</Research Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Quality Criteria>\nFocus on directions that excel in: {criteria}\n</Quality Criteria>\n"
    
    return f"""You're discussing research directions for {use_case} with another expert. Here's the conversation:

{conversation_context}
{evaluation_framework}

<Critical Debate Instructions>
Your role is to be a constructive but critical peer reviewer:

CHALLENGE each direction by asking:
- "This sounds impressive, but what evidence supports feasibility?"
- "Are we solving problems that don't exist in the questions?"
- "Is this direction adding unnecessary complexity?"
- "What would prevent this from working in practice?"

AVOID these unhelpful patterns:
- Adding constraints to make unrealistic ideas seem more plausible
- Building elaborate frameworks on weak foundations  
- "Yes, and..." responses that compound speculation
- Making ideas sound more scientific by adding technical details

BE SPECIFIC in critiques:
- Point to exact questions that a direction fails to address
- Identify assumptions that require major technological breakthroughs
- Call out when directions drift from the original questions
</Critical Debate Instructions>

Respond to Expert A's proposals with critical analysis. You can:
- Challenge unrealistic assumptions with specific concerns
- Point out which questions are inadequately addressed  
- Identify where directions drift from source material
- Propose {num_directions} more grounded alternatives

Focus on advancing toward realistic, well-founded research directions."""


def get_llm_debate_meta_analysis_continue_a(use_case: str, num_directions: int, conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert A continuation prompt for meta-analysis LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Research Goal>\n{goal}\n</Research Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Quality Criteria>\nEvaluate directions based on: {criteria}\n</Quality Criteria>\n"
    
    return f"""Continue the {use_case} research directions discussion:

{conversation_context}
{evaluation_framework}

<Critical Debate Instructions>
Maintain a constructive but critical stance:
- Address Expert B's challenges with specific evidence or acknowledge weaknesses
- Don't add elaborate constraints to save unrealistic ideas
- Question whether your directions truly address the source questions
- Be willing to abandon or significantly revise directions that don't hold up
</Critical Debate Instructions>

Respond to Expert B's points. Refine ideas, acknowledge valid critiques, or offer new perspectives. Work toward consensus on the best {num_directions} directions.

If consensus reached, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]  
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""


def get_llm_debate_meta_analysis_continue_b(use_case: str, num_directions: int, conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert B continuation prompt for meta-analysis LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Research Goal>\n{goal}\n</Research Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Quality Criteria>\nEvaluate directions based on: {criteria}\n</Quality Criteria>\n"
    
    return f"""Continue the {use_case} research directions discussion:

{conversation_context}
{evaluation_framework}

<Critical Debate Instructions>
Continue your critical peer review role:
- Challenge any remaining unrealistic assumptions
- Don't let ideas become more complex without becoming more plausible
- Verify that directions address the actual source questions
- Push for evidence-based feasibility over impressive-sounding concepts
</Critical Debate Instructions>

Respond to Expert A's latest points. Maintain critical analysis, refine ideas based on evidence, or offer new perspectives. Work toward consensus on the best {num_directions} directions.

If consensus reached, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""


def get_llm_debate_tournament_prompt_a(use_case: str, scenario_1_content: str, scenario_2_content: str, goal: str = None, criteria: str = None) -> str:
    """Expert A evaluation prompt for tournament LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Evaluation Goal>\n{goal}\n</Evaluation Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Evaluation Criteria>\nFocus your analysis on: {criteria}\n</Evaluation Criteria>\n"
    
    return f"""You're evaluating two {use_case} options with another expert. Review Option 1 and make a case for why it's better:{evaluation_framework}

OPTION 1:
{scenario_1_content}

OPTION 2: 
{scenario_2_content}

Analyze Option 1's strengths using the evaluation criteria and explain why it's the better choice."""


def get_llm_debate_tournament_prompt_b(use_case: str, scenario_2_content: str, conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert B evaluation prompt for tournament LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Evaluation Goal>\n{goal}\n</Evaluation Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Evaluation Criteria>\nFocus your analysis on: {criteria}\n</Evaluation Criteria>\n"
    
    return f"""You're evaluating two {use_case} options with another expert. Here's what Expert A said about Option 1:

{conversation_context}
{evaluation_framework}
Now review Option 2 and make a case for why it's better:

OPTION 2:
{scenario_2_content}

Analyze Option 2's strengths using the evaluation criteria and explain why it's the better choice than Option 1."""


def get_llm_debate_tournament_final_a(conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert A final assessment prompt for tournament LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Evaluation Goal>\n{goal}\n</Evaluation Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Evaluation Criteria>\nBase your final decision on: {criteria}\n</Evaluation Criteria>\n"
    
    return f"""Based on the discussion, make your final assessment of which option is better:{evaluation_framework}

{conversation_context}

Give your concluding assessment using the evaluation criteria and declare:
BETTER OPTION: 1 or BETTER OPTION: 2"""


def get_llm_debate_tournament_final_b(conversation_context: str, goal: str = None, criteria: str = None) -> str:
    """Expert B final assessment prompt for tournament LLM vs LLM debate."""
    
    # Build evaluation framework
    evaluation_framework = ""
    if goal:
        evaluation_framework += f"\n<Evaluation Goal>\n{goal}\n</Evaluation Goal>\n"
    if criteria:
        evaluation_framework += f"\n<Evaluation Criteria>\nBase your final decision on: {criteria}\n</Evaluation Criteria>\n"
    
    return f"""Based on the full discussion, make your final assessment of which option is better:{evaluation_framework}

{conversation_context}

Give your concluding assessment using the evaluation criteria and declare:
BETTER OPTION: 1 or BETTER OPTION: 2""" 