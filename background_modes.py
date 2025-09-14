import threading
import time
import script_generator as _sg
import random


loop_thread = None

def _observer_push_chat(response):
    try:
        text = ''
        if isinstance(response, dict):
            text = response.get('chat') or response.get('text') or response.get('raw') or ''
        _sg._observer_note_text(text)
    except Exception:
        pass

last_moves = []
class AutoModeThread(threading.Thread):
    def __init__(self, mode_func, initial_message, services, callbacks, mode_name="auto"):
        super().__init__()
        self.name = mode_name
        self._mode_func = mode_func
        self._initial_message = initial_message
        self._services = services
        self._callbacks = callbacks
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        message_callback = self._callbacks.get('send_message')
        handy_controller = self._services.get('handy')
        
        if message_callback:
            message_callback(self._initial_message)
        time.sleep(2)

        try:
            self._mode_func(self._stop_event, self._services, self._callbacks)
        except Exception as e:
            print(f"Auto mode crashed: {e}")
        finally:
            if handy_controller:
                handy_controller.stop()
            
            stop_callback = self._callbacks.get('on_stop')
            if stop_callback:
                stop_callback()

            if message_callback:
                message_callback("Okay, you're in control now.")

    def stop(self):
        self._stop_event.set()

def _check_for_user_message(queue):
    if queue:
        try: return queue.popleft()
        except IndexError: pass
    return None

def auto_mode_logic(stop_event, services, callbacks):
    """
    Autonomous mode logic.  This routine periodically asks the language model for a response
    while generating random stroking parameters.  No explicit instructions about
    "Automode" are sent to the model; instead, any pending user message is
    forwarded directly.  When the model returns a chat response, it is sent to
    the user interface.  Speed, depth and range are randomly chosen within
    reasonable bounds to keep the experience varied.
    """
    llm_service, handy_controller = services['llm'], services['handy']
    get_context = callbacks['get_context']
    send_message = callbacks['send_message']
    get_timings = callbacks['get_timings']
    message_queue = callbacks['message_queue']

    while not stop_event.is_set():
        auto_min, auto_max = get_timings('auto')
        context = get_context()
        # Allow the model to respond with its own persona; do not force a mood
        user_message = _check_for_user_message(message_queue)
        chat = []
        if user_message:
            # Forward the user message directly to the model
            chat.append({"role": "user", "content": user_message})
        
        # Ask the model for a chat-only response; ignore move instructions from the model
        try:
            response = llm_service.get_chat_response(chat, context, temperature=1.0)
        except Exception:
            response = None
        
        # Send any returned chat to the UI
        if response and isinstance(response.get("chat"), str):
            chat_text = response.get("chat").strip()
            if chat_text:
                send_message(chat_text)
        
        
        # Start loop for moves if present
        if response and isinstance(response.get("moves"), list):
            _observer_push_chat(response)
            from threading import Thread
            last_moves = response["moves"]
            if loop_thread and loop_thread.is_alive():
                stop_event.set()
            stop_event.clear()
            loop_thread = Thread(target=loop_moves_randomly, args=(last_moves, handy_controller, stop_event))
            loop_thread.daemon = True
            loop_thread.start()
        elif response and isinstance(response.get("move"), dict):
            _observer_push_chat(response)
            try:
                handy_controller.move(response["move"]["sp"], response["move"]["dp"], response["move"]["rng"])
            except Exception:
                pass

        # Generate a random stroking move.  Without explicit instructions from
        # the model, choose values within typical mid-range bounds.
        try:
            sp = random.randint(20, 80)
            dp = random.randint(30, 70)
            rng = random.randint(20, 50)
            handy_controller.move(sp, dp, rng)
        except Exception:
            pass
        time.sleep(random.uniform(auto_min, auto_max))

def milking_mode_logic(stop_event, services, callbacks):
    """
    Milking mode logic.  This routine goes through a series of strokes intended to
    build intensity towards climax.  It forwards any user feedback directly to
    the language model and otherwise allows the persona to speak freely.  At
    each step, random stroking parameters are chosen.  The model's response is
    sent to the user interface without instructing it about 'milking' or
    orgasmic goals.
    """
    llm_service, handy_controller = services['llm'], services['handy']
    get_context = callbacks['get_context']
    send_message = callbacks['send_message']
    get_timings = callbacks['get_timings']
    message_queue = callbacks['message_queue']

    # Define how many strokes/moves to perform in this milking session
    for _ in range(random.randint(6, 9)):
        if stop_event.is_set():
            break
        milking_min, milking_max = get_timings('milking')
        context = get_context()
        # Set a mood hint for the model but avoid forcing instructions
        context['current_mood'] = "Dominant"
        # Prepare chat input: include any pending user feedback
        user_message = _check_for_user_message(message_queue)
        chat = []
        if user_message:
            chat.append({"role": "user", "content": user_message})
        # Query the model for a chat-only response
        try:
            response = llm_service.get_chat_response(chat, context, temperature=1.0)
        except Exception:
            response = None
        # Send the model's chat reply to the UI
        if response and isinstance(response.get("chat"), str):
            chat_text = response.get("chat").strip()
            if chat_text:
                send_message(chat_text)
        # Generate a random, high-intensity move within broader bounds for milking
        try:
            sp = random.randint(40, 90)
            dp = random.randint(50, 85)
            rng = random.randint(30, 60)
            handy_controller.move(sp, dp, rng)
        except Exception:
            pass
        time.sleep(random.uniform(milking_min, milking_max))

    # After completing the milking session, send a closing statement if not interrupted
    if not stop_event.is_set():
        send_message("That's it... give it all to me. Don't hold back.")
        time.sleep(4)

def edging_mode_logic(stop_event, services, callbacks):
    llm_service, handy_controller = services['llm'], services['handy']
    get_context, send_message, get_timings, update_mood = callbacks['get_context'], callbacks['send_message'], callbacks['get_timings'], callbacks['update_mood']
    user_signal_event = callbacks['user_signal_event']
    message_queue = callbacks['message_queue']
    edge_count = 0

    states = ["BUILD_UP", "TEASE", "HOLD", "RECOVERY"]
    current_state = "BUILD_UP"

    while not stop_event.is_set():
        edging_min, edging_max = get_timings('edging')
        context = get_context()
        context['edge_count'] = edge_count
        prompt = ""
        
        user_message = _check_for_user_message(message_queue)
        
        if user_signal_event.is_set():
            user_signal_event.clear()
            edge_count += 1
            context['edge_count'] = edge_count
            update_mood("Dominant")
            prompt = f"I am on the edge. I have been edged {edge_count} times. You must choose one of three reactions: 1. A hard 'Pull Back'. 2. A 'Hold'. 3. A risky 'Push Over'. Describe what you choose to do and provide the move."
            current_state = "PULL_BACK"
        else:
            prompts = {
                "BUILD_UP": "Edging mode, phase: Build-up. Your goal is to slowly build my arousal. Invent a slow to medium intensity move.",
                "TEASE": "Edging mode, phase: Tease. Invent a short, fast, shallow, or otherwise teasing move to keep me guessing.",
                "HOLD": "Edging mode, phase: Hold. Maintain a medium, constant intensity. Don't go too fast or too slow. Be steady.",
                "RECOVERY": "Edging mode, phase: Recovery. Stimulation should be very low. Invent a very slow and gentle move.",
            }
            moods = {"BUILD_UP": "Seductive", "TEASE": "Playful", "HOLD": "Confident", "RECOVERY": "Loving"}
            if current_state not in moods: current_state = "BUILD_UP"
            update_mood(moods[current_state])
            prompt = prompts[current_state]

            if user_message:
                prompt += f"\n\n**USER MESSAGE TO CONSIDER:** \"{user_message}\"\n\n**INSTRUCTION:** Analyze this message. Decide if you should alter your pattern or state in response to it. Then, describe your action and provide the next `move`."

        response = llm_service.get_chat_response([{"role": "user", "content": prompt}], context, temperature=1.1)
        if not response or not response.get("move"):
            time.sleep(1); continue
        
        if chat_text := response.get("chat"): send_message(chat_text)
        if move_data := response.get("move"):
            _observer_push_chat(response)
            handy_controller.move(move_data.get("sp"), move_data.get("dp"), move_data.get("rng"))

        if current_state != "PULL_BACK":
            current_state = random.choice(states)
        else:
            current_state = "RECOVERY"

        time.sleep(random.uniform(edging_min, edging_max))

    if not stop_event.is_set():
        send_message(f"You did so well, holding it in for {edge_count} edges...")
        update_mood("Afterglow")

# --- CUSTOM PATTERN MODES ---
def _step_move(stop_event, handy_controller, sp, dp, rng, dur):
    """Helper to move then wait dur seconds, interruptible."""
    try:
        handy_controller.move(int(sp), int(dp), int(rng))
    except Exception as e:
        print(f"[PATTERN] move error: {e}")
    # interruptible sleep
    t_end = time.time() + float(dur)
    while not stop_event.is_set() and time.time() < t_end:
        time.sleep(0.05)

def waves_mode_logic(stop_event, services, callbacks):
    """
    Ondate morbide: depth sale-scende 20↔80, range ~50, speed ~35-55.
    Signature compatibile con AutoModeThread.
    """
    send_message = callbacks.get('send_message')
    update_mood = callbacks.get('update_mood')
    handy_controller = services['handy']
    if send_message: send_message("Ok, vado a onde morbide…")
    if update_mood: update_mood("Playful")

    centers = [20,35,50,65,80,65,50,35]  # oscillazione
    while not stop_event.is_set():
        for dp in centers:
            sp = 35 + (dp % 20)  # piccole variazioni
            _step_move(stop_event, handy_controller, sp, dp, 50, 0.8)
            if stop_event.is_set(): break

def pulse_mode_logic(stop_event, services, callbacks):
    """Impulsi: range pulsa 20↔60, depth 55, speed 55."""
    send_message = callbacks.get('send_message')
    update_mood = callbacks.get('update_mood')
    handy_controller = services['handy']
    if send_message: send_message("Arrivano gli impulsi…")
    if update_mood: update_mood("Focused")

    ranges = [20,40,60,40]
    while not stop_event.is_set():
        for rng in ranges:
            _step_move(stop_event, handy_controller, 55, 55, rng, 0.5)
            if stop_event.is_set(): break

def stairs_mode_logic(stop_event, services, callbacks):
    """Scale: salgo a gradini 30→90 e scendo, range medio 40, speed 30→45."""
    send_message = callbacks.get('send_message')
    update_mood = callbacks.get('update_mood')
    handy_controller = services['handy']
    if send_message: send_message("Salgo a gradini… e poi riscendo.")
    if update_mood: update_mood("Teasing")

    up = [30,45,60,75,90]
    down = [75,60,45]
    seq = up + down
    while not stop_event.is_set():
        for i, dp in enumerate(seq):
            sp = 30 + i*3 if i < len(up) else 35
            _step_move(stop_event, handy_controller, sp, dp, 40, 1.2)
            if stop_event.is_set(): break

def teasehold_mode_logic(stop_event, services, callbacks):
    """Tease & Hold: salgo lentamente fino in punta, tengo, poi rilascio."""
    send_message = callbacks.get('send_message')
    update_mood = callbacks.get('update_mood')
    handy_controller = services['handy']
    if send_message: send_message("Ti porto su piano… e ti tengo lì.")
    if update_mood: update_mood("Seductive")

    # salita lenta
    for dp in range(40, 90, 5):
        if stop_event.is_set(): break
        _step_move(stop_event, handy_controller, 25, dp, 20, 0.6)
    # hold
    hold_time = 6.0
    t_end = time.time() + hold_time
    while not stop_event.is_set() and time.time() < t_end:
        _step_move(stop_event, handy_controller, 20, 88, 15, 0.6)
    # discesa
    for dp in range(85, 45, -5):
        if stop_event.is_set(): break
        _step_move(stop_event, handy_controller, 22, dp, 25, 0.5)



def post_orgasm_mode_logic(stop_event, services, callbacks):
    # Slow massage after orgasm: depth 100, range 100, speed 1-5% changing every 5s.
    handy_controller = services['handy']
    send_message = callbacks.get('send_message') or (lambda *a, **k: None)

    # One-time intro (non-spammy)
    try:
        send_message("Post-Orgasm: massaggio lento e costante. Rilassati.")
    except Exception:
        pass

    # Loop until stopped
    while not stop_event.is_set():
        sp = max(1, min(5, int(__import__('random').randint(1, 5))))
        try:
            handy_controller.move(sp, 100, 100)
        except Exception:
            pass
        # Sleep 5s but interruptible
        for _ in range(50):
            if stop_event.is_set():
                break
            time.sleep(0.1)

def loop_moves_randomly(moves, handy, stop_event):
    import random, time
    if not moves:
        return
    while not stop_event.is_set():
        for move in moves:
            if stop_event.is_set():
                break
            try:
                handy.move(move.get("sp", 10), move.get("dp", 50), move.get("rng", 30))
            except Exception:
                continue
            time.sleep(random.uniform(0.5, 1.2))
        time.sleep(random.uniform(1.5, 3.5))
