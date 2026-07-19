import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from bluetooth_manager import BluetoothManager

scan_state = {
    "is_scanning": False,
    "captured_tag": None
}

# --- UPDATE: Added get_volume_func & set_volume_func as initialization dependencies ---
def create_app(tag_mappings, save_mappings_func, get_devices_func, set_device_func, get_volume_func, set_volume_func):
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'static/audio'
    app.config['SCAN_STATE'] = scan_state
    bt_manager = BluetoothManager()
    
    @app.route('/')
    def index():
        return render_template('index.html') 

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

    @app.route('/api/start-scan', methods=['POST'])
    def start_scan():
        scan_state['is_scanning'] = True
        scan_state['captured_tag'] = None
        return jsonify({"status": "scanning"})

    @app.route('/api/check-scan', methods=['GET'])
    def check_scan():
        if scan_state['captured_tag']:
            tag = scan_state['captured_tag']
            scan_state['is_scanning'] = False
            scan_state['captured_tag'] = None
            return jsonify({"status": "found", "tag_id": tag})
        return jsonify({"status": "waiting"})

    # --- NEW API ROUTE FOR PROCESSING LIVE AUDIO VOLUME REQUESTS ---
    @app.route('/api/set-volume', methods=['POST'])
    def set_volume_api():
        data = request.get_json() or {}
        volume_val = data.get('volume')
        if volume_val is not None:
            try:
                set_volume_func(int(volume_val))
                return jsonify({"status": "success", "volume": volume_val})
            except ValueError:
                pass
        return jsonify({"status": "error", "message": "Invalid volume payload"}), 400

    @app.route('/settings', methods=['GET', 'POST'])
    def settings_page():
        if request.method == 'POST':
            chosen_device = request.form.get('device_name')
            set_device_func(chosen_device)
            return redirect(url_for('settings_page'))
            
        devices = get_devices_func()
        
        # Pull dynamic variables out of our current execution context
        # assuming your set_device_func/audio_manager structure allows device tracking
        # If your set_device_func is mapped to audio_manager.set_audio_device, you can expose attributes directly
        current_volume = get_volume_func()
        
        # Render the template injecting the extra configuration trackers
        return render_template(
            'settings.html', 
            devices=devices, 
            current_volume=current_volume
        )
    
    @app.route('/api/bluetooth/scan', methods=['POST'])
    def bt_start_scan():
        bt_manager.start_scan(duration=6)
        return jsonify({"status": "scanning_started"})

    @app.route('/api/bluetooth/status', methods=['GET'])
    def bt_status():
        return jsonify(bt_manager.get_scan_status())

    @app.route('/api/bluetooth/connect', methods=['POST'])
    def bt_connect():
        data = request.get_json() or {}
        mac = data.get('mac')
        if not mac:
            return jsonify({"status": "error", "message": "Missing MAC address"}), 400
        res = bt_manager.connect_device(mac)
        return jsonify(res)

    @app.route('/api/bluetooth/disconnect', methods=['POST'])
    def bt_disconnect():
        data = request.get_json() or {}
        mac = data.get('mac')
        if not mac:
            return jsonify({"status": "error", "message": "Missing MAC address"}), 400
        res = bt_manager.disconnect_device(mac)
        return jsonify(res)

    return app