import os
import time
import threading
from pygame import mixer

# Global hardware variables
USING_MOCK_NFC = False
pn532_hardware = None

try:
    import board
    import busio
    from adafruit_pn532.i2c import PN532_I2C
    
    # Initialize the I2C bus cleanly once
    i2c = busio.I2C(board.SCL, board.SDA)
    pn532_hardware = PN532_I2C(i2c, debug=False)
    
    # Verify firmware version to ensure communication works
    pn532_hardware.firmware_version
    print("[NFC] PN532 Hardware successfully initialized!")
    
except (ImportError, RuntimeError, ValueError, AttributeError) as e:
    print(f"\n[NFC] Cannot initialize Raspberry Pi PN532 hardware ({type(e).__name__}): {e}")
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
        # Check if the web app is actively trying to capture/register a tag
        scan_state = self.config.get('SCAN_STATE')
        if scan_state and scan_state.get('is_scanning'):
            print(f"\n[NFC Capture] Intercepted Tag ID for registration: {tag_str}")
            scan_state['captured_tag'] = tag_str
            # Optional: You could play a short "beep" sound here to confirm the scan
            return 

        # Otherwise, proceed with normal playback behavior
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
        # Use the globally verified hardware object
        global pn532_hardware
        
        # Configure PN532 to communicate with MiFare cards
        pn532_hardware.SAM_configuration()
        
        last_tag = None
        last_time = 0
        
        print("[NFC] PN532 Hardware Reader active...")
        while self.running:
            try:
                # Read passive tag
                uid = pn532_hardware.read_passive_target(timeout=0.2)
                
                if uid is not None:
                    tag_id = "".join([f"{x:02X}" for x in uid])
                    current_time = time.time()
                    
                    if tag_id != last_tag or (current_time - last_time > 3):
                        print(f"\n[NFC] Detected Tag: {tag_id}")
                        self._play_audio(tag_id)
                        
                        last_tag = tag_id
                        last_time = current_time
                else:
                    last_tag = None
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"[NFC Error]: {e}")
                time.sleep(1)

    def _mock_nfc_worker(self):
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