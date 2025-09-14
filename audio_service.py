from collections import deque
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings

class AudioService:
    def __init__(self):
        self.api_key = ""
        self.voice_id = ""
        self.is_on = False
        self.client = None
        self.available_voices = {}
        self.audio_output_queue = deque()

    def set_api_key(self, api_key):
        self.api_key = api_key
        try:
            self.client = ElevenLabs(api_key=self.api_key)
            return True
        except Exception as e:
            print(f"🔥 Failed to initialize ElevenLabs client: {e}")
            self.client = None
            return False

    def fetch_available_voices(self):
        if not self.client:
            return {"status": "error", "message": "API key not set or invalid."}
        
        try:
            voices_list = self.client.voices.get_all()
            self.available_voices = {voice.name: voice.voice_id for voice in voices_list.voices}
            print(f"✅ ElevenLabs key set. Found {len(self.available_voices)} voices.")
            return {"status": "success", "voices": self.available_voices}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't fetch voices: {e}"}

    def configure_voice(self, voice_id, enabled):
        if not voice_id and enabled:
            return False, "A voice must be selected to enable audio."
            
        self.voice_id = voice_id
        self.is_on = bool(enabled)
        
        status_message = "ON" if self.is_on else "OFF"
        if voice_id:
            voice_name = next((name for name, v_id in self.available_voices.items() if v_id == voice_id), "Unknown")
            print(f"🎤 Voice set to '{voice_name}'. Audio is now {status_message}.")
        else:
            print(f"🎤 Audio is now {status_message}.")
        return True, "Settings updated."


    def generate_audio_for_text(self, text_to_speak):
        if not self.is_on or not self.api_key or not self.voice_id or not self.client:
            return
            
        if not text_to_speak or text_to_speak.strip().startswith(("(", "[")):
            return

        try:
            print(f"🎙️ Generating audio: '{text_to_speak[:50]}...'")
            
            audio_stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text_to_speak,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(stability=0.4, similarity_boost=0.7, style=0.1, use_speaker_boost=True)
            )

            audio_bytes_data = b"".join(audio_stream)
            self.audio_output_queue.append(audio_bytes_data)
            print("✅ Audio ready.")

        except Exception as e:
            print(f"🔥 Oops, ElevenLabs problem: {e}")
            
    def get_next_audio_chunk(self):
        if self.audio_output_queue:
            return self.audio_output_queue.popleft()
        return None