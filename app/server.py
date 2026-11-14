"""
Demo Video SaaS Application
Backend Flask server handling recording sessions, TTS generation, and video assembly.
"""

import os
import json
import uuid
import shutil
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
RECORDINGS_DIR = os.path.join(PROJECT_DIR, 'recordings')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'output')
ASSETS_DIR = os.path.join(PROJECT_DIR, 'assets')
OPENVOICE_DIR = os.path.join(PROJECT_DIR, 'OpenVoice')
CHECKPOINTS_DIR = os.path.join(PROJECT_DIR, 'checkpoints_v2')

# Ensure directories exist
for d in [RECORDINGS_DIR, OUTPUT_DIR, ASSETS_DIR]:
    os.makedirs(d, exist_ok=True)

app = Flask(
    __name__,
    static_folder=os.path.join(PROJECT_DIR, 'static'),
    static_url_path='/static',
    template_folder=os.path.join(PROJECT_DIR, 'templates')
)

# Session store (in-memory)
sessions = {}

# OpenVoice state
openvoice_initialized = False
openvoice_error = None
tts_model = None
tone_converter = None
device = 'cpu'


@app.route('/')
def index():
    """Main page - the demo video recorder UI."""
    return render_template('index.html')


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new recording session."""
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        'id': session_id,
        'created_at': datetime.now().isoformat(),
        'status': 'ready',
        'screen_recording': None,
        'audio_recording': None,
        'events': [],
        'annotations': [],
        'voice_text': '',
        'reference_audio': None,
        'voice_cloned': False
    }
    return jsonify({'session_id': session_id, 'status': 'ready'})


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(sessions[session_id])


@app.route('/api/session/<session_id>/events', methods=['POST'])
def add_event(session_id):
    """Add a recorded event (click, movement, keystroke)."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    data = request.json
    event = {
        'timestamp': data.get('timestamp', 0),
        'type': data.get('type', 'unknown'),  # click, move, key
        'x': data.get('x'),
        'y': data.get('y'),
        'key': data.get('key'),
        'description': data.get('description', '')
    }
    sessions[session_id]['events'].append(event)
    return jsonify({'status': 'ok', 'event_count': len(sessions[session_id]['events'])})


@app.route('/api/session/<session_id>/annotation', methods=['POST'])
def add_annotation(session_id):
    """Add a text annotation at a specific time."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    data = request.json
    annotation = {
        'id': str(uuid.uuid4())[:8],
        'text': data.get('text', ''),
        'start_time': data.get('start_time', 0),
        'end_time': data.get('end_time', 0),
        'position': data.get('position', {'x': 50, 'y': 50}),
        'color': data.get('color', '#ffffff'),
        'font_size': data.get('font_size', 24)
    }
    sessions[session_id]['annotations'].append(annotation)
    return jsonify({'status': 'ok', 'annotation': annotation})


@app.route('/api/session/<session_id>/voice-text', methods=['POST'])
def set_voice_text(session_id):
    """Set the narration text for voice generation."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    data = request.json
    sessions[session_id]['voice_text'] = data.get('text', '')
    return jsonify({'status': 'ok'})


@app.route('/api/session/<session_id>/recording', methods=['POST'])
def upload_recording(session_id):
    """Upload the recorded screen video."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    file = request.files['video']
    filename = f"{session_id}_screen.webm"
    filepath = os.path.join(RECORDINGS_DIR, filename)
    file.save(filepath)
    sessions[session_id]['screen_recording'] = filepath
    sessions[session_id]['status'] = 'recorded'
    return jsonify({'status': 'ok', 'filepath': filepath})


@app.route('/api/session/<session_id>/reference-audio', methods=['POST'])
def upload_reference_audio(session_id):
    """Upload reference audio for voice cloning."""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    file = request.files['audio']
    filename = f"{session_id}_reference.wav"
    filepath = os.path.join(ASSETS_DIR, filename)
    file.save(filepath)
    sessions[session_id]['reference_audio'] = filepath
    return jsonify({'status': 'ok', 'filepath': filepath})


@app.route('/api/tts/generate', methods=['POST'])
def generate_tts():
    """Generate speech from text using gTTS (primary) or OpenVoice (optional)."""
    data = request.json
    text = data.get('text', '')
    session_id = data.get('session_id', '')
    language = data.get('language', 'en')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    output_wav = os.path.join(ASSETS_DIR, f"{session_id}_tts.wav")

    # Try OpenVoice first if initialized
    if openvoice_initialized:
        try:
            import torch
            from openvoice import se_extractor
            from openvoice.api import ToneColorConverter

            session = sessions.get(session_id, {})
            ref_audio = session.get('reference_audio')

            dialect = data.get('dialect', 'EN-US')
            output_base = os.path.join(ASSETS_DIR, f"{session_id}_tts_base.wav")
            tts_model.tts_to_file(text, tts_model.hps.data.spk2id[dialect], output_base, speed=1.0)

            file_key = dialect.lower().replace('_', '-')
            source_se = torch.load(
                os.path.join(CHECKPOINTS_DIR, 'base_speakers', 'ses', f'{file_key}.pth'),
                map_location=device
            )

            if ref_audio and os.path.exists(ref_audio):
                target_se, _ = se_extractor.get_se(ref_audio, tone_converter, vad=True)
            else:
                target_se = source_se

            with torch.no_grad():
                tone_converter.convert(
                    audio_src_path=output_base,
                    src_se=source_se,
                    tgt_se=target_se,
                    output_path=output_wav,
                    message="@MyShell"
                )

            return jsonify({
                'status': 'ok',
                'audio_path': output_wav,
                'method': 'OpenVoice',
                'duration_estimate': len(text) * 0.06
            })
        except Exception as e:
            print(f"OpenVoice failed, falling back to gTTS: {e}")

    # Fallback to gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=language, slow=False)
        output_mp3 = os.path.join(ASSETS_DIR, f"{session_id}_tts.mp3")
        tts.save(output_mp3)

        # Convert MP3 to WAV using ffmpeg
        subprocess.run([
            'ffmpeg', '-y', '-i', output_mp3,
            '-ar', '44100', '-ac', '1',
            output_wav
        ], capture_output=True, check=True)

        return jsonify({
            'status': 'ok',
            'audio_path': output_wav,
            'method': 'gTTS',
            'duration_estimate': len(text) * 0.06
        })
    except Exception as e:
        return jsonify({'error': f'TTS generation failed: {str(e)}'}), 500


@app.route('/api/tts/system', methods=['POST'])
def generate_system_tts():
    """Generate speech using system TTS (espeak/festival) as fallback."""
    data = request.json
    text = data.get('text', '')
    session_id = data.get('session_id', '')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    output_wav = os.path.join(ASSETS_DIR, f"{session_id}_tts_system.wav")

    try:
        # Use espeak-ng for system TTS
        subprocess.run([
            'espeak-ng', '-w', output_wav,
            '-s', '150', '-p', '50',
            text
        ], check=True, capture_output=True)
        return jsonify({
            'status': 'ok',
            'audio_path': output_wav,
            'method': 'espeak-ng'
        })
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return jsonify({'error': f'System TTS not available: {str(e)}'}), 500


@app.route('/api/video/assemble', methods=['POST'])
def assemble_video():
    """Assemble the final video from screen recording, audio, and annotations."""
    data = request.json
    session_id = data.get('session_id', '')

    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404

    session = sessions[session_id]
    screen_video = session.get('screen_recording')
    # Audio file is generated as {session_id}_tts.wav in ASSETS_DIR
    audio_file = os.path.join(ASSETS_DIR, f"{session_id}_tts.wav")
    if not os.path.exists(audio_file):
        audio_file = None  # No audio generated
    annotations = session.get('annotations', [])

    if not screen_video or not os.path.exists(screen_video):
        return jsonify({'error': 'No screen recording found'}), 400

    # Build output filename
    output_filename = f"demo_{session_id}_{int(time.time())}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y']

        # Input screen recording
        cmd.extend(['-i', screen_video])

        # Input audio if available
        if audio_file and os.path.exists(audio_file):
            cmd.extend(['-i', audio_file])

        # Build filter complex for text annotations
        filter_parts = []
        audio_input = 1 if audio_file and os.path.exists(audio_file) else 0
        final_video_label = '0:v'  # Default to unfiltered video

        if annotations:
            # Create drawtext filters for each annotation, chained properly
            prev_label = '0:v'
            drawtext_parts = []
            for i, ann in enumerate(annotations):
                # Position can be a string (top-left, etc.) or dict with x/y
                pos = ann.get('position', 'top-left')
                if isinstance(pos, dict):
                    x = int(pos.get('x', 50))
                    y = int(pos.get('y', 50))
                else:
                    # Map position names to pixel coordinates (assuming 1280x720)
                    pos_map = {
                        'top-left': (50, 50),
                        'top-right': (1180, 50),
                        'bottom-left': (50, 660),
                        'bottom-right': (1180, 660),
                        'center': (615, 335),
                    }
                    x, y = pos_map.get(pos, (50, 50))

                text = ann['text'].replace(':', '\\:').replace(',', '\\,').replace("'", "'\\''")
                color = ann.get('color', 'white')
                font_size = ann.get('font_size', 24)
                start = ann.get('start_time', 0)
                end = ann.get('end_time', 999999)

                out_label = f'annotated_{i}'
                # Use enable with between() for time-based visibility
                # Note: single quotes needed for FFmpeg filter syntax even in subprocess
                filter_str = (
                    f"[{prev_label}]drawtext=text='{text}':x={x}:y={y}:"
                    f"fontsize={font_size}:fontcolor={color}:"
                    f"font=DejaVu-Sans:"
                    f"enable='between(t,{start},{end})'[{out_label}]"
                )
                drawtext_parts.append(filter_str)
                prev_label = out_label

            # Final output label
            final_video_label = prev_label
            if drawtext_parts:
                filter_parts.append(';'.join(drawtext_parts))

        # Apply filters
        if filter_parts:
            cmd.extend(['-filter_complex', ';'.join(filter_parts)])
            # Map the final annotated video output (last label in chain)
            cmd.extend(['-map', f'[{final_video_label}]'])
            if audio_input:
                cmd.extend(['-map', '1:a'])
        else:
            if audio_input:
                cmd.extend(['-map', '0:v', '-map', '1:a'])
            else:
                cmd.extend(['-map', '0:v'])

        # Audio settings
        if audio_input:
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '23'])
            cmd.extend(['-c:a', 'aac', '-b:a', '192k', '-shortest'])
        else:
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-an'])

        cmd.append(output_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return jsonify({'error': f'FFmpeg error: {result.stderr}'}), 500

        session['status'] = 'completed'
        session['output_file'] = output_path

        return jsonify({
            'status': 'ok',
            'output_file': output_path,
            'filename': output_filename
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Video assembly timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/download/<filename>')
def download_video(filename):
    """Download the assembled video."""
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.route('/api/video/<filename>')
def stream_video(filename):
    """Stream the assembled video for preview."""
    return send_from_directory(OUTPUT_DIR, filename)


@app.route('/api/audio/<filename>')
def stream_audio(filename):
    """Stream generated audio for preview."""
    return send_from_directory(ASSETS_DIR, filename)


@app.route('/api/openvoice/status', methods=['GET'])
def openvoice_status():
    """Check OpenVoice initialization status."""
    return jsonify({
        'initialized': openvoice_initialized,
        'error': openvoice_error,
        'device': device,
        'checkpoints_dir': CHECKPOINTS_DIR,
        'checkpoints_exist': os.path.exists(CHECKPOINTS_DIR)
    })


@app.route('/api/openvoice/init', methods=['POST'])
def init_openvoice():
    """Initialize OpenVoice models."""
    global openvoice_initialized, openvoice_error, tts_model, tone_converter, device

    try:
        import torch

        # Detect device
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = 'mps'
        elif torch.cuda.is_available():
            device = 'cuda:0'
        else:
            device = 'cpu'

        # Check if checkpoints exist
        if not os.path.exists(CHECKPOINTS_DIR):
            openvoice_error = 'Checkpoints not found. Please download OpenVoice V2 checkpoints.'
            openvoice_initialized = False
            return jsonify({
                'status': 'error',
                'error': openvoice_error,
                'download_url': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip'
            })

        # Initialize TTS model
        from melo.api import TTS
        tts_model = TTS(language='EN', device=device)

        # Initialize tone color converter
        from openvoice.api import ToneColorConverter
        converter_config = os.path.join(CHECKPOINTS_DIR, 'converter', 'config.json')
        converter_ckpt = os.path.join(CHECKPOINTS_DIR, 'converter', 'checkpoint.pth')

        if not os.path.exists(converter_config) or not os.path.exists(converter_ckpt):
            openvoice_error = 'Converter model files not found.'
            openvoice_initialized = False
            return jsonify({'status': 'error', 'error': openvoice_error})

        tone_converter = ToneColorConverter(converter_config, device=device)
        tone_converter.load_ckpt(converter_ckpt)

        openvoice_initialized = True
        openvoice_error = None

        return jsonify({
            'status': 'ok',
            'device': device,
            'supported_dialects': list(tts_model.hps.data.spk2id.keys())
        })

    except ImportError as e:
        openvoice_error = f'Missing dependency: {str(e)}'
        openvoice_initialized = False
        return jsonify({'status': 'error', 'error': openvoice_error})
    except Exception as e:
        openvoice_error = str(e)
        openvoice_initialized = False
        return jsonify({'status': 'error', 'error': openvoice_error})


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'server': 'Demo Video SaaS',
        'version': '1.0.0'
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  Demo Video SaaS Application")
    print("  Starting server on http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
