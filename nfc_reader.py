import os
import time
import threading
from pygame import mixer

# Flag to track if we are using real hardware or a mock
USING_MOCK_NFC = False

try:
    # First layer: Try importing the PN532 libraries
    import board
    import busio
    from adafruit_pn532.i2c import PN532_I2C
    
    # Second layer: Test instantiate it via I2C
    i2c = busio.I2C(board.SCL, board.SDA)
    _test_pn532 = PN532_I2C(i2c, debug=False)
    _test_pn532.get_firmware_version()
    del _test_pn532, i2c
    
except (ImportError, RuntimeError, Exception) as e:
    print(f"\n[NFC] Cannot initialize Raspberry Pi PN532 hardware ({type(e).__name__}).")
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
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        # Initialize I2C and PN532
        i2c = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, debug=False)
        
        # Configure PN532 to communicate with MiFare cards
        pn532.SAM_configuration()
        
        last_tag = None
        last_time = 0
        
        print("[NFC] PN532 Hardware Reader active...")
        while self.running:
            try:
                # Read passive tag
                uid = pn532.read_passive_target(timeout=0.2)
                
                if uid is not None:
                    # Convert byte array UID to a hex string representation
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