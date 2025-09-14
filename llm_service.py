
import json
import requests
import random

def _trim_words(text: str, max_words: int) -> str:
    if not isinstance(text, str) or max_words <= 0:
        return text
    parts = text.split()
    return text if len(parts) <= max_words else " ".join(parts[:max_words])

def _extract_first_json_obj(s: str):
    """Return first top-level {...} object as dict, else None. Handles strings/escapes."""
    if not isinstance(s, str):
        return None
    in_str = False
    esc = False
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        block = s[start:i+1]
                        try:
                            return json.loads(block)
                        except Exception:
                            # keep scanning (there might be another valid block later)
                            start = -1
                            continue
    return None

def _heuristic_move_from_text(t: str):
    """Very light heuristic mapping keywords -> sp/dp/rng (0..100)."""
    tl = (t or "").lower()

    sp = 50
    if any(k in tl for k in ["very slow","molto lento","lentissimo","slowly"]): sp = 20
    elif any(k in tl for k in ["slow","lento","piano","take it slow","rallenta"]): sp = 35
    elif any(k in tl for k in ["medium","medio","steady","costante"]): sp = 50
    elif any(k in tl for k in ["fast","veloce","accelera","svelto","rapido"]): sp = 70
    elif any(k in tl for k in ["very fast","rapidissimo","full speed","massimo"]): sp = 85

    dp = 50  # 0=base, 100=tip
    if any(k in tl for k in ["tip","punta","just the tip","superficiale","shallow"]): dp = 85
    if any(k in tl for k in ["base","a fondo","fond","deep","profondo"]): dp = 25

    rng = 50
    if any(k in tl for k in ["short","mezzi colpi","mezze","half stroke","half strokes","shallow"]): rng = 25
    if any(k in tl for k in ["long","full stroke","colpo lungo","colpi lunghi","a fondo"]): rng = 85

    # Introduce randomness when no explicit keywords matched.  The default
    # values of sp=50, dp=50, rng=50 result in identical fallback moves
    # across turns; to add variety, pick values within reasonably broad bounds.
    if sp == 50 and dp == 50 and rng == 50:
        # Choose a speed between 25 and 75 to avoid monotony
        sp = random.randint(25, 75)
        # Depth anywhere mid‑range, skewing slightly towards the centre
        dp = random.randint(30, 70)
        # Range moderately wide but not full; ensure >15
        rng = random.randint(20, 60)
    return {"sp": int(sp), "dp": int(dp), "rng": int(rng)}

class LLMService:
    def __init__(self, url: str, model: str, provider: str = "lmstudio"):
        self.url = url
        self.model = model
        self._provider = provider or "lmstudio"
        self._last_model_id = model

    def _build_system_prompt(self, context: dict) -> str:
        """Keep pass-through friendly: primarily persona; allow one-turn task directive separately."""
        persona = context.get("persona_desc") or ""
        return persona.strip()

    def get_chat_response(self, chat, context=None):
        context = context or {}
        max_tokens = int(context.get("max_tokens", 1200))
        reply_trim = int(context.get("reply_trim", 0))
        temperature = float(context.get("temperature", 0.9))
        top_p = float(context.get("top_p", 0.95))
        stop = context.get("stop") if isinstance(context.get("stop"), (list,tuple)) else None

        messages = []
        sys_prompt = self._build_system_prompt(context)
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        directive = context.get("task_directive")
        if directive:
            messages.append({"role": "system", "content": directive})
        for m in chat:
            role = m.get("role")
            content = m.get("content")
            if role and content:
                messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop

        r = requests.post(self.url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()

        text = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(text, str):
            text = data.get("text") or json.dumps(data)

        # Try to parse a JSON block if present
        if isinstance(text, str) and "moves" in text:
            try:
                obj = json.loads(text[text.index("{"):text.rindex("}")+1])
                if "moves" in obj:
                    return obj
            except Exception:
                pass

        obj = _extract_first_json_obj(text)
        chat_out = text
        move_out = None
        new_mood = None
        if isinstance(obj, dict):
            if "chat" in obj or "move" in obj or "new_mood" in obj:
                chat_out = obj.get("chat", chat_out)
                move_out = obj.get("move")
                new_mood = obj.get("new_mood")

        # Fallback: infer move from narration if none provided
        if move_out is None and isinstance(chat_out, str):
            move_out = _heuristic_move_from_text(chat_out)

        if reply_trim > 0 and isinstance(chat_out, str):
            chat_out = _trim_words(chat_out, reply_trim)

        return {"chat": chat_out, "move": move_out, "new_mood": new_mood}

    def name_this_move(self, sp: int, dp: int, mood: str = None) -> str:
        mood = (mood or "Neutral").title()
        return f"{mood}-SP{int(sp)}-DP{int(dp)}"
