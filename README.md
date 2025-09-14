# StrokeGPT v1.5

StrokeGPT is an interactive web application that connects a local LLM (e.g., LM Studio, Text-Gen-WebUI) with The Handy device (or compatible haptic hardware), ElevenLabs TTS, and a modular phase/command system for interactive sessions.  
It provides:
- Real-time text + haptic synchronization
- Phase-based control (Warm-up, Active, Recovery)
- Manual and automated modes
- Media (images, videos, gifs, audio, bot selfies) management
- Explicit JSON commands for developers (“Danger Zone”)
- A local web interface to control everything

---

## **1. Prerequisites**

### Software
- **Python 3.10+**  
  [Download Python](https://www.python.org/downloads/), add it to PATH.

- **pip** (comes with Python)

- **Git** (to clone and manage repo)
  ```bash
  https://git-scm.com/downloads
LM Studio (or Text-Gen-WebUI / OpenAI-compatible endpoint)

Recommended model: Nous-Hermes-2-Mistral-7B-DPO

Start LM Studio with OpenAI-compatible endpoint enabled:

bash
Copia codice
http://127.0.0.1:1234/v1/chat/completions
spaCy for natural language parsing:

bash
Copia codice
pip install spacy
python -m spacy download en_core_web_sm
ElevenLabs API Key (optional, for text-to-speech)

Get ElevenLabs key

Add it to .env:

ini
Copia codice
ELEVENLABS_API_KEY=your_api_key_here
2. Installation
Clone the repo and install dependencies:

bash
Copia codice
git clone https://github.com/yourusername/StrokeGPT.git
cd StrokeGPT
pip install -r requirements.txt
Create a .env file or set environment variables:

ini
Copia codice
ELEVENLABS_API_KEY=your_api_key_here
HANDY_KEY=your_handy_device_key
3. Starting the app
Run the local web server:

bash
Copia codice
python app.py
Access via browser: http://127.0.0.1:5000

Device, model, and TTS connections are managed in real time.

4. Phase System
StrokeGPT operates on 3 main phases with explicit rules:

Phase	Speed (sp)	Depth (dp)	Range (rng)	Rules
Warm-up	8–20	40–60	25–45	Light teasing, gentle start
Active	45–85	50–80	40–70	Main stimulation, steady rhythm
Recovery	1–15	35–55	15–35	Stay here until user explicitly says to continue

After climax triggers (e.g., “I came”), system automatically switches to Recovery.

Recovery lock: The system remains in Recovery until user explicitly commands:

“continue”, “resume”, “again”, “go on”, “riprendi”, “continua” → goes to Warm-up or Active

5. Manual Phase Control
Explicit commands available during sessions:

Command	Action
warm up	Switch to Warm-up phase
active	Switch to Active phase
recovery	Switch to Recovery phase
next phase	Cycle: Warm-up → Active → Recovery → Warm-up
stop	Immediate stop (Danger Zone)
reset	Reset all phases & settings (Danger Zone)

6. Speed, Depth & Range Control
You can issue natural language commands to adjust stimulation:

Command examples	Effect
slow down, gentle, take it slow	Decrease speed (sp 10–25)
faster, speed up, go harder	Increase speed (sp 55–85)
full stroke, all the way	dp=50, rng=100
just the tip, tip only	dp=15, rng=15
base only	dp=85, rng=15
medium speed, steady	sp=40–55, dp=50, rng=50
stop	sp=0 (halts movement)

7. Automatic Modes
Mode	Description
Auto Mode	Generates random moves in-phase automatically
Milking Mode	Build-up patterns toward climax
Edging Mode	Edge control with build-up → tease → hold → recovery cycle

8. JSON Command Schema
For developer control (“Danger Zone”), raw JSON commands can be sent:

json
Copia codice
{
  "chat": "*keeps a steady rhythm* Right there.",
  "move": { "sp": 60, "dp": 55, "rng": 55 },
  "new_mood": "Focused"
}
chat: Text response from model

move: Motion parameters (speed, depth, range)

new_mood: Optional emotional tag

9. Climax & Recovery Lock
Phrases like:
I came, I have finished, ho finito, sono venuto →
System immediately switches to Recovery phase with:

sp ≤ 15

dp = 35–55

rng = 15–35

Recovery lock stays until explicit resume command:

continue, resume, go on, ready, riprendi, ancora → resumes Warm-up/Active

10. Media File Organization
All static media lives under static/:

php
Copia codice
static/
 ├── updates/
 │    ├── audio/        # Custom audio files (.mp3, .wav)
 │    ├── gif/          # GIF animations
 │    ├── video/        # Video files (.mp4, .webm)
 │    ├── immagini/     # Static images
 │    └── botselfie/    # Bot avatars / selfies
Files are served automatically via Flask’s static/ route.

Media can be referenced in the UI or scripts.

11. Danger Zone Commands
Command	Description
stop	Immediate stop of device & loops
reset	Full reset of phases and automations
raw {json}	Send raw JSON directly to Handy API
loop on/off	Toggle automated looping modes

Warning: These bypass normal phase rules. Use with caution.

12. LLM Parameters
Configurable in settings_manager.py or UI:

temperature → creativity (default 0.9)

top_p → nucleus sampling (default 0.95)

max_tokens → max length of response

persona_desc → system prompt / role description

13. Terminal Commands
Command	Action
python app.py	Start local server
Ctrl+C	Stop the server
pip install -r requirements.txt	Install dependencies
git pull	Update local repo

14. Phase Cycle Example
Warm-up (gentle start)

Active (main stimulation)

Climax triggers (“I came”) → Switch to Recovery

Recovery lock stays until user says:

“continue” → Warm-up

“active” → Active phase directly

15. Media & Botselfie Usage
Place files into correct subfolders under static/updates/

Reference them in index.html or UI panels

Handy can be synchronized with audio/video cues

16. Contributing
Fork the repo, create a feature branch, open PRs

Document all new modes & commands in README

Never commit .env or real API keys

17. License
MIT License – free to use with attribution.

18. Quick Command Reference
Phrase	Effect
“warm up”	Warm-up phase
“active”	Active phase
“recovery”	Recovery phase
“next phase”	Cycle phases sequentially
“faster”	Increase speed
“slow down”	Decrease speed
“full stroke”	dp=50, rng=100
“just the tip”	dp=15, rng=15
“base only”	dp=85, rng=15
“stop”	Stop device (Danger Zone)
“reset”	Reset everything
