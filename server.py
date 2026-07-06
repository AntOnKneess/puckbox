import os
from flask import Flask, render_template, request, redirect, url_for

def create_app(tag_mappings, save_mappings_func):
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'static/audio'

    @app.route('/')
    def index():
        # Simple homepage
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
        
        # GET request: Consolidates files, mappings, and configuration interfaces
        files = os.listdir(app.config['UPLOAD_FOLDER']) if os.path.exists(app.config['UPLOAD_FOLDER']) else []
        return render_template('upload.html', mappings=tag_mappings, files=files)

    @app.route('/map', methods=['POST'])
    def map_tag():
        tag_id = request.form.get('tag_id').strip()
        filename = request.form.get('filename')
        if tag_id and filename:
            tag_mappings[tag_id] = filename
            save_mappings_func()
        return redirect(url_for('upload_file')) # Redirect back to upload management hub

    return app