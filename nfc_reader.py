import os
import time
import threading
from pygame import mixer

# Flag to track if we are using real hardware or a mock
USING_MOCK_NFC = False

try:
    # First layer: Try importing the library
    from mfrc522 import SimpleMFRC522
    
    # Second layer: Test instantiate it. 
    # If RPi.GPIO throws a RuntimeError on your PC, it gets caught here.
    _test_reader = SimpleMFRC522()
    del _test_reader
    
except (ImportError, RuntimeError, Exception) as e:
    print(f"\n[NFC] Cannot initialize Raspberry Pi hardware ({type(e).__name__}).")
    print("      Switching to MOCK terminal mode for testing.")
    USING_MOCK_NFC = True

class NFCReader:
    def __init__(self, app_config, tag_mappings):
        self.config = app_config
        self.tag_mappings = tag_mappings
        self.running = False

    def start(self):
        self.running = True
        if USING_MOCK_NFC:
            threading.Thread(target=self._mock_nfc_worker, daemon=True).start()
        else:
            threading.Thread(target=self._hardware_nfc_worker, daemon=True).start()

    def _play_audio(self, tag_str):
        if tag_str in self.tag_mappings:
            mp3_file = self.tag_mappings[tag_str]
            file_path = os.path.join(self.config['UPLOAD_FOLDER'], mp3_file)
            
            if os.path.exists(file_path):
                print(f"\n[NFC] Playing locally: {mp3_file}")
                mixer.music.load(file_path)
                mixer.music.play()
            else:
                print(f"\n[NFC] Mapped file not found: {file_path}")
        else:
            print(f"\n[NFC] Unmapped Tag Detected: {tag_str}")

    def _hardware_nfc_worker(self):
        # Re-initialize securely inside the worker context
        reader = SimpleMFRC522()
        last_tag = None
        last_time = 0
        
        print("[NFC] Hardware Reader active...")
        while self.running:
            try:
                tag_id, _ = reader.read_no_block()
                if tag_id:
                    current_time = time.time()
                    if tag_id != last_tag or (current_time - last_time > 3):
                        tag_str = str(tag_id)
                        print(f"\n[NFC] Detected Tag: {tag_str}")
                        self._play_audio(tag_str)
                        
                        last_tag = tag_id
                        last_time = current_time
                else:
                    last_tag = None
                    
                time.sleep(0.2)
            except Exception as e:
                print(f"[NFC Error]: {e}")
                time.sleep(1)

    def _mock_nfc_worker(self):
        """Simulates tag scans via terminal input for non-RPi testing."""
        print("[NFC] Mock Mode Active. Type a Tag ID in the terminal and press Enter to simulate a scan.")
        while self.running:
            try:
                mock_input = input().strip()
                if mock_input:
                    print(f"\n[NFC Mock] Simulated scan for Tag ID: {mock_input}")
                    self._play_audio(mock_input)
            except Exception as e:
                print(f"[NFC Mock Error]: {e}")
            time.sleep(0.5)