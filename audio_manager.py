import os
from pygame import mixer
import pygame._sdl2 as sdl2_audio

class AudioManager:
    def __init__(self):
        self.current_device = None
        self.target_volume = 0.7  # Tracks setting across hardware teardowns (70% standard default)
        # Safe initial startup with default fallback
        self.set_audio_device(None)

    def get_audio_devices(self):
        """Queries physical system hardware for active audio output devices."""
        try:
            if not mixer.get_init():
                mixer.init()
            return list(sdl2_audio.get_audio_device_names(False))
        except Exception as e:
            print(f"[Audio Manager Error] Cannot read devices: {e}")
            return ["Default Hardware Device"]

    def set_audio_device(self, device_name):
        """Shuts down the mixer engine and spins it back up on a new device target."""
        print(f"\n[Audio Hardware] Switching target output device to: {device_name}")
        
        try:
            mixer.quit()  # Safely flush out old sound pipelines
            
            if device_name and device_name != "Default Hardware Device":
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192, devicename=device_name)
                self.current_device = device_name
            else:
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
                self.current_device = None
            
            # Re-apply the system volume tracking setting to the newly chosen device target
            mixer.music.set_volume(self.target_volume)
            print(f"[Audio Hardware] Mixer successfully initialized! Volume set to {int(self.target_volume * 100)}%")
        except Exception as e:
            print(f"[Audio Error] Failed setting output device target: {e}")
            mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
            mixer.music.set_volume(self.target_volume)
            self.current_device = None

    # --- NEW MASTER VOLUME METHODS ---
    
    def set_volume(self, volume_percent):
        """Sets the system volume using an integer parameter from 0 to 100."""
        # Bound incoming signals safely between 0.0 and 1.0 float targets
        self.target_volume = max(0.0, min(1.0, volume_percent / 100.0))
        if mixer.get_init():
            mixer.music.set_volume(self.target_volume)

    def get_volume(self):
        """Returns the current volume configuration mapped as an integer scale from 0 to 100."""
        if mixer.get_init():
            return int(mixer.music.get_volume() * 100)
        return int(self.target_volume * 100)