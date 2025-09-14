"""
semantic_funscript.py
~~~~~~~~~~~~~~~~~~~~~

This module provides functionality to derive haptic stroke patterns from
narrative text.  It exposes two primary helpers:

* ``extract_semantic_movements`` parses plain text using a set of regular
  expressions.  Each matched pattern expands into a list of ``(pos, duration)``
  tuples where ``pos`` is the target position (0–100, logical scale) and
  ``duration`` is the dwell time at that position in milliseconds.

* ``extract_movements_with_nlp`` uses spaCy to perform part‑of‑speech
  analysis and determine the high‑level intent of each sentence.  It falls
  back on the regular expression matcher when no relevant verb is found.

Both functions ultimately return a list of ``(pos, duration)`` pairs which
may be consumed by a realtime scheduler.  The ``FunscriptGenerator`` class
is provided for convenience; it can persist the generated movements to a
``.funscript`` file compatible with third‑party players.

This file is intentionally standalone to minimise coupling with the Flask
application.  To drive The Handy directly from these movements see the
``play_funscript_actions`` helper in ``app.py`` which consumes the action
sequence and converts it into calls to ``handy.move``.

The semantic dictionaries defined here include both English and Italian
phrases.  Feel free to extend them further to support additional
languages or synonyms; the patterns below are deliberately generous and
case‑insensitive.
"""

from __future__ import annotations

import json
import re
try:
    import spacy  # Attempt to import spaCy.  It may not be present in all environments.
    try:
        # Load the small English model; if unavailable or fails, fall back to regex only.
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = None
except ModuleNotFoundError:
    # spaCy not installed; disable NLP functionality.
    nlp = None


class FunscriptGenerator:
    """Utility to build and save a funscript from an ordered list of actions."""

    def __init__(self, inverted: bool = False, range_: int = 90, min_pos: int = 5, max_pos: int = 95):
        # Whether to invert the logical position (0 → 100) before scaling.
        self.inverted = inverted
        # Percentage of the full stroke the funscript covers.  Default 90%.
        self.range = range_
        # Lower and upper bounds for the mechanical stroke (percent).
        self.min_pos = min_pos
        self.max_pos = max_pos
        # Internal storage for actions.  Each entry is ``{"pos": int, "at": int}``.
        self.actions: list[dict[str, int]] = []
        # Running timestamp in milliseconds when the next action should occur.
        self.time = 0
        # Last logical position added (0–100).
        self.last_pos = 0

    def scale_position(self, pos: float) -> float:
        """Apply inversion and scaling to a logical position (0–100)."""
        if self.inverted:
            pos = 100 - pos
        # Map from logical 0–100 to the configured min/max range.
        return (pos * self.range / 100.0) + self.min_pos

    def add_movement(self, target_pos: float, duration_ms: int) -> None:
        """Append a movement to the script, updating the timestamp and last position."""
        # Compute absolute timestamp by adding the dwell duration.
        self.time += duration_ms
        # Append the action with scaled position.
        self.actions.append({
            "pos": int(round(self.scale_position(target_pos))),
            "at": int(self.time)
        })
        # Track the last logical position for downstream consumers.
        self.last_pos = float(target_pos)

    def to_funscript(self) -> dict:
        return {
            "version": "1.0",
            "inverted": self.inverted,
            "range": self.range,
            "actions": self.actions,
        }

    def save(self, filename: str = "output.funscript") -> None:
        """Write the funscript JSON to disk."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_funscript(), f, indent=2)


# -----------------------------------------------------------------------------
# Semantic dictionaries
#
# The following list contains tuples of (regex pattern, movement sequence).  If
# the pattern matches anywhere in the input text (case‑insensitive), the
# associated sequence of movements is appended.  Patterns are ordered; later
# entries are evaluated even if earlier patterns matched to allow multiple
# triggers per line.
#
# Each movement sequence is a list of (logical position, duration_ms) pairs.
# Logical positions are in the 0–100 space; durations are milliseconds.
# -----------------------------------------------------------------------------

SEMANTIC_MOVEMENT_MAP: list[tuple[str, list[tuple[int, int]]]] = [
    # ---- Desire & anticipation ----
    # Begging for touch or contact
    (r"\bbegging\b.*touch|\bsupplicando\b.*tocco|\bpleading\b.*touch|\basking\b.*touch", [(0, 400), (100, 400)]),
    # Lust, desire, hunger
    (r"\blust\b|\bdesire\b|\bhungry for\b|\bcraving\b|\bbrama\b|\bdesiderio\b|\bbramoso\b|\bvoglia\b|\banelando\b|\byearning\b", [(30, 300), (70, 300)]),
    # Aching & yearning
    (r"\baching\b|\byearning\b|\bcraving\b|\bdesideroso\b|\banelando\b", [(20, 400), (80, 400)]),

    # ---- Breathing & tension ----
    (r"\bbreath(?:es)?\s*quicken\b|\bheavy\s*breathing\b|\brespiro\s*(?:affannoso|rapido)\b|\bpanting\b|\bbreathless\b", [(30, 150), (70, 150), (30, 150)]),
    (r"\bmoaning\b|\bmoan\b|\bgroan\b|\bgasps?\b|\bwhimpers?\b|\bgemiti\b|\bansim[ao]+\b", [(40, 200), (60, 200)]),

    # ---- Physical contact ----
    (r"\bgrabbing\b|\bgrabs\b|\bgripping\b|\bgrip\b|\bholding\b|\bclutching\b|\bafferra(?:re|ndo)?\b|\bstringere\b", [(95, 200), (10, 200)]),
    (r"\btouching\b|\bcaressing\b|\bcaress\b|\bstroke(?:s|ing)?\b|\bpetting\b|\bfondling\b|\btoccare\b|\baccarezz(?:are|ando)\b|\bmassaggiare\b", [(20, 300), (60, 300), (40, 300)]),
    (r"\bteasing\b|\btracing\b|\btickling\b|\bprovocando\b|\bstuzzic(?:are|ando)\b", [(10, 150), (30, 150), (20, 150), (40, 150)]),
    (r"\bsliding\b|\bgliding\b|\bslipping\b|\bscivolando\b|\bscivolare\b", [(0, 300), (100, 300)]),
    (r"\brubbing\b|\bgrinding\b|\bpressing\b|\bstrofinando\b|\bsfregando\b", [(40, 200), (50, 200), (45, 200)]),

    # ---- Intensity & emotion ----
    (r"\bslowly\b|\blow\s+tempo\b|\bgently\b|\bsoftly\b|\blentamente\b|\bdolcemente\b|\bpiano\b|\bdelicatamente\b", [(30, 600), (70, 600)]),
    (r"\bpassionately\b|\bintensely\b|\bfiercely\b|\broughly\b|\bhard\b|\bforcefully\b|\bappassionatamente\b|\bintensamente\b|\bcon\s+forza\b|\bbruscamente\b|\bviolentemente\b", [(10, 150), (100, 150), (0, 150), (100, 150)]),
    (r"\bthrusting\b|\bthrusts\b|\bpounding\b|\bhammering\b|\bspingendo\b|\bpenetrando\b|\bcolpendo\b|\bmartellando\b|\bsbattendo\b", [(0, 100), (100, 100), (0, 100)]),

    # ---- Command & climax ----
    (r"\bcum\b.*me|\bcome\b.*me|\bvieni\b.*(me|dentro)|\bgodi\b.*me|\besplodi\b.*me", [(100, 100), (0, 600), (100, 300)]),
    (r"\blet\s+me\s+feel\b|\bfammi\s+sentire\b|\blasciami\s+sentire\b", [(90, 200), (10, 200), (80, 200)]),

    # ---- Position / Riding ----
    (r"\bsit\s+on\b|\bsit\s+atop\b|\bsederti\s+su\b|\bsiediti\s+sopra\b", [(0, 150), (100, 150), (0, 150)]),
    (r"\bclimb\s+on\b|\bsalire\s+su\b|\bmount\b|\bcavalcare\b", [(0, 150), (100, 150), (0, 150)]),
    (r"\bride\b|\bcavalcare\b", [(0, 150), (100, 150), (0, 150)]),

    # ---- Emotional involvement ----
    (r"\bneed\s+you\b|\bwant\s+you\b|\bvoglio\s+te\b|\bho\s+bisogno\s+di\s+te\b|\bti\s+desidero\b|\bti\s+voglio\b", [(40, 400), (60, 400)]),
    (r"\bcloser\b|\bpiù\s+vicino\b|\bavvicinati\b|\bcloser\s+to\s+me\b", [(100, 300)]),
    (r"\binside\b|\bdentro\b", [(100, 400)]),
]

DEFAULT_FALLBACK: list[tuple[int, int]] = [(30, 500), (70, 500), (30, 500)]


def extract_semantic_movements(text: str) -> list[tuple[int, int]]:
    """Return a flattened list of movements triggered by regex patterns in the text.

    This function iterates through ``SEMANTIC_MOVEMENT_MAP`` in order.  For
    each pattern that matches, the associated sequence is appended to the
    movements list.  If nothing matches the default fallback pattern is
    returned.

    Parameters
    ----------
    text: str
        Input text to scan.

    Returns
    -------
    list of (int, int)
        A list of ``(pos, duration)`` pairs extracted from the text.
    """
    movements: list[tuple[int, int]] = []
    if not text:
        return DEFAULT_FALLBACK.copy()
    for pattern, sequence in SEMANTIC_MOVEMENT_MAP:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                movements.extend(sequence)
        except re.error:
            # Skip invalid patterns silently; this should never happen if
            # patterns are validated at development time.
            continue
    return movements if movements else DEFAULT_FALLBACK.copy()


def determine_intensity(text: str) -> str:
    """Classify a sentence into build/climax/release/neutral categories.

    Words associated with tempo (slowly, gently, etc.) bias towards
    ``build``; those associated with depth or force (deep, thrust, grip)
    bias towards ``climax``; words implying relaxation or aftermath bias
    towards ``release``.  Anything else is ``neutral``.
    """
    t = text.lower()
    if any(w in t for w in ["slow", "slowly", "gentle", "gently", "soft", "softly", "teasing", "piano", "lentamente", "dolce", "delicatamente"]):
        return "build"
    if any(w in t for w in ["deep", "thrust", "thrusting", "grip", "climax", "cum", "vieni", "godi", "profondo", "spinta", "stringere"]):
        return "climax"
    if any(w in t for w in ["relax", "breathe", "collapse", "after", "rilass", "respira", "dopo"]):
        return "release"
    return "neutral"


def intensity_to_pattern(level: str) -> list[tuple[int, int]]:
    """Map an intensity level into a movement pattern."""
    if level == "build":
        return [(30, 500), (70, 500)]
    if level == "climax":
        return [(0, 150), (100, 150), (0, 150)]
    if level == "release":
        return [(50, 600), (40, 600)]
    # Neutral
    return [(30, 300), (70, 300)]


def extract_movements_with_nlp(text: str) -> list[tuple[int, int]]:
    """Use spaCy to derive movements from text, falling back to regex.

    Each sentence is scanned for verbs associated with physical contact; the
    overall intensity of the sentence is classified.  If a target verb is
    present and not negated the corresponding intensity pattern is added to
    the result.  If no verbs match throughout the text, the regex based
    ``extract_semantic_movements`` is used instead.

    Note: spaCy is optional.  If the language model failed to load, this
    function delegates entirely to ``extract_semantic_movements``.
    """
    if not nlp:
        return extract_semantic_movements(text)

    doc = nlp(text)
    movements: list[tuple[int, int]] = []
    found_any = False
    # Define lemmas to look for (English & Italian).  Italian forms are the
    # infinitive or root; spaCy's English model may not lemmatise Italian
    # correctly but these entries allow substring matching on token.lemma_.
    target_lemmas = {"touch", "grab", "stroke", "tease", "slide", "rub", "suck", "kiss", "grip", "penetrate", "ride",
                     "toccare", "afferr", "accarezz", "stuzzic", "scivol", "strofin", "succhi", "baci", "string", "sping", "cavalca"}
    for sent in doc.sents:
        intent = determine_intensity(sent.text)
        for token in sent:
            # Skip negated verbs (e.g. "don't touch").  spaCy marks negation via
            # children with dep_ == "neg".
            if token.pos_ == "VERB" or token.pos_ == "AUX":
                lemma = token.lemma_.lower()
                # Check for substring to account for Italian stems.
                if any(lemma.startswith(prefix) for prefix in target_lemmas):
                    # Check for negation on the verb
                    negated = any(child.dep_ == "neg" for child in token.children)
                    if negated:
                        continue
                    movements.extend(intensity_to_pattern(intent))
                    found_any = True
    # If nothing matched via NLP, fallback to regex patterns
    if not found_any:
        return extract_semantic_movements(text)
    return movements if movements else extract_semantic_movements(text)


def generate_funscript_from_erotic_text(
    text: str,
    filename: str = "semantic_output.funscript",
    config: dict | None = None,
) -> dict:
    """Top‑level helper to produce a funscript from arbitrary text.

    This helper instantiates a ``FunscriptGenerator`` with optional
    configuration (inverted, range, min, max) and populates it with an
    initial zero‑duration movement followed by all movements extracted from
    the text.  The script is then saved to disk and returned as a dict.

    Parameters
    ----------
    text: str
        The erotic or narrative text to analyse.
    filename: str, optional
        The filename to save the generated funscript to.  Defaults to
        ``semantic_output.funscript``.
    config: dict, optional
        Optional configuration for ``FunscriptGenerator``.  Keys: ``inverted``,
        ``range`` (int), ``min`` (int), ``max`` (int).

    Returns
    -------
    dict
        The generated funscript in dictionary form.
    """
    cfg = config or {}
    fg = FunscriptGenerator(
        inverted=bool(cfg.get("inverted", False)),
        range_=int(cfg.get("range", 90)),
        min_pos=int(cfg.get("min", 5)),
        max_pos=int(cfg.get("max", 95)),
    )
    # Begin with an initial reference point at time zero
    fg.add_movement(0, 0)
    # Derive movements via NLP when possible
    actions = extract_movements_with_nlp(text)
    for pos, duration in actions:
        fg.add_movement(pos, duration)
    # Persist script and return the dict
    fg.save(filename)
    return fg.to_funscript()
