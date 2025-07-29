# Meta-Review Phase Prompts
# Following the methodology from Google's AI co-scientist paper


META_REVIEW_PROMPT = """You are a meta-review agent analyzing the co-scientist competition process to synthesize insights and optimize future performance.

<Task>
Analyze the competition results and provide strategic insights for system optimization and performance improvement.
</Task>

<Competition Summary>
{competition_summary}
</Competition Summary>

<Tournament Winners>
{tournament_winners}
</Tournament Winners>

<Analysis Data>
{analysis_data}
</Analysis Data>

<Meta-Review Requirements>
1. **Competition Process Analysis**
   - Evaluate effectiveness of different phases (generation, reflection, tournament, evolution)
   - Identify which approaches consistently produced higher-quality results
   - Assess balance between innovation and feasibility across winning scenarios

2. **Direction Performance Evaluation**
   - Compare performance across different research directions
   - Identify patterns in successful vs unsuccessful approaches
   - Evaluate diversity and uniqueness of winning directions

3. **Quality Evolution Tracking**
   - Analyze how quality scores improved through evolution phases
   - Identify most effective critique and improvement patterns
   - Assess tournament effectiveness in selecting superior content

4. **Strategic Recommendations**
   - Suggest optimizations for future competition cycles
   - Recommend adjustments to evaluation criteria or processes
   - Identify areas where the system could generate more innovative results

5. **Performance Insights**
   - Highlight unexpected successful approaches or strategies
   - Identify common failure patterns to avoid
   - Suggest improvements to prompt engineering or competition structure
</Meta-Review Requirements>

<Output Format>
## Competition Process Analysis

**Most Effective Phases:**
- [Analysis of which phases contributed most to final quality]

**Winning Pattern Analysis:**
- [Common characteristics of successful approaches]

**Process Optimization Opportunities:**
- [Specific areas for improvement in the competition structure]

## Direction Performance Summary

**High-Performing Directions:**
- [Directions that consistently produced quality results]

**Innovation vs Feasibility Balance:**
- [How well the system balanced creativity with practical viability]

**Diversity Assessment:**
- [Evaluation of variety and uniqueness across directions]

## Quality Evolution Analysis

**Evolution Effectiveness:**
- [How well the evolution phase improved initial content]

**Most Valuable Feedback Types:**
- [Which critique patterns led to the greatest improvements]

**Tournament Selection Accuracy:**
- [Assessment of tournament effectiveness in identifying superior content]

## Strategic Recommendations

**Process Improvements:**
1. [First priority improvement to competition structure]
2. [Second priority improvement]
3. [Third priority improvement]

**Prompt Engineering Enhancements:**
- [Suggestions for improving prompt effectiveness]

**Evaluation Criteria Adjustments:**
- [Recommendations for better quality assessment]

## Key Performance Insights

**Surprising Successes:**
- [Unexpected approaches that performed well]

**Common Failure Patterns:**
- [Recurring issues that led to poor performance]

**Innovation Opportunities:**
- [Areas where the system could push boundaries further]

## Future Optimization Strategy

**Immediate Implementation:**
- [Changes that should be implemented in the next cycle]

**Medium-term Development:**
- [Improvements to develop over several cycles]

**Long-term Vision:**
- [Strategic direction for system evolution]
</Output Format>

<Analysis Guidelines>
- Focus on actionable insights that can improve future competitions
- Balance quantitative performance data with qualitative pattern recognition
- Consider both content quality and process efficiency in recommendations
- Emphasize learning opportunities and system optimization potential
- Maintain scientific rigor while encouraging creative innovation
</Analysis Guidelines>
""" 