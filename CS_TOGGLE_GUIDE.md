# 🔄 CS Toggle System Guide

## Overview

The Deep Sci-Fi Writer now supports a clean toggle between **CS Competition** and **Direct LLM** modes for all competitive steps. This allows for A/B testing, speed optimization, and flexible workflow adaptation.

## 🎯 How It Works

### Toggle Configuration
Located at the top of `src/deep_sci_fi/deep_sci_fi_writer.py`:

```python
# === CS TOGGLE CONFIGURATION ===
# Set to False to disable CS competition and use direct LLM calls instead
CS_ENABLED = True
```

### Affected Steps

When `CS_ENABLED = True` (Default):
- **Step 3**: Competitive Loglines → CS Competition with 3 research directions
- **Step 8**: Competitive Outline → CS competition with 3 outline approaches  
- **Step 11**: First Chapter → CS competition with 3 writing approaches
- **Step 12a-alt**: KEY Chapters → CS competition with specialist prompts

When `CS_ENABLED = False`:
- **Step 3**: Direct Loglines → Single GPT-5 call with structured 9-logline output
- **Step 8**: Direct Outline → Single Claude Opus call with comprehensive outline
- **Step 11**: Direct First Chapter → Single Claude Opus call with detailed requirements
- **Step 12a-alt**: Direct KEY Chapters → Single Claude Opus call with scientific rigor

## 🚀 Quick Switch Guide

### Enable CS Competition (Default)
```python
CS_ENABLED = True
```
- **Best for**: Final production runs, when quality is priority
- **Speed**: Slower (3-5x processing time for CS steps)
- **Quality**: Maximum creative variety and competitive refinement
- **User Interaction**: Requires logline selection (Step 3.5)

### Enable Direct LLM Mode  
```python
CS_ENABLED = False
```
- **Best for**: Speed testing, development, rapid iteration
- **Speed**: Faster (direct single calls)
- **Quality**: High-quality single responses with comprehensive prompts
- **User Interaction**: Same logline selection workflow maintained

## 📊 Comparison Matrix

| Aspect | CS Competition | Direct LLM |
|--------|----------------|------------|
| **Speed** | Slower (CS processing overhead) | Faster (direct calls) |
| **Quality** | Multiple approaches, competitive selection | Single comprehensive approach |
| **Resource Usage** | Higher (multiple model calls per step) | Lower (single calls) |
| **Creativity** | Maximum variety through competition | High quality through detailed prompts |
| **Debug/Development** | More complex to debug | Simpler, linear workflow |
| **A/B Testing** | Competitive benchmark | Direct comparison baseline |

## 🔧 Technical Implementation

### Wrapper Functions
All CS steps now use toggle wrapper functions:
- `generate_loglines_with_toggle()`
- `create_outline_with_toggle()`
- `write_first_chapter_with_toggle()`
- `write_key_chapter_with_toggle()`

### Transparent Integration
- Same input/output interfaces for both modes
- Identical state management
- Compatible file outputs (different prefixes: `03_competitive_` vs `03_direct_`)
- Same user selection workflow maintained

### Model Configuration
Both modes use the same model assignments:
- **Direct Loglines**: GPT-5 (general_creative)
- **Direct Outline**: Claude Opus 4.1 (chapter_writing)
- **Direct First Chapter**: Claude Opus 4.1 (chapter_writing)
- **Direct KEY Chapters**: Claude Opus 4.1 (chapter_writing)

## 🎯 Use Cases

### Production Runs
```python
CS_ENABLED = True  # Maximum quality, competitive refinement
```

### Development & Testing
```python
CS_ENABLED = False  # Fast iteration, simpler debugging
```

### A/B Comparison
1. Run with `CS_ENABLED = True` → Save outputs
2. Run with `CS_ENABLED = False` → Compare quality/speed
3. Choose optimal mode for your use case

### Speed-Critical Scenarios
```python
CS_ENABLED = False  # When time constraints are priority
```

## 📝 Output Differences

### File Naming
- **CS Mode**: `03_competitive_loglines.md`, `08_competitive_outline.md`
- **Direct Mode**: `03_direct_loglines.md`, `08_direct_outline.md`

### Content Structure
- **CS Mode**: Shows 3 approaches with competitive analysis
- **Direct Mode**: Shows comprehensive single response with structured sections

### Quality Characteristics
- **CS Mode**: Varied creative approaches, competitive refinement
- **Direct Mode**: Comprehensive coverage, consistent quality baseline

## 🔍 Logging & Observability

Each step logs its mode:
```
--- Generate Loglines: Using 🏆 CS Competition ---
--- Generate Loglines: Using ⚡ Direct LLM ---
```

Initialization shows current mode:
```
🔄 CS Toggle: 🏆 CS Competition mode enabled (CS_ENABLED = True)
🔄 CS Toggle: ⚡ Direct LLM mode enabled (CS_ENABLED = False)
```

## ⚙️ Advanced Configuration

### Per-Step Granular Control (Future Enhancement)
Could be extended to:
```python
CS_CONFIG = {
    "loglines": True,    # CS for loglines
    "outline": False,    # Direct for outline  
    "first_chapter": True,   # CS for first chapter
    "key_chapters": False    # Direct for KEY chapters
}
```

### Environment-Based Toggle
```python
import os
CS_ENABLED = os.getenv("CS_ENABLED", "true").lower() == "true"
```

## 🚀 Getting Started

1. **Choose your mode** by setting `CS_ENABLED` in `deep_sci_fi_writer.py`
2. **Run your workflow** - all CS steps automatically adapt
3. **Compare results** by switching modes and running again
4. **Optimize for your needs** - speed vs. competitive quality

The toggle system is fully modular and can be easily removed by replacing wrapper functions with direct calls to either mode. 