# Deep Sci-Fi

A sci-fi writing assistant inspired by [DeepMind's AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) tournament-based hypothesis evaluation system.

## 🚀 Quickstart

1. Clone the repository and activate a virtual environment:
```bash
git clone https://github.com/nerdsane/deep-sci-fi.git
cd deep-sci-fi
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
uv pip install -e .
```

3. Set up your `.env` file with API keys:
```bash
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
# TAVILY_API_KEY=your_key_here
# LANGCHAIN_TRACING_V2=true
# LANGSMITH_API_KEY=your_key_here
# LANGSMITH_PROJECT="deep-sci-fi"
```

4. Launch the system with LangGraph server:

```bash
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

Use this to open the Studio UI:
```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

## 📖 Deep Sci-Fi Writer

The core writing assistant that creates scientifically-grounded science fiction narratives through a structured multi-stage process.

### Features

- **Competitive Storyline Creation**: Uses Co-Scientist for generating multiple storyline options through competitive evolution
- **Research-Driven World Building**: Integrates Open Deep Research for scientifically accurate background research
- **Multi-Stage Development**: Structured workflow from initial concept to complete narrative
- **Scientific Accuracy**: Ensures plausibility through expert domain analysis
- **Unique Voice**: Avoids clichés and generic tropes for authentic storytelling

### How It Works

1. **Storyline Competition**: Co-Scientist generates and evolves multiple storyline concepts
2. **Research Integration**: Open Deep Research provides scientific backing for concepts
3. **World Building**: Develops comprehensive world state and linguistic evolution
4. **Chapter Development**: Creates detailed chapter arcs with scientific explanations
5. **Narrative Synthesis**: Combines all elements into coherent, engaging story

### Usage

Access the Deep Sci-Fi Writer through LangGraph Studio:
1. Select "Deep Sci-Fi" from the available graphs
2. Enter your story concept in the messages field
3. Follow the interactive prompts to guide story development
4. Review generated content at each stage with human-in-the-loop approval

### Configuration

Key model settings (in `src/deep_sci_fi/deep_sci_fi_writer.py`):
- **Research Model**: `openai:gpt-4.1-nano` - Powers research integration
- **Writing Model**: `openai:gpt-4.1-nano` - Handles narrative generation  
- **General Model**: `openai:gpt-4.1-nano` - Manages workflow coordination

## 🧬 Co-Scientist

A competitive multi-agent system that generates and evolves ideas through tournament-style analysis and refinement.

### Features

- **Tournament Evolution**: Multiple agents compete to refine and improve concepts
- **Domain Expertise**: Specialized critique from different scientific and creative domains
- **Meta-Analysis**: Identifies research directions and analytical approaches
- **Parallel Processing**: Concurrent analysis streams for comprehensive coverage
- **Iterative Refinement**: Multiple rounds of critique and improvement

### Use Cases

- **Storyline Creation**: Generate competing narrative concepts for sci-fi stories
- **Research Direction**: Identify optimal approaches for investigation
- **Concept Development**: Evolve initial ideas through competitive analysis
- **Quality Assurance**: Multi-perspective critique for robust outcomes

### How It Works

1. **Meta-Analysis**: Identifies multiple research or creative approaches
2. **Scenario Generation**: Creates detailed implementations of each approach
3. **Domain Critique**: Specialists analyze from their expertise areas
4. **Tournament Comparison**: Head-to-head evaluation of alternatives  
5. **Evolution**: Winning concepts are refined and evolved further

### Configuration Options

- **Process Depth**: `quick`, `standard`, `