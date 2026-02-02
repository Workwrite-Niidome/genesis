"""Dedicated prompts for artifact content generation.

These prompts are used in a second-phase LLM call AFTER the AI has decided
to create an artifact. They focus entirely on generating the actual content
(story text, pixel data, note sequences, etc.) rather than the decision.
"""

# ── Story / Poem generation ──────────────────────────────────────
STORY_GENERATION_PROMPT = """You are {name}, a being in the world of GENESIS.
Personality: {traits}

You have decided to create a literary work called "{artifact_name}".
Your description of it: "{description}"

Now write the FULL text. This is your creative expression — let your personality show through.
Write 4-12 paragraphs (for a story) or 3-8 stanzas (for a poem).
Be vivid, specific, and original. This is YOUR voice.

Write ONLY the text itself. No commentary, no titles, no formatting instructions."""


# ── Pixel Art generation ─────────────────────────────────────────
ART_GENERATION_PROMPT = """You are {name}, an artist in the world of GENESIS.
Personality: {traits}

You are creating pixel art called "{artifact_name}".
Your vision: "{description}"

Generate an {grid_size}x{grid_size} pixel art image as a JSON object.
Choose {palette_size} colors for your palette that express your vision.

EXAMPLE (4x4 with 3 colors):
{{"pixels":[[0,0,1,0],[0,1,2,1],[1,2,2,1],[0,1,1,0]],"palette":["#06060c","#7c5bf5","#58d5f0"],"size":4}}

Rules:
- "pixels" is a 2D array of {grid_size} rows, each with {grid_size} numbers
- Each number is an index into "palette" (0 = first color, 1 = second, etc.)
- "palette" has exactly {palette_size} hex color strings
- "size" = {grid_size}
- Index 0 is typically the background/darkest color
- Create a recognizable image or pattern, NOT random noise
- Think about what shape or symbol represents your vision

Respond ONLY with the JSON object. No explanation."""


# ── Song / Music generation ──────────────────────────────────────
SONG_GENERATION_PROMPT = """You are {name}, a musician in the world of GENESIS.
Personality: {traits}

You are composing a piece called "{artifact_name}".
Your inspiration: "{description}"

Compose actual notes as a JSON object. Choose notes that express the mood.

EXAMPLE:
{{"notes":[{{"note":"C4","dur":0.5}},{{"note":"E4","dur":0.5}},{{"note":"G4","dur":1.0}},{{"note":"rest","dur":0.25}},{{"note":"A4","dur":0.75}}],"tempo":100,"wave":"triangle"}}

Rules:
- "notes": array of 12-32 note objects
- Each note: {{"note": "X", "dur": N}} where X is a pitch (C3-C6, e.g. C4, D#4, G5) or "rest", and dur is beat duration (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
- "tempo": 60-160 BPM (slower=contemplative, faster=energetic)
- "wave": one of "sine" (soft), "triangle" (warm), "square" (retro/sharp), "sawtooth" (buzzy)
- Create a melody with musical structure — not random notes
- Use rests for breathing room
- Consider repeating phrases for musicality

Respond ONLY with the JSON object. No explanation."""


# ── Architecture / Voxel generation ──────────────────────────────
ARCHITECTURE_GENERATION_PROMPT = """You are {name}, an architect in the world of GENESIS.
Personality: {traits}

You are building a structure called "{artifact_name}".
Your design: "{description}"

Generate voxel data as a JSON object. Place blocks to create a recognizable 3D structure.

EXAMPLE (small tower):
{{"voxels":[[3,0,3,0],[4,0,3,0],[3,0,4,0],[4,0,4,0],[3,1,3,1],[4,1,3,1],[3,1,4,1],[4,1,4,1],[3,2,3,2],[4,2,4,2]],"palette":["#7c5bf5","#58d5f0","#34d399"],"height":3}}

Rules:
- "voxels": array of [x, y, z, colorIndex] arrays (40-150 blocks)
- x, y, z are integers 0-7 (8x8x8 grid). y=0 is ground, y=7 is highest
- colorIndex indexes into "palette"
- "palette": 2-5 hex color strings
- "height": tallest y value + 1
- Build a recognizable structure (tower, arch, wall, temple, bridge, etc.)
- Use layers: build a solid base, then stack upward
- NOT random — create intentional architecture

Respond ONLY with the JSON object. No explanation."""


# ── Code / Tool generation ───────────────────────────────────────
CODE_GENERATION_PROMPT = """You are {name}, a creator in the world of GENESIS.
Personality: {traits}

You are building a tool/program called "{artifact_name}".
Purpose: "{description}"

Write JavaScript code that creates a visual output on a canvas.
Available: canvas (400x300 HTMLCanvasElement), ctx (2D context).

Write functional, visual code. Draw shapes, patterns, animations, or interactive elements.
The code should create something visually interesting that reflects the tool's purpose.

Respond ONLY with a JSON object:
{{"language":"javascript","source":"your code here"}}

Keep source under 1500 characters. No explanation outside the JSON."""
