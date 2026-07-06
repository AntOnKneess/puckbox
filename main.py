import os
import json
from pygame import mixer
from server import create_app
from nfc_reader import NFCReader

MAPPING_FILE = 'mappings.json'

# Initialize local audio mixer
mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)

# Load or create mappings
if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, 'r') as f:
        tag_mappings = json.load(f)
else:
    tag_mappings = {}

def save_mappings():
    with open(MAPPING_FILE, 'w') as f:
        json.dump(tag_mappings, f, indent=4)

# Instantiate Flask app
app = create_app(tag_mappings, save_mappings)

# Start the NFC Subsystem (automatically handles mock vs hardware)
nfc_subsystem = NFCReader(app.config, tag_mappings)
nfc_subsystem.start()

if __name__ == '__main__':
    # Flask is set to debug=False to avoid running the background thread twice 
    # (Flask's reloader triggers thread duplication)
    app.run(host='0.0.0.0', port=5000, debug=False)