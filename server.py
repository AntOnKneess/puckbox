import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify

# Global variables for capturing tag scans
scan_state = {
    "is_scanning": False,
    "captured_tag": None
}

def create_app(tag_mappings, save_mappings_func):
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'static/audio'
    
    # Expose the scan state to the app context so the NFC thread can see it
    app.config['SCAN_STATE'] = scan_state

    @app.route('/')
    def index():
        return redirect(url_for('upload_file'))

    @app.route('/upload', methods=['GET', 'POST'])
    def upload_file():
        if request.method == 'POST':
            if 'file' not in request.files:
                return redirect(url_for('upload_file'))
            file = request.files['file']
            if file.filename == '':
                return redirect(url_for('upload_file'))
            
            if file and file.filename.endswith('.mp3'):
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return redirect(url_for('upload_file'))
        
        files = os.listdir(app.config['UPLOAD_FOLDER']) if os.path.exists(app.config['UPLOAD_FOLDER']) else []
        return render_template('upload.html', mappings=tag_mappings, files=files)

    @app.route('/map', methods=['POST'])
    def map_tag():
        tag_id = request.form.get('tag_id').strip()
        filename = request.form.get('filename')
        if tag_id and filename:
            tag_mappings[tag_id] = filename
            save_mappings_func()
        return redirect(url_for('upload_file'))

    # --- NEW API ENDPOINTS FOR CAPTURING ---

    @app.route('/api/start-scan', methods=['POST'])
    def start_scan():
        """Triggers the system to intercept the next physical or mock scan."""
        scan_state['is_scanning'] = True
        scan_state['captured_tag'] = None
        return jsonify({"status": "scanning"})

    @app.route('/api/check-scan', methods=['GET'])
    def check_scan():
        """Polled by the frontend to see if a tag has been captured."""
        if scan_state['captured_tag']:
            tag = scan_state['captured_tag']
            # Reset state now that it's consumed
            scan_state['is_scanning'] = False
            scan_state['captured_tag'] = None
            return jsonify({"status": "found", "tag_id": tag})
        
        return jsonify({"status": "waiting"})

    return app