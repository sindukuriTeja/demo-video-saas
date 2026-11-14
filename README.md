# Demo Video SaaS Application

A web-based application for creating demo videos with screen recording, click/mouse tracking, text annotations, and AI voice narration using OpenVoice voice cloning technology.

## Features

- **Screen Recording**: Record your screen directly from the browser using the MediaRecorder API
- **Input Tracking**: Automatically tracks mouse clicks, movements, and keyboard events during recording
- **Text Annotations**: Add timed text overlays that appear at specific moments in the video
- **Voice Narration**: Generate AI voiceover from text using:
  - **gTTS** (Google Text-to-Speech) - Works out of the box, multi-language support
  - **OpenVoice** (optional) - Voice cloning from a reference audio sample
- **Video Assembly**: Combines screen recording + voiceover + annotations into a single MP4 using FFmpeg
- **Download**: Export the final demo video

## Architecture

```
demo-video-saas/
├── app/
│   └── server.py          # Flask backend server
├── templates/
│   └── index.html         # Main UI
├── static/
│   ├── style.css          # Styles
│   └── app.js             # Frontend logic (recording, tracking, annotations)
├── checkpoints_v2/        # OpenVoice V2 model files
│   ├── base_speakers/ses/ # Base speaker embeddings (11 languages)
│   └── converter/         # Tone color converter model
├── OpenVoice/             # OpenVoice source code
├── recordings/            # Uploaded screen recordings
├── assets/                # Generated audio files
├── output/                # Final assembled videos
├── requirements.txt       # Python dependencies
├── start.sh               # Startup script
└── test_app.py            # End-to-end test suite
```

## How It Works

1. **Start Recording**: Click "Start Recording" and grant screen sharing permission
2. **Perform Actions**: Navigate your app while the system tracks clicks, movements, and keystrokes
3. **Add Narration**: Type narration text and generate voiceover (gTTS or OpenVoice)
4. **Add Annotations**: Insert text overlays that appear at specific timestamps
5. **Assemble**: Click "Assemble Video" to combine everything into a final MP4
6. **Download**: Download the completed demo video

## Setup & Run

### Prerequisites
- Python 3.9+
- FFmpeg
- Modern web browser (Chrome/Edge/Firefox)

### Install Dependencies
```bash
cd /opt/sandbox/workspace/demo-video-saas
pip3 install -r requirements.txt
```

### Start the Server
```bash
./start.sh
# or
export PYTHONPATH="/opt/sandbox/workspace/demo-video-saas/OpenVoice:$PYTHONPATH"
python3 app/server.py
```

### Open the App
Navigate to `http://localhost:5000` in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/session/create` | POST | Create a new recording session |
| `/api/session/<id>` | GET | Get session details |
| `/api/session/<id>/events` | POST | Add a recorded event |
| `/api/session/<id>/recording` | POST | Upload screen recording |
| `/api/session/<id>/annotation` | POST | Add a text annotation |
| `/api/session/<id>/reference-audio` | POST | Upload voice reference for cloning |
| `/api/tts/generate` | POST | Generate voice from text |
| `/api/video/assemble` | POST | Assemble final video |
| `/api/video/<filename>` | GET | Stream video |
| `/api/video/download/<filename>` | GET | Download video |
| `/api/audio/<filename>` | GET | Stream generated audio |

## Voice Options

### gTTS (Default)
- Works immediately, no model download needed
- Supports multiple languages
- Uses Google's TTS service

### OpenVoice (Optional - Voice Cloning)
- Requires downloading OpenVoice V2 checkpoints (already included)
- Clone a voice from a reference audio sample
- Supports flexible voice style control (emotion, accent, rhythm)
- **Note**: Requires MeloTTS installation which may have compatibility issues with newer numpy versions. Falls back to gTTS automatically.

## Testing

Run the end-to-end test suite:
```bash
python3 test_app.py
```

This tests:
- Health check
- Session creation
- Event recording (click, move, key)
- Annotations
- Voice generation (gTTS)
- Test video creation
- Video assembly with annotations and audio
- OpenVoice status check

## Supported Languages for Voice

English (US, UK, Australia, India), Spanish, French, Chinese, Japanese, Korean

## License

This application integrates OpenVoice which is released under the MIT License.
