import os
import subprocess  # <--- Added for system volume control
from pygame import mixer
import pygame._sdl2 as sdl2_audio

class AudioManager:
    def __init__(self):
        self.current_device = None
        self.target_volume = 0.7
        self.set_audio_device(None)

    def get_audio_devices(self):
        try:
            if not mixer.get_init():
                mixer.init()
            return list(sdl2_audio.get_audio_device_names(False))
        except Exception as e:
            print(f"[Audio Manager Error] Cannot read devices: {e}")
            return ["Default Hardware Device"]

    def set_audio_device(self, device_name):
        print(f"\n[Audio Hardware] Switching target output device to: {device_name}")
        
        # --- NEW: SYSTEM-LEVEL AUX MIXER BOOST ---
        # If targeting default analog/headphones on Linux, force ALSA to 100% volume capacity
        try:
            # Common sound card controls: "PCM", "Headphone", "Audio Out", or "Master"
            for control in ["PCM", "Headphone", "Master"]:
                subprocess.run(["amixer", "set", control, "100%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Some Pi systems allow hardware boosting (e.g., 400 parameter steps over standard)
                subprocess.run(["amixer", "set", control, "--", "400+占"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass # Gracefully skip if running on non-Linux architectures
        # ----------------------------------------

        try:
            mixer.quit()
            
            if device_name and device_name != "Default Hardware Device":
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192, devicename=device_name)
                self.current_device = device_name
            else:
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
                self.current_device = None
            
            mixer.music.set_volume(self.target_volume)
            print(f"[Audio Hardware] Mixer initialized! Volume set to {int(self.target_volume * 100)}%")
        except Exception as e:
            print(f"[Audio Error] Failed setting output device target: {e}")
            mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
            mixer.music.set_volume(self.target_volume)
            self.current_device = None

    def set_volume(self, volume_percent):
        self.target_volume = max(0.0, min(1.0, volume_percent / 100.0))
        if mixer.get_init():
            mixer.music.set_volume(self.target_volume)

    def get_volume(self):
        if mixer.get_init():
            return int(mixer.music.get_volume() * 100)
        return int(self.target_volume * 100)