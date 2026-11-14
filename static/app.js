/**
 * Demo Video SaaS - Frontend Application
 * Handles screen recording, input tracking, annotations, and voice generation.
 */

class DemoVideoApp {
    constructor() {
        this.sessionId = null;
        this.isRecording = false;
        this.startTime = null;
        this.timerInterval = null;
        this.mediaRecorder = null;
        this.screenStream = null;
        this.audioContext = null;
        this.events = [];
        this.annotations = [];
        this.recordingChunks = [];
        this.voiceAudioBlob = null;

        this.init();
    }

    async init() {
        this.bindEvents();
        await this.checkHealth();
        await this.checkOpenVoiceStatus();
    }

    // ==================== API Helpers ====================

    async api(endpoint, options = {}) {
        try {
            const res = await fetch(`/api${endpoint}`, {
                ...options,
                headers: { 'Content-Type': 'application/json', ...options.headers }
            });
            return await res.json();
        } catch (err) {
            console.error('API error:', err);
            return { error: err.message };
        }
    }

    async checkHealth() {
        const status = await this.api('/health');
        const el = document.getElementById('connection-status');
        if (status.status === 'ok') {
            el.textContent = 'Connected';
            el.className = 'status-badge status-ok';
        } else {
            el.textContent = 'Disconnected';
            el.className = 'status-badge';
        }
    }

    async checkOpenVoiceStatus() {
        const status = await this.api('/openvoice/status');
        const el = document.getElementById('openvoice-status');
        if (status.initialized) {
            el.textContent = 'Voice: Ready';
            el.className = 'status-badge status-ok';
        } else if (status.checkpoints_exist) {
            el.textContent = 'Voice: Init Required';
            el.className = 'status-badge status-neutral';
        } else {
            el.textContent = 'Voice: Models Missing';
            el.className = 'status-badge';
        }
    }

    // ==================== Event Binding ====================

    bindEvents() {
        document.getElementById('btn-start').addEventListener('click', () => this.startRecording());
        document.getElementById('btn-stop').addEventListener('click', () => this.stopRecording());
        document.getElementById('btn-generate-voice').addEventListener('click', () => this.generateVoice());
        document.getElementById('btn-add-annotation').addEventListener('click', () => this.addAnnotation());
        document.getElementById('btn-assemble').addEventListener('click', () => this.assembleVideo());
        document.getElementById('btn-upload-voice').addEventListener('click', () => {
            document.getElementById('voice-reference').click();
        });
        document.getElementById('voice-reference').addEventListener('change', (e) => this.handleVoiceUpload(e));
        document.getElementById('font-size').addEventListener('input', (e) => {
            document.getElementById('font-size-val').textContent = e.target.value;
        });
    }

    // ==================== Screen Recording ====================

    async startRecording() {
        try {
            // Create session
            const session = await this.api('/session/create');
            this.sessionId = session.session_id;

            // Request screen capture
            this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always',
                    displaySurface: 'monitor'
                },
                audio: false
            });

            // Get screen resolution
            const track = this.screenStream.getVideoTracks()[0];
            const settings = track.getSettings();
            document.getElementById('screen-res').textContent = `${settings.width} x ${settings.height}`;

            // Show preview
            const video = document.getElementById('screen-preview');
            video.srcObject = this.screenStream;

            // Setup MediaRecorder
            this.recordingChunks = [];
            const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
                ? 'video/webm;codecs=vp9'
                : 'video/webm';
            this.mediaRecorder = new MediaRecorder(this.screenStream, { mimeType });

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.recordingChunks.push(e.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                const blob = new Blob(this.recordingChunks, { type: 'video/webm' });
                await this.uploadRecording(blob);
            };

            // Handle stream stop (user presses ESC or shares stop)
            this.screenStream.getVideoTracks()[0].addEventListener('ended', () => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            });

            // Start recording
            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            this.startTime = Date.now();
            this.events = [];

            // Update UI
            this.updateRecordingUI(true);
            this.startTimer();
            this.startInputTracking();
            this.startAnnotationOverlay();

            // Enable voice button
            document.getElementById('btn-generate-voice').disabled = false;

        } catch (err) {
            console.error('Failed to start recording:', err);
            alert('Failed to start screen recording. Please allow screen sharing permission.');
        }
    }

    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
        }

        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
        }

        this.isRecording = false;
        this.stopTimer();
        this.stopInputTracking();
        this.stopAnnotationOverlay();
        this.updateRecordingUI(false);

        // Upload events
        await this.uploadEvents();
    }

    async uploadRecording(blob) {
        const formData = new FormData();
        formData.append('video', blob, 'screen_recording.webm');

        try {
            const res = await fetch(`/api/session/${this.sessionId}/recording`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.status === 'ok') {
                document.getElementById('assembly-status').textContent = 'Recording saved. Ready to assemble.';
                document.getElementById('btn-assemble').disabled = false;
            }
        } catch (err) {
            console.error('Failed to upload recording:', err);
        }
    }

    updateRecordingUI(recording) {
        const btnStart = document.getElementById('btn-start');
        const btnStop = document.getElementById('btn-stop');
        const indicator = document.getElementById('recording-indicator');

        btnStart.disabled = recording;
        btnStop.disabled = !recording;

        if (recording) {
            indicator.className = 'recording-indicator recording';
            indicator.innerHTML = '<span class="rec-dot"></span> Recording...';
        } else {
            indicator.className = 'recording-indicator';
            indicator.innerHTML = '<span class="rec-dot"></span> Ready';
        }
    }

    startTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            document.getElementById('recording-timer').textContent =
                `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    // ==================== Input Tracking ====================

    startInputTracking() {
        this.mouseMoveHandler = (e) => this.trackMouseEvent(e, 'move');
        this.mouseDownHandler = (e) => this.trackMouseEvent(e, 'click');
        this.keyDownHandler = (e) => this.trackKeyEvent(e);

        document.addEventListener('mousemove', this.mouseMoveHandler);
        document.addEventListener('mousedown', this.mouseDownHandler);
        document.addEventListener('keydown', this.keyDownHandler);
    }

    stopInputTracking() {
        document.removeEventListener('mousemove', this.mouseMoveHandler);
        document.removeEventListener('mousedown', this.mouseDownHandler);
        document.removeEventListener('keydown', this.keyDownHandler);
    }

    trackMouseEvent(e, type) {
        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(2);
        const event = {
            timestamp: elapsed,
            type: type,
            x: e.clientX,
            y: e.clientY,
            description: type === 'click' ? `Clicked at (${e.clientX}, ${e.clientY})` : ''
        };
        this.events.push(event);
        this.logEvent(event);
        document.getElementById('event-count').textContent = `Events: ${this.events.length}`;

        if (type === 'click') {
            this.showClickIndicator(e.clientX, e.clientY);
        }
    }

    trackKeyEvent(e) {
        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(2);
        const event = {
            timestamp: elapsed,
            type: 'key',
            key: e.key,
            description: `Typed: ${e.key}`
        };
        this.events.push(event);
        this.logEvent(event);
        document.getElementById('event-count').textContent = `Events: ${this.events.length}`;
    }

    showClickIndicator(x, y) {
        const indicator = document.getElementById('click-indicator');
        indicator.style.left = x + 'px';
        indicator.style.top = y + 'px';
        indicator.classList.add('active');
        setTimeout(() => indicator.classList.remove('active'), 500);
    }

    logEvent(event) {
        const log = document.getElementById('events-log');
        const empty = log.querySelector('.log-empty');
        if (empty) empty.remove();

        const entry = document.createElement('div');
        entry.className = `log-entry ${event.type}`;
        entry.innerHTML = `
            <span class="log-time">${event.timestamp}s</span>
            <span class="log-type ${event.type}">${event.type}</span>
            <span class="log-desc">${event.description || ''}</span>
        `;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }

    async uploadEvents() {
        for (const event of this.events) {
            await this.api(`/session/${this.sessionId}/events`, {
                method: 'POST',
                body: JSON.stringify(event)
            });
        }
    }

    // ==================== Annotations ====================

    startAnnotationOverlay() {
        this.annotationInterval = setInterval(() => {
            this.renderActiveAnnotations();
        }, 100);
    }

    stopAnnotationOverlay() {
        if (this.annotationInterval) {
            clearInterval(this.annotationInterval);
            this.annotationInterval = null;
        }
    }

    addAnnotation() {
        const text = document.getElementById('annotation-text').value.trim();
        if (!text) {
            alert('Please enter annotation text');
            return;
        }

        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(2);
        const position = document.querySelector('input[name="pos"]:checked').value;
        const color = document.getElementById('annotation-color').value;
        const fontSize = document.getElementById('font-size').value;

        const annotation = {
            id: Date.now().toString(36),
            text: text,
            start_time: parseFloat(elapsed),
            end_time: parseFloat(elapsed) + 5, // Show for 5 seconds by default
            position: position,
            color: color,
            font_size: parseInt(fontSize)
        };

        this.annotations.push(annotation);
        this.renderAnnotationList();
        this.saveAnnotation(annotation);
        document.getElementById('annotation-text').value = '';
    }

    renderAnnotationList() {
        const list = document.getElementById('annotations-list');
        list.innerHTML = this.annotations.map((ann, i) => `
            <div class="annotation-item">
                <span class="ann-text">${ann.text}</span>
                <span class="ann-time">@${ann.start_time}s</span>
                <button class="ann-delete" onclick="app.deleteAnnotation(${i})">&times;</button>
            </div>
        `).join('');
    }

    deleteAnnotation(index) {
        this.annotations.splice(index, 1);
        this.renderAnnotationList();
    }

    async saveAnnotation(annotation) {
        await this.api(`/session/${this.sessionId}/annotation`, {
            method: 'POST',
            body: JSON.stringify(annotation)
        });
    }

    renderActiveAnnotations() {
        const elapsed = (Date.now() - this.startTime) / 1000;
        const overlay = document.getElementById('annotation-overlay');
        const active = this.annotations.filter(a =>
            elapsed >= a.start_time && elapsed <= a.end_time
        );

        overlay.innerHTML = active.map(ann => {
            let posStyle = '';
            switch (ann.position) {
                case 'top-left': posStyle = 'top: 20px; left: 20px;'; break;
                case 'top-right': posStyle = 'top: 20px; right: 20px;'; break;
                case 'bottom-left': posStyle = 'bottom: 20px; left: 20px;'; break;
                case 'bottom-right': posStyle = 'bottom: 20px; right: 20px;'; break;
                case 'center': posStyle = 'top: 50%; left: 50%; transform: translate(-50%, -50%);'; break;
            }
            return `
                <div style="
                    position: absolute;
                    ${posStyle}
                    color: ${ann.color};
                    font-size: ${ann.font_size}px;
                    font-family: 'Inter', sans-serif;
                    font-weight: 600;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
                    background: rgba(0,0,0,0.5);
                    padding: 8px 16px;
                    border-radius: 8px;
                    max-width: 80%;
                ">
                    ${ann.text}
                </div>
            `;
        }).join('');
    }

    // ==================== Voice Generation ====================

    async handleVoiceUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('audio', file);

        try {
            const res = await fetch(`/api/session/${this.sessionId}/reference-audio`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.status === 'ok') {
                document.getElementById('voice-reference-status').textContent =
                    `✓ Reference audio uploaded: ${file.name}`;
            }
        } catch (err) {
            document.getElementById('voice-reference-status').textContent =
                `✗ Upload failed: ${err.message}`;
        }
    }

    async generateVoice() {
        const text = document.getElementById('voice-text').value.trim();
        if (!text) {
            alert('Please enter narration text');
            return;
        }

        const dialect = document.getElementById('voice-dialect').value;
        const btn = document.getElementById('btn-generate-voice');
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">⏳</span> Generating...';

        // First try OpenVoice
        let result = await this.api('/tts/generate', {
            method: 'POST',
            body: JSON.stringify({
                text: text,
                session_id: this.sessionId,
                language: 'EN',
                dialect: dialect
            })
        });

        // Fallback to system TTS if OpenVoice unavailable
        if (result.available === false || result.error) {
            result = await this.api('/tts/system', {
                method: 'POST',
                body: JSON.stringify({
                    text: text,
                    session_id: this.sessionId
                })
            });
        }

        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🔊</span> Generate Voice';

        if (result.status === 'ok' && result.audio_path) {
            this.voiceAudioBlob = result.audio_path;
            const preview = document.getElementById('voice-preview');
            const method = result.method || 'TTS';
            const sessionId = this.sessionId;
            preview.innerHTML = `
                <p class="status-text" style="color: var(--success)">✓ Voice generated using ${method}</p>
                <audio controls src="/api/audio/${sessionId}_tts.wav"></audio>
            `;
            document.getElementById('assembly-status').textContent = 'Voice generated. Ready to assemble.';
        } else {
            document.getElementById('voice-preview').innerHTML =
                `<p class="status-text" style="color: var(--danger)">✗ ${result.error || 'Generation failed'}</p>`;
        }
    }

    // ==================== Video Assembly ====================

    async assembleVideo() {
        const btn = document.getElementById('btn-assemble');
        const status = document.getElementById('assembly-status');
        btn.disabled = true;
        status.textContent = 'Assembling video... This may take a moment.';

        const result = await this.api('/video/assemble', {
            method: 'POST',
            body: JSON.stringify({ session_id: this.sessionId })
        });

        if (result.status === 'ok') {
            status.textContent = '✓ Video assembled successfully!';
            const downloadLink = document.getElementById('download-link');
            downloadLink.href = `/api/video/download/${result.filename}`;
            downloadLink.style.display = 'flex';
        } else {
            status.textContent = `✗ Assembly failed: ${result.error}`;
        }

        btn.disabled = false;
    }
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new DemoVideoApp();
});
