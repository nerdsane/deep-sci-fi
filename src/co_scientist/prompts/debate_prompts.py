# Debate Phase Prompts
# Following the methodology from Google's AI co-scientist paper
# Contains only the LLM vs LLM debate functions that are actively used


def get_llm_debate_meta_analysis_prompt_a(use_case: str, num_directions: int, context_value: str, source_content: str) -> str:
    """Expert A starting prompt for meta-analysis LLM vs LLM debate."""
    return f"""You're discussing research directions for {use_case} with another expert. Propose {num_directions} distinct research directions.

Context: {context_value}
Reference Material: {source_content}

Propose {num_directions} different directions, explaining your reasoning. Focus on diverse approaches for high-quality results."""


def get_llm_debate_meta_analysis_prompt_b(use_case: str, num_directions: int, conversation_context: str) -> str:
    """Expert B response prompt for meta-analysis LLM vs LLM debate."""
    return f"""You're discussing research directions for {use_case} with another expert. Here's the conversation:

{conversation_context}

Respond to Expert A's proposals. You can:
- Build on their ideas with enhancements
- Offer alternative perspectives  
- Identify improvements or gaps
- Propose {num_directions} refined alternatives

Focus on advancing toward the best research directions."""


def get_llm_debate_meta_analysis_continue_a(use_case: str, num_directions: int, conversation_context: str) -> str:
    """Expert A continuation prompt for meta-analysis LLM vs LLM debate."""
    return f"""Continue the {use_case} research directions discussion:

{conversation_context}

Respond to Expert B's points. Refine ideas, build on theirs, or offer new perspectives. Work toward consensus on the best {num_directions} directions.

If consensus reached, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]  
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""


def get_llm_debate_meta_analysis_continue_b(use_case: str, num_directions: int, conversation_context: str) -> str:
    """Expert B continuation prompt for meta-analysis LLM vs LLM debate."""
    return f"""Continue the {use_case} research directions discussion:

{conversation_context}

Respond to Expert A's latest points. Refine ideas, build on them, or offer new perspectives. Work toward consensus on the best {num_directions} directions.

If consensus reached, conclude with:
FINAL CONSENSUS:
Direction 1: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

Direction 2: [Name]
Core Assumption: [Key assumption]
Focus: [What this emphasizes]

[Continue for {num_directions} directions]"""


def get_llm_debate_tournament_prompt_a(use_case: str, scenario_1_content: str, scenario_2_content: str) -> str:
    """Expert A evaluation prompt for tournament LLM vs LLM debate."""
    return f"""You're evaluating two {use_case} options with another expert. Review Option 1 and make a case for why it's better:

OPTION 1:
{scenario_1_content}

OPTION 2: 
{scenario_2_content}

Analyze Option 1's strengths and explain why it's the better choice."""


def get_llm_debate_tournament_prompt_b(use_case: str, scenario_2_content: str, conversation_context: str) -> str:
    """Expert B evaluation prompt for tournament LLM vs LLM debate."""
    return f"""You're evaluating two {use_case} options with another expert. Here's what Expert A said about Option 1:

{conversation_context}

Now review Option 2 and make a case for why it's better:

OPTION 2:
{scenario_2_content}

Analyze Option 2's strengths and explain why it's the better choice than Option 1."""


def get_llm_debate_tournament_final_a(conversation_context: str) -> str:
    """Expert A final assessment prompt for tournament LLM vs LLM debate."""
    return f"""Based on the discussion, make your final assessment of which option is better:

{conversation_context}

Give your concluding assessment and declare:
BETTER OPTION: 1 or BETTER OPTION: 2"""


def get_llm_debate_tournament_final_b(conversation_context: str) -> str:
    """Expert B final assessment prompt for tournament LLM vs LLM debate."""
    return f"""Based on the full discussion, make your final assessment of which option is better:

{conversation_context}

Give your concluding assessment and declare:
BETTER OPTION: 1 or BETTER OPTION: 2""" 