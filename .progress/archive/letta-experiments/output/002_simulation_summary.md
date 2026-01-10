# Simulation Summary: The Architect of Felt Worlds

*Ran December 27, 2025 to ground worldbuilding before writing story*

---

## Simulation 1: Memory Reconsolidation (Simple Model)

**Question:** How quickly do memories degrade through repeated recall?

**Model:** Memory as high-dimensional unit vector. Each recall adds Gaussian noise and reconsolidates the noisy version as the new "original."

**Finding:** Degradation is MUCH faster than intuition suggests.
- At σ=0.05 noise: after 4 recalls, only 20% similar to original
- At σ=0.10 noise: after 4 recalls, only 2% similar (essentially random)

**Problem:** This contradicts phenomenology—real memories don't completely randomize in 4 recalls.

---

## Simulation 2: Core/Periphery Memory Model

**Hypothesis:** Memories have a stable "core" (emotional gestalt, ~20% of signal) and a labile "periphery" (details like faces, ~80% of signal).

**Model:** Two separate vectors with different noise levels. Core has low noise (structural, redundant), periphery has high noise (activation patterns, easily perturbed).

**Results (medium disturbance, σ_core=0.02, σ_periph=0.15):**

| Recalls | Core Similarity | Periphery Similarity |
|---------|-----------------|---------------------|
| 0       | 100%            | 100%                |
| 1       | 98%             | 27%                 |
| 2       | 97%             | 7%                  |
| 3       | 96%             | -2%                 |
| 4       | 93%             | 0%                  |

**Story Implication:** After 4 recordings:
- Emotional core: 93% intact (still *feels* like the memory)
- Peripheral details: ~0% intact (faces gone, sequences scrambled)

This explains "I can't see her face" while the memory still feels true.

---

## Simulation 3: Self-Training Feedback Loop

**Question:** What happens when an artist:
1. Trains model on neural recordings
2. Experiences model's output
3. Records reaction to output
4. Uses reaction to train next version

**Parameters:**
- Emergence factor: 0.2 (20% of output is model's priors)
- Recognition weight: 0.6 (60% of reaction is artist's prior state)
- Experience noise: 0.1

**Results:**

| Iteration | Similarity to Original | Similarity to Model |
|-----------|----------------------|---------------------|
| 1         | 48%                  | 3%                  |
| 5         | 0%                   | 7%                  |
| 10        | -7%                  | -5%                 |
| 20        | -11%                 | 5%                  |

**Key Finding:** The loop creates NOVELTY.
- Does NOT converge to original self
- Does NOT converge to model's priors
- Drifts into entirely new territory (neither Nia nor AI)
- After 20 iterations: anti-correlated with original (-11%)

---

## Simulation 4: Parameter Space Exploration

**Question:** What conditions preserve vs transform the artist?

**Results:** Regardless of parameters (emergence 0.1-0.4, recognition 0.3-0.9), after 20 iterations similarity to original approaches random chance (~0-2%).

The noise dominates over longer timescales—there's no stable attractor.

---

## Simulation 5: Short-Term Dynamics (Realistic Scenario)

**Question:** What happens in 3-10 iterations with professional low-noise recording?

**Professional Setup (noise=0.02):**

| Iteration | Similarity to Original | Change from Start |
|-----------|----------------------|-------------------|
| 0         | 100%                 | 0%                |
| 1         | 90.5%                | 9.5%              |
| 3         | 72.5%                | 27.5%             |
| 5         | 58.7%                | 41.3%             |
| 7         | 47.8%                | 52.2%             |
| 10        | 35.9%                | 64.1%             |

**Rate of drift:** ~8% per iteration (professional), ~18% per iteration (home setup)

**Story Implication:**
- Iteration 7: 48% similar → she NOTICES something is different
- Iteration 10: 36% similar → substantial transformation, still recognizable
- She's NOT becoming the AI (only ~20% similar to model priors)
- She's becoming a THIRD THING

---

## Simulation 6: Information Theory of Neural Recording

**Physical Parameters (from 2024 Nature Electronics paper):**
- Electrodes: 65,536
- Sampling: 1000 Hz, 16-bit resolution
- Raw data rate: 125 MB/sec = 439.5 GB/hour

**Brain Coverage:**
- Each electrode averages ~10,000 neurons
- Effective neurons sensed: ~0.7 billion
- Coverage of total brain: **0.8%**

**What ECoG Actually Captures:**
- ✓ Emotional valence (amygdala activation patterns)
- ✓ Attention/salience (frontal activity)
- ✓ Broad perceptual categories (visual cortex patterns)
- ✓ Temporal structure (sequence of activation)

**What ECoG Cannot Capture:**
- ✗ Individual neuron firing (only population averages)
- ✗ Specific memory content (faces, words, details)
- ✗ Hippocampal activity (deep structure, needs different tech)
- ✗ The 'movie' of the memory (just the emotional envelope)

**Story Implication:**
Nia's recordings are NOT capturing memories as images. She's capturing the EMOTIONAL ENVELOPE:
- "This moment felt important"
- "I was paying attention here"
- "There was a smell trigger"
- "I felt sad, then surprised"

The world model RECONSTRUCTS sensory details from:
1. Her emotional envelope (neural recordings)
2. Self-reported context ("grandmother's kitchen")
3. Learned priors about kitchens, grandmothers, etc.

Her mother's face fades because **she never recorded it**—only the emotion of seeing it.

---

## Synthesis: How Simulations Changed the Story

| Original Assumption | Simulation Finding | Story Change |
|--------------------|-------------------|--------------|
| Memories erode gradually | Core stable (93%), periphery gone (0%) after 4 recalls | She can't see her mother's face—she recorded the *feeling*, not the image |
| She's dissolving into the AI | Only 20% correlated with model priors | She's becoming a THIRD THING, genuine novelty |
| Vague existential drift | 8% per iteration, 48% at iter 7, 36% at iter 10 | Specific moment: "48% correlated with session-one Nia" |
| Recording memories | 125 MB/sec captures emotional envelope only | Model hallucinates sensory details to match feeling-map |
| Mirror shows unknown future | Projection of drift vector forward | Model extrapolated iteration-20 Nia from trajectory |

---

## Code Used

All simulations run in JavaScript due to Python sandbox issues. Key models:

1. **Memory vector:** High-dimensional unit vector, noise added per recall
2. **Core/periphery:** Two vectors with different noise parameters
3. **Feedback loop:** Generate → experience → record → train cycle
4. **Information theory:** Direct calculation from electrode specs

---

## References

- Nature Electronics (Dec 2024): "Wireless subdural-contained BCI with 65,536 electrodes"
- Bridge et al., Northwestern: Memory reconsolidation research
- DeepMind (2024): Genie 2 foundation world model
- US Copyright Office (Jan 2025): AI authorship ruling
