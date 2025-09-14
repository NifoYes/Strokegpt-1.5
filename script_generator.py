import random

# ===== ALWAYS-ON OBSERVER DEBUG (read-only) =====
_LAST_TEXT = ""
_LAST_MATCHES = {}

def _observer_note_text(text: str):
    global _LAST_TEXT
    _LAST_TEXT = text or ""

# Keyword map used only to EXPLAIN cues (does NOT change behavior)
_OBSERVER_KEYWORDS = {
    "slow": ["slow", "gentle", "soft", "tender"],
    "fast": ["fast", "faster", "quick", "rapid"],
    "tip_only": ["tip", "glans", "head"],
    "base_only": ["base", "root", "shaft base"],
    "deep": ["deep", "deeper", "down", "bottom"],
    "circular": ["circle", "circular", "swirl", "spiral"],
    "edge": ["edge", "edging", "hold", "tease"],
    "short": ["short", "shallow"],
    "long": ["long", "full", "all the way"],
}

def _observer_match_keywords(text: str, cues: dict):
    global _LAST_MATCHES
    t = (text or "").lower()
    matches = {}
    for cue, words in _OBSERVER_KEYWORDS.items():
        hits = [w for w in words if w in t]
        if hits:
            matches[cue] = hits
    if isinstance(cues, dict):
        matches = {k: v for k, v in matches.items() if cues.get(k)}
    _LAST_MATCHES = matches
    return matches

def _observer_show_debug(phase, cues, moves):
    try:
        print("\n[SCRIPT DEBUG] mapping >>>")
        if phase:
            print(f"phase: {phase}")
        print(f"raw_text: {_LAST_TEXT!r}")
        if _LAST_MATCHES:
            print("matches:")
            for cue, hits in _LAST_MATCHES.items():
                print(f"  {hits!r} → {cue}")
        print(f"cues: {cues}")
        if isinstance(moves, list):
            print("moves (speed,depth,range,duration):")
            for i, m in enumerate(moves[:12]):
                speed = m.get('sp'); depth = m.get('dp'); rng = m.get('rng'); dur = m.get('duration', 0)
                print(f"  #{i:02d} -> speed={speed}, depth={depth}, range={rng}, duration={dur}")
        elif isinstance(moves, dict):
            m = moves
            print("move:", { 'speed': m.get('sp'), 'depth': m.get('dp'), 'range': m.get('rng'), 'duration': m.get('duration',0) })
        print("[/SCRIPT DEBUG]\n")
    except Exception as _e:
        print(f"[SCRIPT DEBUG ERROR] {_e}")


def parse_cues_from_text(text: str) -> dict:
    """
    Parse user text and return a dictionary of high‑level cues.

    The following cues may be set to True when matched:
      * ``fast``    – the user asks for more speed.
      * ``slow``    – the user asks to slow down or be gentle.
      * ``tip_only`` – focus stimulation near the tip (or glans).
      * ``base_only`` – focus near the base/root.
      * ``full``    – request for full strokes from tip to base.

    The parser is bilingual (English/Italian) and matches common synonyms and
    variations (e.g. plural forms like "tips").
    The returned dictionary only includes keys present in the user text.
    """
    global _LAST_TEXT
    _LAST_TEXT = text or ""

    cues: dict[str, bool] = {}
    if not text:
        try:
            _observer_match_keywords(text, cues)
        except Exception:
            pass
        return cues

    lower = (text or "").lower()

    # Speed cues
    # Explicit fast/slow synonyms (English + Italian).  Fast also includes phrases
    # signalling imminent climax ("I'm coming", "sto venendo", "gonna cum") to
    # encourage escalation instead of slowing down.
    if any(k in lower for k in [
        "fast", "faster", "veloce", "più veloce", "svelto", "rapido", "accelera",
        "i'm coming", "im coming", "i'm gonna cum", "i am coming", "gonna cum",
        "sto venendo", "vengo", "sto per venire", "sono in arrivo", "sto arrivando"
    ]):
        cues["fast"] = True
    if any(k in lower for k in [
        "slow", "slowly", "gentle", "gently", "piano", "lento", "lentamente", "rallenta",
        "slow down", "take it slow", "vai piano", "più piano", "meno veloce"
    ]):
        cues["slow"] = True

    # Coming cues imply full strokes: treat "I'm coming"/"gonna cum" as near full
    if any(k in lower for k in [
        "i'm coming", "im coming", "i am coming", "i'm gonna cum", "im gonna cum", "gonna cum",
        "i'm going to cum", "im going to cum", "going to cum"
    ]):
        cues["full"] = True
        cues["coming"] = True

    # Full stroke cues
    if any(k in lower for k in [
        "full stroke", "full strokes", "all the way", "entire length", "whole length",
        "tip to base", "tip-to-base", "from tip to base", "from base to tip", "down to the base",
        "long strokes", "from top to bottom",
        "corsa completa", "tutta la corsa", "fino in fondo", "dal top alla base", "dalla punta alla base"
    ]):
        cues["full"] = True

    # Tip‑focused cues – include plural and generic "tip"
    if any(k in lower for k in [
        "just the tip", "only the tip", "just the head", "only the head", "head only",
        "on the tip", "at the tip", "glans", "glande",
        "solo la punta", "sulla punta", "alla punta", "punta soltanto", "solo la testa", "sulla testa", "sulla cima",
        "tip", "tips", "my tip", "my tips", "la punta", "le punte"
    ]):
        cues["tip_only"] = True

    # Base‑focused cues – include generic base synonyms
    if any(k in lower for k in [
        "base only", "only the base", "just the base", "at the base", "down at the base",
        "near the base", "toward the base", "close to the base", "root only", "at the root",
        "solo la base", "alla base", "sulla base", "verso la base", "alla radice", "sulla radice",
        "giù in fondo", "parte bassa", "solo in basso", "alla base soltanto", "base", "a fondo", "profondo"
    ]):
        cues["base_only"] = True

    # Treat "deep" and variations as base focus
    if any(k in lower for k in ["deep", "deeper", "profondo", "a fondo", "fond", "profonda"]):
        cues["base_only"] = True

    try:
        _observer_match_keywords(text, cues)
    except Exception:
        pass
    return cues


# Track previous move and phase globally for smoothing/clamping
_LAST_MOVE: dict[str, int] | None = None
_LAST_PHASE: str | None = None

def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))

def _compute_sp_adjusted(base_sp: int, dp: int, rng: int) -> int:
    """
    Adjust the base speed according to depth.  Larger offsets from the centre
    depth (50) warrant slightly faster speeds to compensate for less perceived
    pressure.  Range scaling is handled separately by generate_moves.

    We remove the range factor here so that speed can be explicitly scaled
    relative to stroke length in the calling code.  The depth factor is
    retained: 1.0 + 0.3×(|dp − 50|/50) gives values ≥1.
    """
    d_factor = 1.0 + 0.3 * (abs(dp - 50) / 50.0)
    sp = int(round(base_sp * d_factor))
    return _clamp(sp, 1, 100)

def generate_moves(phase: str = "WARM-UP", cues: dict | None = None) -> list[dict[str, int]]:
    """
    Generate a list of moves respecting the current phase and user cues.

    ``phase`` selects one of the envelopes defined below.  ``cues`` can
    nudge speed (fast/slow) or steer focus (tip_only, base_only, full).
    Moves are smoothed relative to the previous call while staying within
    envelope bounds.  When the phase changes, the smoothing state resets.
    """
    global _LAST_MOVE, _LAST_PHASE
    cues = cues or {}
    phase_upper = str(phase).upper() if isinstance(phase, str) else "WARM-UP"

    # Reset smoothing when phase changes
    if _LAST_PHASE != phase_upper:
        _LAST_MOVE = None
        _LAST_PHASE = phase_upper

    # Envelope definitions: (min, max) for sp, dp, rng and durations in ms
    # Envelope definitions: (min, max) for sp, dp, rng and durations in ms.
    # These values align with the phase envelopes defined in the main app.
    ENVELOPES = {
        "WARM-UP": {
            # gentle to moderate speeds for warm‑up; allow variation up to ~35
            "sp": (15, 35),
            "dp": (40, 60),
            "rng": (25, 45),
            # longer strokes: 2–3.5 s per move
            # adjust durations: 3–3.5s per stroke
            "dur": (3000, 3500),
        },
        "ACTIVE": {
            # higher speeds and wider range for active play
            "sp": (45, 85),
            "dp": (50, 80),
            # widen active range slightly for orgasmic strokes
            "rng": (50, 80),
            # medium strokes: 2.5–3 s per move
            "dur": (2500, 3000),
        },
        "RECOVERY": {
            # very slow and gentle during recovery
            "sp": (5, 15),
            "dp": (35, 55),
            # Increase amplitude in recovery slightly
            "rng": (20, 40),
            # longest strokes: 3.5–4.5 s per move
            "dur": (3500, 4500),
        },
    }
    env = ENVELOPES.get(phase_upper, ENVELOPES["WARM-UP"])
    sp_min, sp_max = env["sp"]
    dp_min, dp_max = env["dp"]
    rng_min, rng_max = env["rng"]
    dur_min, dur_max = env["dur"]

    # Number of moves per batch.  Using more moves yields longer continuous
    # sequences (e.g., 10 moves × 3–3.5 s ≈ 30–35 s) before the next user input is needed.
    num_moves = 10
    moves: list[dict[str, int]] = []

    # Maximum deltas for smoothing across moves.  Lower deltas produce
    # smoother transitions between moves and across batches.
    # Maximum deltas for smoothing across moves.  Lower values yield smoother
    # transitions both within and across batches.  Tightened deltas reduce
    # abrupt jumps in speed, depth and range.
    MAX_DELTA = {"sp": 6, "dp": 10, "rng": 10}

    for _ in range(num_moves):
        # Base random values within envelope
        base_sp = random.randint(sp_min, sp_max)
        dp = random.randint(dp_min, dp_max)
        rng = random.randint(rng_min, rng_max)
        duration = random.randint(dur_min, dur_max)

        # Apply speed cues: adjust base_sp but keep within absolute bounds.
        if cues.get("fast") and not cues.get("slow"):
            # Increase speed for fast cue.  Allow overshooting envelope slightly up to +12.
            base_sp = _clamp(base_sp + 8, sp_min, min(100, sp_max + 12))
        if cues.get("slow") and not cues.get("fast"):
            # Decrease speed for slow cue.  Allow dipping below envelope slightly.
            base_sp = _clamp(base_sp - 8, max(1, sp_min - 5), sp_max)

        # Determine zone and amplitude based on cues.  We combine cues rather than
        # overwrite them: e.g. tip + full results in a tip‑focused full stroke.
        dp_override = False
        rng_override = False
        # Flags to detect presence of tip/base/full independently
        tip_flag = bool(cues.get("tip_only"))
        base_flag = bool(cues.get("base_only"))
        full_flag = bool(cues.get("full"))
        coming_flag = bool(cues.get("coming"))

        # Adjust dp/rng based on combination of flags
        if tip_flag and base_flag:
            # Conflicting cues: default to phase envelope (ignore both)
            pass
        elif tip_flag and full_flag:
            # Tip zone with full‑stroke amplitude: high dp, mid–high range
            dp = random.randint(85, 95)
            rng = random.randint(40, 70)
            dp_override = True
            rng_override = True
        elif base_flag and full_flag:
            # Base zone with full‑stroke amplitude: low dp, mid–high range
            dp = random.randint(5, 15)
            rng = random.randint(40, 70)
            dp_override = True
            rng_override = True
        elif full_flag:
            # Pure full stroke: centre dp with very wide range
            dp = random.randint(45, 55)
            rng = random.randint(60, 100)
            dp_override = True
            rng_override = True
        elif tip_flag:
            # Tip focus: high dp, narrow range
            dp = random.randint(85, 95)
            rng = random.randint(10, 20)
            dp_override = True
            rng_override = True
        elif base_flag:
            # Base focus: low dp, narrow range
            dp = random.randint(5, 15)
            rng = random.randint(10, 20)
            dp_override = True
            rng_override = True

        # Coming cue: treat like near‑full stroke with extended duration.  If
        # another zone cue exists, widen the range further but keep the zone.
        if coming_flag:
            # Extend duration beyond normal envelope: 3.5–7 s
            duration = random.randint(3500, 7000)
            # If dp/rng were not overridden above, treat as full stroke
            if not (dp_override or rng_override):
                dp = random.randint(45, 55)
                rng = random.randint(70, 100)
                dp_override = True
                rng_override = True
            else:
                # Already tip or base; widen range moderately
                rng = _clamp(rng, 40, 90)
                rng_override = True

        # Scale base speed relative to the stroke range to maintain a
        # consistent perceived pace.  Larger strokes receive proportionally
        # higher speeds and vice versa.  Use the midpoint of the phase
        # envelope as a reference range.
        rng_ref = (rng_min + rng_max) / 2.0
        # Avoid division by zero; if rng_ref is zero (which shouldn't happen), skip scaling
        if rng_ref > 0:
            # Adjust base speed by the ratio of actual range to reference range
            scaled_sp = base_sp * (rng / rng_ref)
        else:
            scaled_sp = base_sp
        base_sp_scaled = int(round(scaled_sp))
        # Convert to final sp with depth factor only
        sp = _compute_sp_adjusted(base_sp_scaled, dp, rng)

        # Smoothing relative to previous move
        if _LAST_MOVE:
            prev_sp = _LAST_MOVE.get("sp", sp)
            prev_dp = _LAST_MOVE.get("dp", dp)
            prev_rng = _LAST_MOVE.get("rng", rng)
            sp = _clamp(prev_sp + _clamp(sp - prev_sp, -MAX_DELTA["sp"], MAX_DELTA["sp"]), 1, 100)
            dp = _clamp(prev_dp + _clamp(dp - prev_dp, -MAX_DELTA["dp"], MAX_DELTA["dp"]), 0, 100)
            rng = _clamp(prev_rng + _clamp(rng - prev_rng, -MAX_DELTA["rng"], MAX_DELTA["rng"]), 0, 100)

        # Enforce envelope after smoothing.  When cues override dp/rng (tip/base/full),
        # do not clamp to the phase envelope – allow the larger/smaller values.  Clamp
        # them only to the absolute 0..100 range.
        sp = _clamp(sp, sp_min, sp_max)
        if not dp_override:
            dp = _clamp(dp, dp_min, dp_max)
        else:
            dp = _clamp(dp, 0, 100)
        if not rng_override:
            rng = _clamp(rng, rng_min, rng_max)
        else:
            rng = _clamp(rng, 0, 100)

        # Hard clamp speed in RECOVERY phase
        if phase_upper == "RECOVERY":
            sp = min(sp, 15)

        # Possibly hold the speed from the previous move to simulate natural cadence.
        # With a higher probability (e.g. 60%), reuse the previous speed with a
        # small variation (±5).  This produces sequences where several moves
        # maintain a similar velocity, helping to mask any gaps between strokes.
        if moves:
            hold_probability = 0.60  # 60% chance to hold speed
            if random.random() < hold_probability:
                prev_sp_val = moves[-1]['sp']
                jitter = random.randint(-5, 5)
                sp = _clamp(prev_sp_val + jitter, sp_min, sp_max)
        # Create a single move dict and append it to the list
        move = {"sp": int(sp), "dp": int(dp), "rng": int(rng), "duration": int(duration)}
        moves.append(move)
        _LAST_MOVE = move

    try:
        _observer_show_debug(phase, cues, moves)
    except Exception:
        pass
    return moves
