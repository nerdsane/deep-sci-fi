# Deep Sci-Fi

A sci-fi writing workflow inspired by [DeepMind's AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/). 

This system uses **competitive tournaments** and **AI debates** to create science fiction grounded in research:

- **Tournament competition** generates multiple world-building scenarios
- **Research-backed predictions** create scientifically plausible futures through incremental steps
- **Debate phases** refine ideas through argumentation between different AI models
- **Evolutionary refinement** improves storylines, chapters, and prose through iterative competition

The result: rigorous research meets creative storytelling for scientifically-grounded sci-fi.

## 🏗️ Architecture

The system uses a CS (Co-Scientist) agent-based architecture for iterative, scientifically grounded chapter writing:

**Main Workflow:** Parse → Context → Loglines → [USER SELECTION] → CS Agent System

**CS Agent System:** Meta-Analysis → Generation → Reflection → Evolution → Meta-Review
- Iterative improvement loop with just-in-time research
- Each agent specializes in specific aspects of chapter writing
- Quality-driven process with visible failure modes

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
# Edit .env with your API keys
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

Creates scientifically-grounded science fiction through competitive AI tournaments and research integration.

### Process

1. **Competitive Loglines**: Multiple AI approaches compete to create authentic future story loglines
2. **📋 User Selection**: Choose your preferred numbered logline option in LangGraph Studio (see `LOGLINE_SELECTION_GUIDE.md`)
3. **Research Integration**: Automated fact-gathering for scientific accuracy
4. **World Building**: Develops plausible future scenarios and technologies
5. **Chapter Development**: Creates structured narrative with scientific explanations

### Usage

1. **Launch** via LangGraph Studio and select "Deep Sci-Fi" graph
2. **Enter** your story concept and parameters
3. **Wait** for logline generation (workflow pauses automatically)
4. **Select** your preferred logline by number in the `user_story_selection` field
5. **Resume** workflow - the system handles the rest automatically

📖 **Detailed Selection Guide**: See `LOGLINE_SELECTION_GUIDE.md` for step-by-step instructions.

### Configuration

Model templates (in `src/co_scientist/configuration.py`):
- **Creative Template**: Optimized for narrative tasks (Claude Opus + O3)
- **Reasoning Template**: Optimized for research tasks (O3 + GPT-4o)

## 🧬 Co-Scientist

Competitive tournament workflow that generates and evolves ideas through AI debates and quality ranking.

### Core Features

- **Tournament Competition**: AI models compete to generate the best concepts
- **Debate Phases**: Different models argue for competing approaches
- **Quality Ranking**: Elo rating system tracks performance across competitions
- **Evolutionary Refinement**: Winning ideas are improved through iterative competition

### Workflow Phases

1. **Meta-Analysis**: Generate multiple research/creative directions
2. **Generation**: Create detailed content for each direction  
3. **Reflection**: Quality assessment and critique
4. **Tournament**: Head-to-head comparisons with debates
5. **Evolution**: Refine and improve winning concepts

### Configuration

Templates automatically assign models per use case:
- **Creative Template**: For storylines, chapters (Claude Opus + Sonnet + O3)
- **Reasoning Template**: For research, analysis (O3 + GPT-4o + Sonnet)

Per-phase model override supported for advanced users.

## 📁 Project Structure

```
deep-sci-fi/
├── src/                          # Main source code
│   ├── co_scientist/            # Competitive tournament system
│   │   ├── phases/              # Tournament phases (debate, evolution, etc.)
│   │   ├── prompts/             # Phase-specific prompts
│   │   ├── utils/               # Model factory, LLM manager, output tools
│   │   └── configuration.py     # Model templates and settings
│   ├── deep_sci_fi/             # Main writing workflow
│   │   ├── deep_sci_fi_writer.py # Core orchestration logic
│   │   └── prompts.py           # Writing-specific prompts
│   └── open_deep_research/      # Research integration module
├── output/                      # Generated content (timestamped folders)
├── examples/                    # Usage examples and demos
└── langgraph.json              # LangGraph configuration
```

### Output Organization

All generated content is saved to timestamped folders in `output/`:

```
output/YYYY-MM-DD_HH-MM-SS/
├── 00_01a_storyline_competition_summary.md    # Competition overview
├── 00_01b_storyline_competition_details.md    # Detailed results
├── 01_storyline_option_1_full.md              # Generated storylines
├── 02_world_scenario_full.md                  # World building
├── 03_first_chapter_full.md                   # Chapter content
├── elo_leaderboard.md                         # Quality rankings
└── tournament_*.md                            # Debate transcripts
```

### Key Configuration Files

- **`src/co_scientist/configuration.py`**: Model templates, phase settings
- **`src/deep_sci_fi/deep_sci_fi_writer.py`**: Use case configurations  
- **`langgraph.json`**: Workflow definitions and API settings

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Work

- Uses [Open Deep Research](https://github.com/langchain-ai/open_deep_research) for automated web research and scientific fact-gathering
- Inspired by [DeepMind's AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) tournament-based hypothesis evaluation system

