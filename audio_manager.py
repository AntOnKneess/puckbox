import os
from pygame import mixer
import pygame._sdl2 as sdl2_audio

class AudioManager:
    def __init__(self):
        self.current_device = None
        # Safe initial startup with default fallback
        self.set_audio_device(None)

    def get_audio_devices(self):
        """Queries physical system hardware for active audio output devices."""
        try:
            if not mixer.get_init():
                mixer.init()
            # capture_devices=False targets speakers/outputs
            return list(sdl2_audio.get_audio_device_names(False))
        except Exception as e:
            print(f"[Audio Manager Error] Cannot read devices: {e}")
            return ["Default Hardware Device"]

    def set_audio_device(self, device_name):
        """Shuts down the mixer engine and spins it back up on a new device target."""
        print(f"\n[Audio Hardware] Switching target output device to: {device_name}")
        
        try:
            mixer.quit()  # Safely flush out old sound pipelines
            
            # Re-initialize with high buffer safety margins to stop ALSA underruns
            if device_name and device_name != "Default Hardware Device":
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192, devicename=device_name)
                self.current_device = device_name
            else:
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
                self.current_device = None
                
            print("[Audio Hardware] Mixer successfully initialized!")
        except Exception as e:
            print(f"[Audio Error] Failed setting output device target: {e}")
            # Fallback configuration to prevent total silence
            mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
            self.current_device = None