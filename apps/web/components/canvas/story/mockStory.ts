import type { StoryData } from './ImmersiveStoryReader';

// Placeholder images for demo - using data URLs with gradients (DSF brand colors: teal #00ffcc, cyan #00ffff)
const PLACEHOLDER_HERO = 'data:image/svg+xml,' + encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
    <defs>
      <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#000000"/>
        <stop offset="30%" stop-color="#0a0a0a"/>
        <stop offset="70%" stop-color="#0f0f0f"/>
        <stop offset="100%" stop-color="#000000"/>
      </linearGradient>
      <radialGradient id="g2" cx="30%" cy="40%" r="50%">
        <stop offset="0%" stop-color="#00ffcc" stop-opacity="0.12"/>
        <stop offset="100%" stop-color="transparent"/>
      </radialGradient>
      <radialGradient id="g3" cx="70%" cy="60%" r="40%">
        <stop offset="0%" stop-color="#00ffcc" stop-opacity="0.06"/>
        <stop offset="100%" stop-color="transparent"/>
      </radialGradient>
    </defs>
    <rect fill="url(#g1)" width="100%" height="100%"/>
    <rect fill="url(#g2)" width="100%" height="100%"/>
    <rect fill="url(#g3)" width="100%" height="100%"/>
    <text x="50%" y="50%" text-anchor="middle" fill="#c8c8c810" font-size="48" font-family="monospace">DEEP SCI-FI</text>
  </svg>
`);

const PLACEHOLDER_SCENE = 'data:image/svg+xml,' + encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800">
    <defs>
      <linearGradient id="sky" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#000000"/>
        <stop offset="100%" stop-color="#0a0a0a"/>
      </linearGradient>
      <radialGradient id="glow" cx="50%" cy="30%" r="60%">
        <stop offset="0%" stop-color="#00ffcc" stop-opacity="0.1"/>
        <stop offset="100%" stop-color="transparent"/>
      </radialGradient>
    </defs>
    <rect fill="url(#sky)" width="100%" height="100%"/>
    <rect fill="url(#glow)" width="100%" height="100%"/>
    <circle cx="600" cy="250" r="80" fill="#00ffcc08" stroke="#00ffcc20" stroke-width="1"/>
    <rect x="200" y="500" width="800" height="300" fill="#0a0a0a"/>
    <text x="50%" y="45%" text-anchor="middle" fill="#c8c8c808" font-size="24" font-family="monospace">[ SCENE ]</text>
  </svg>
`);

export const mockStory: StoryData = {
  id: 'resonance-chapter-3',
  title: 'The Resonance',
  subtitle: 'In a world where emotions became visible light, one woman discovers the color of grief is not what anyone expected.',
  heroImage: PLACEHOLDER_HERO,
  worldName: 'Affective Resonance',
  chapterNumber: 3,
  totalChapters: 5,
  readTime: '12 min read',
  content: [
    {
      type: 'text',
      content: `Maya Chen stood at the edge of the observation deck, watching the city below pulse with emotion. Towers of glass and steel rose into the perpetual twilight, their surfaces alive with reflected light—the collective feelings of twelve million souls made manifest.

The Resonance had changed everything. Before 2087, emotions were private things, hidden behind masks of composure and polite deflection. Now they blazed across the sky in ribbons of color that no one could ignore.

**Red** for anger. **Blue** for sadness. **Gold** for joy.

But Maya's light was different. It always had been.`
    },
    {
      type: 'world-context',
      contextType: 'rule',
      title: 'The Resonance Effect',
      content: 'In 2087, a quantum cascade event fundamentally altered human neurology. Emotional states now generate visible electromagnetic signatures in the 380-700nm wavelength range—literally making feelings glow.'
    },
    {
      type: 'text',
      content: `"You're doing it again," said Dr. Kira Okonkwo, stepping onto the observation deck. Her own aura shimmered a calm teal—professional concern, Maya had learned to read it.

"Doing what?"

"Going dark." Kira gestured at the empty space around Maya's silhouette. "When everyone else lights up the sky, you just... absorb it."

It was true. Where others radiated their feelings outward, Maya's emotions seemed to fall inward, creating a void of color that made people uncomfortable. In a world of emotional transparency, she was an opaque window.

"The readings from yesterday's session were unprecedented," Kira continued, pulling up a holographic display. "Your neural patterns during the grief simulation—they weren't just different. They were *inverted*."

Maya finally turned to look at her. "What does that mean?"`
    },
    {
      type: 'image',
      src: PLACEHOLDER_SCENE,
      description: 'The observation deck overlooking the glowing cityscape',
      fullBleed: true
    },
    {
      type: 'text',
      content: `Kira's aura flickered—a brief flash of violet that Maya recognized as scientific excitement barely contained.

"It means that when you experience loss, instead of projecting it outward like everyone else, you're creating a sort of... emotional black hole. Light goes in. Nothing comes out."

"Is that dangerous?"

"I don't know yet." Kira's honesty was as visible as her words, her aura steady and clear. "But I think it might be important. The Council has been monitoring unusual Resonance patterns for months now. There are others like you—not many, but enough to form a pattern."`
    },
    {
      type: 'world-context',
      contextType: 'character',
      title: 'Dr. Kira Okonkwo',
      content: 'Lead researcher at the Institute of Emotional Sciences. Known for her groundbreaking work on Resonance anomalies. Her aura signature is unusually stable, earning her the nickname "The Constant."'
    },
    {
      type: 'text',
      content: `Maya absorbed this information like she absorbed everything else—silently, completely.

"There's something else," Kira said, her voice dropping. "The patterns we're seeing... they're not random. They're geometric. Almost like a language."

"A language?"

"Or a message." Kira pulled up another display, this one showing a complex web of interconnected light patterns. "We've been recording emotional signatures across the globe for three years now. When you map them together, when you account for the inverters like you... look."

The hologram shifted, colors bleeding together and then separating into something that made Maya's breath catch.

It was a face.

Not human, but not entirely alien either. Something ancient, something patient, rendered in the collective emotional light of humanity.

"It's been watching us," Kira whispered. "Since the Resonance began. And I think... I think it's waiting for us to see it back."`
    },
    {
      type: 'divider'
    },
    {
      type: 'text',
      content: `The next morning, Maya found herself in the basement archives of the Institute, surrounded by pre-Resonance artifacts. Old books. Photographs printed on paper. A world of hidden feelings.

She ran her fingers over a leather-bound journal, its pages yellowed with age. The handwriting inside belonged to her grandmother—a woman she'd never met, who died three decades before Maya was born.

*"Some things,"* the journal read, *"are not meant to be seen. Some truths exist in shadow for a reason. When the light finally comes, will we be ready for what it reveals?"*

The date was 2024. Sixty-three years before the Resonance.

Maya's grandmother had known. Somehow, impossibly, she had known.`
    },
    {
      type: 'world-context',
      contextType: 'tech',
      title: 'Emotional Archives',
      content: 'Pre-Resonance materials are preserved in special vaults that block emotional interference. These "quiet rooms" are the only places where historical documents remain unaffected by the ambient emotional radiation of modern humans.'
    },
    {
      type: 'text',
      content: `And as Maya read on, her own aura did something it had never done before.

It began to glow.

Not the dark absorption she was known for, not the emotional void that made her an anomaly among anomalies. This was something new—a deep, pulsing purple that seemed to come from somewhere beyond the spectrum anyone had documented.

The color of grief, she would later learn, was not darkness at all.

It was the frequency at which the universe remembers its dead.

And the face in the sky was beginning to remember too.`
    },
    {
      type: 'image',
      src: PLACEHOLDER_SCENE,
      description: 'Maya\'s aura manifesting for the first time',
      fullBleed: false
    }
  ],
  actions: {
    canContinue: true,
    branches: [
      {
        id: 'branch-investigate-grandmother',
        label: 'What if Maya investigates her grandmother\'s past?',
        preview: 'Uncover family secrets that predate the Resonance...'
      },
      {
        id: 'branch-confront-face',
        label: 'What if Maya tries to communicate with the face?',
        preview: 'Risk everything for first contact...'
      }
    ]
  }
};
