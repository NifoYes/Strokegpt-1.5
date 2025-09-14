import json
from pathlib import Path
import threading

class SettingsManager:
    def __init__(self, settings_file_path):
        self.file_path = Path(settings_file_path)
        self._save_lock = threading.Lock()

        # Default values
        self.handy_key = ""
        self.ai_name = "BOT" # New field
        self.persona_desc = "An energetic and passionate girlfriend"
        self.profile_picture_b64 = ""
        self.patterns = []
        self.milking_patterns = []
        self.rules = []
        self.user_profile = self._get_default_profile()
        self.session_liked_patterns = []
        self.elevenlabs_api_key = "api key here"
        self.elevenlabs_voice_id = "voice id here"
        self.min_depth = 5
        self.max_depth = 100
        self.min_speed = 10
        self.max_speed = 80
        self.auto_min_time = 4.0
        self.auto_max_time = 7.0
        self.milking_min_time = 2.5
        self.milking_max_time = 4.5
        self.edging_min_time = 5.0
        self.edging_max_time = 8.0

    def _get_default_profile(self):
        return {"name": "Unknown", "likes": [], "dislikes": [], "key_memories": []}

    def load(self):
        if not self.file_path.exists():
            print("ℹ️ No settings file found, creating one with default values.")
            self.save()
            return

        try:
            data = json.loads(self.file_path.read_text())
            self.handy_key = data.get("handy_key", "")
            self.ai_name = data.get("ai_name", "BOT") # Load name
            self.persona_desc = data.get("persona_desc", "An energetic and passionate girlfriend")
            self.profile_picture_b64 = data.get("profile_picture_b64", "")
            self.patterns = data.get("patterns", [])
            self.milking_patterns = data.get("milking_patterns", [])
            self.rules = data.get("rules", [])
            self.user_profile = data.get("user_profile", self._get_default_profile())
            self.elevenlabs_api_key = data.get("elevenlabs_api_key", "")
            self.elevenlabs_voice_id = data.get("elevenlabs_voice_id", "")
            self.min_depth = data.get("min_depth", 5)
            self.max_depth = data.get("max_depth", 100)
            self.min_speed = data.get("min_speed", 10)
            self.max_speed = data.get("max_speed", 80)
            self.auto_min_time = data.get("auto_min_time", 4.0)
            self.auto_max_time = data.get("auto_max_time", 7.0)
            self.milking_min_time = data.get("milking_min_time", 2.5)
            self.milking_max_time = data.get("milking_max_time", 4.5)
            self.edging_min_time = data.get("edging_min_time", 5.0)
            self.edging_max_time = data.get("edging_max_time", 8.0)
            print("✅ Loaded settings from my_settings.json")
        except Exception as e:
            print(f"⚠️ Couldn't read settings file, using defaults. Error: {e}")

    def save(self, llm_service=None, chat_history_to_save=None):
        with self._save_lock:
            if llm_service and chat_history_to_save:
                self.user_profile = llm_service.consolidate_user_profile(
                    list(chat_history_to_save), self.user_profile
                )
            
            if self.session_liked_patterns:
                print(f"🧠 Saving {len(self.session_liked_patterns)} liked patterns...")
                for new_pattern in self.session_liked_patterns:
                    if not any(p["name"] == new_pattern["name"] for p in self.patterns):
                        self.patterns.append(new_pattern)
                self.session_liked_patterns.clear()

            settings_dict = {
                "handy_key": self.handy_key,
                "ai_name": self.ai_name, # Save name
                "persona_desc": self.persona_desc,
                "profile_picture_b64": self.profile_picture_b64,
                "elevenlabs_api_key": self.elevenlabs_api_key, "elevenlabs_voice_id": self.elevenlabs_voice_id,
                "patterns": self.patterns, "milking_patterns": self.milking_patterns,
                "rules": self.rules, "user_profile": self.user_profile,
                "min_depth": self.min_depth, "max_depth": self.max_depth,
                "min_speed": self.min_speed, "max_speed": self.max_speed,
                "auto_min_time": self.auto_min_time, "auto_max_time": self.auto_max_time,
                "milking_min_time": self.milking_min_time, "milking_max_time": self.milking_max_time,
                "edging_min_time": self.edging_min_time, "edging_max_time": self.edging_max_time,
            }
            self.file_path.write_text(json.dumps(settings_dict, indent=2))