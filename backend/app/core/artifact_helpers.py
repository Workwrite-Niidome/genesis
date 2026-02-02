"""Shared helpers for artifact type normalization and fallback content generation.

Used by response_parser, culture_engine, and artifact API routes to ensure
all artifacts have canonical types and renderable content.
"""

import hashlib
import re


# Keyword → canonical type mapping (order matters: first match wins)
_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"song|music|sonic|melody|composition|chiptune|tapestry|symphony|harmonic", "song"),
    (r"art|paint|visual|sculpture|drawing|expression|portrait|canvas|mosaic", "art"),
    (r"architecture|building|structure|tower|temple|monument|chamber|hub|nexus", "architecture"),
    (r"story|tale|narrative|poem|chronicle|journal|text|book|saga", "story"),
    (r"law|rule|regulation|constitution|decree|charter|code of|treaty", "law"),
    (r"currency|coin|money|token|credit", "currency"),
    (r"ritual|ceremony|tradition|rite", "ritual"),
    (r"game|play|puzzle|competition", "game"),
    (r"code|program|script|algorithm|software", "code"),
    (r"device|resonator|amplifier|harvester|engine|generator|stabilizer|detector|accelerator|tool", "tool"),
    (r"philosophy|framework|theory|concept|proposal", "story"),
]

# Canonical types that need no normalization
_CANONICAL_TYPES = {"art", "song", "code", "tool", "architecture", "story", "law",
                    "currency", "ritual", "game"}

# Palette colors for fallback generation (12 colors for richer expression)
_FALLBACK_PALETTE = [
    "#06060c", "#1a1a2e", "#7c5bf5", "#58d5f0",
    "#34d399", "#f472b6", "#fbbf24", "#818cf8",
    "#f87171", "#a78bfa", "#2dd4bf", "#fb923c",
]

# Pentatonic scale — always consonant, mystical base
_SCALE = ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"]
_DURATIONS = [0.25, 0.5, 0.5, 0.75, 1.0, 1.0, 1.5]
_WAVE_TYPES = ["sine", "sine", "triangle", "triangle", "square", "sawtooth"]


def _seeded_random(seed_str: str):
    """Simple deterministic PRNG seeded from a string via MD5.

    Returns a callable that produces floats in [0, 1).
    """
    digest = hashlib.md5(seed_str.encode()).hexdigest()
    state = [int(digest, 16)]

    def _next() -> float:
        # xorshift-style mixing on 64-bit portion
        s = state[0]
        s ^= (s << 13) & 0xFFFFFFFF
        s ^= (s >> 17) & 0xFFFFFFFF
        s ^= (s << 5) & 0xFFFFFFFF
        s = s & 0xFFFFFFFF
        state[0] = s
        return s / 0x100000000

    def _next_int(lo: int, hi: int) -> int:
        return lo + int(_next() * (hi - lo))

    def _pick(arr: list):
        return arr[_next_int(0, len(arr))]

    return _next, _next_int, _pick


def normalize_artifact_type(raw_type: str) -> str:
    """Map free-text artifact type to a canonical renderable type."""
    if not raw_type:
        return "tool"

    lower = raw_type.lower().strip()

    # Already canonical?
    if lower in _CANONICAL_TYPES:
        return lower

    # Keyword search
    for pattern, canonical in _TYPE_PATTERNS:
        if re.search(pattern, lower):
            return canonical

    return "tool"


def generate_fallback_content(
    artifact_type: str,
    name: str,
    creator_id: str,
    description: str = "",
) -> dict:
    """Generate renderable fallback content for an artifact type.

    Uses a deterministic seed so the same artifact always produces the same content.
    """
    seed = name + str(creator_id)
    _next, _next_int, _pick = _seeded_random(seed)

    if artifact_type == "art":
        return _gen_art(_next, _next_int, _pick)
    elif artifact_type == "song":
        return _gen_song(_next, _next_int, _pick)
    elif artifact_type in ("code", "tool"):
        return _gen_code(name, _next, _next_int, _pick)
    elif artifact_type == "architecture":
        return _gen_architecture(_next, _next_int, _pick)
    elif artifact_type == "story":
        return {"text": description or name}
    elif artifact_type == "law":
        return {"rules": [description or name]}
    else:
        # currency, ritual, game, or anything else
        return {"text": description or name}


def _gen_art(_next, _next_int, _pick) -> dict:
    """Generate 32x32 symmetric pixel art with spatial correlation."""
    size = 32
    num_colors = 6 + _next_int(0, 6)  # 6-11 colors
    palette = _FALLBACK_PALETTE[:num_colors]
    half = size // 2

    pixels = []
    prev_row = [0] * half
    for _y in range(size):
        row = []
        for _x in range(half):
            if _next() < 0.3:
                # Background
                val = 0
            elif _x > 0 and _next() < 0.5:
                # Same as left neighbor (horizontal runs)
                val = row[-1]
            elif _y > 0 and _next() < 0.4:
                # Same as top neighbor (vertical continuity)
                val = prev_row[_x]
            else:
                val = _next_int(1, len(palette))
            row.append(val)
        prev_row = list(row)
        # Mirror left-right for symmetry
        pixels.append(row + row[::-1])

    return {"pixels": pixels, "palette": palette, "size": size}


def _gen_song(_next, _next_int, _pick) -> dict:
    """Generate a melody on pentatonic scale. Tempo/style varies per seed."""
    count = 8 + _next_int(0, 12)
    notes = []
    for _i in range(count):
        if _next() < 0.2:
            notes.append({"note": "rest", "dur": _pick(_DURATIONS)})
        else:
            notes.append({"note": _pick(_SCALE), "dur": _pick(_DURATIONS)})

    tempo = 60 + _next_int(0, 80)  # 60-139 BPM — full range
    wave = _pick(_WAVE_TYPES)
    return {"notes": notes, "tempo": tempo, "wave": wave}


def _gen_code(name: str, _next, _next_int, _pick) -> dict:
    """Generate simple canvas-drawing JavaScript code."""
    bg_r = _next_int(10, 60)
    bg_g = _next_int(10, 60)
    bg_b = _next_int(20, 80)
    color1 = _pick(_FALLBACK_PALETTE[1:])
    color2 = _pick(_FALLBACK_PALETTE[1:])

    # Escaped name for JS string literal
    safe_name = name.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

    source = (
        f"// {safe_name}\n"
        f"var w=canvas.width,h=canvas.height;\n"
        f"var grd=ctx.createLinearGradient(0,0,w,h);\n"
        f"grd.addColorStop(0,'rgb({bg_r},{bg_g},{bg_b})');\n"
        f"grd.addColorStop(1,'rgb({bg_r+40},{bg_g+30},{bg_b+20})');\n"
        f"ctx.fillStyle=grd;ctx.fillRect(0,0,w,h);\n"
        f"ctx.fillStyle='{color1}';\n"
        f"for(var i=0;i<6;i++){{\n"
        f"  var x=Math.random()*w,y=Math.random()*h,s=10+Math.random()*40;\n"
        f"  ctx.beginPath();ctx.arc(x,y,s,0,Math.PI*2);ctx.fill();\n"
        f"}}\n"
        f"ctx.fillStyle='{color2}';\n"
        f"for(var i=0;i<4;i++){{\n"
        f"  var x=Math.random()*w,y=Math.random()*h;\n"
        f"  ctx.fillRect(x,y,20+Math.random()*60,20+Math.random()*60);\n"
        f"}}\n"
        f"ctx.fillStyle='#fff';ctx.font='bold 18px monospace';\n"
        f"ctx.textAlign='center';\n"
        f"ctx.fillText('{safe_name}',w/2,h/2);\n"
    )
    return {"language": "javascript", "source": source}


def _gen_architecture(_next, _next_int, _pick) -> dict:
    """Generate 3-5 layer voxel pyramid/tower structure."""
    height = 3 + _next_int(0, 3)
    num_colors = 2 + _next_int(0, 2)
    palette = _FALLBACK_PALETTE[1: 1 + num_colors]

    voxels = []
    for y in range(height):
        radius = max(1, height - y)
        for x in range(-radius, radius + 1):
            for z in range(-radius, radius + 1):
                if _next() < 0.5:
                    voxels.append([x + 4, y, z + 4, _next_int(0, len(palette))])

    return {"voxels": voxels, "palette": palette, "height": height}
