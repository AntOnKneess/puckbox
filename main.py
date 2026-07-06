import os
import json
from server import create_app
from nfc_reader import NFCReader
from audio_manager import AudioManager  # Import our new manager class

MAPPING_FILE = 'mappings.json'

# Fire up the isolated audio subsystem
audio_manager = AudioManager()

# Load or create tag configurations
if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, 'r') as f:
        tag_mappings = json.load(f)
else:
    tag_mappings = {}

def save_mappings():
    with open(MAPPING_FILE, 'w') as f:
        json.dump(tag_mappings, f, indent=4)

# Create Flask app and cleanly pass the audio manager methods
app = create_app(
    tag_mappings=tag_mappings, 
    save_mappings_func=save_mappings,
    get_devices_func=audio_manager.get_audio_devices,
    set_device_func=audio_manager.set_audio_device
)

nfc_subsystem = NFCReader(app.config, tag_mappings)
nfc_subsystem.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)