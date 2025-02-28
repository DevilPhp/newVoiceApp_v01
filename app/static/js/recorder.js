class AudioRecorder {
    constructor(options = {}) {
        this.options = {
            mimeType: 'audio/webm',
            audioBitsPerSecond: 128000,
            ...options
        };

        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.onDataAvailable = null;
        this.onStop = null;
        this.onStart = null;
        this.onError = null;
        this.startTime = 0;
        this.timerInterval = null;
        this.initialized = false;
    }

    /**
     * Request microphone access and initialize the recorder
     */
    async init() {
        try {
            // If already initialized, release previous resources
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }

            this.initialized = false;

            // Try different audio constraints for better cross-browser compatibility
            const audioConstraints = {
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            };

            // Get microphone access
            console.log("Attempting to get user media with constraints:", audioConstraints);
            this.stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
            console.log("Successfully got user media stream:", this.stream);

            // Determine supported mime types
            const mimeTypes = [
                'audio/webm',
                'audio/webm;codecs=opus',
                'audio/mp4',
                'audio/ogg',
                'audio/wav'
            ];

            let selectedMimeType = null;

            // Find the first supported mime type
            for (const mimeType of mimeTypes) {
                if (MediaRecorder.isTypeSupported(mimeType)) {
                    selectedMimeType = mimeType;
                    console.log(`Browser supports mime type: ${mimeType}`);
                    break;
                } else {
                    console.log(`Browser does not support mime type: ${mimeType}`);
                }
            }

            if (!selectedMimeType) {
                console.warn("None of the preferred mime types are supported. Using default.");
            }

            // Create the MediaRecorder with the best available options
            const recorderOptions = selectedMimeType ?
                { mimeType: selectedMimeType, audioBitsPerSecond: this.options.audioBitsPerSecond } :
                {};

            console.log("Creating MediaRecorder with options:", recorderOptions);
            this.mediaRecorder = new MediaRecorder(this.stream, recorderOptions);
            console.log("MediaRecorder created successfully with mimeType:", this.mediaRecorder.mimeType);

            this.mediaRecorder.addEventListener('dataavailable', event => {
                console.log("Data available event received, data size:", event.data.size);
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }

                if (this.onDataAvailable) {
                    this.onDataAvailable(event.data);
                }
            });

            this.mediaRecorder.addEventListener('stop', () => {
                console.log("Recording stopped, creating audio blob");
                const audioBlob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType });
                console.log("Created audio blob of type:", this.mediaRecorder.mimeType, "size:", audioBlob.size);
                this.audioChunks = [];
                this.isRecording = false;
                this.stopTimer();

                if (this.onStop) {
                    this.onStop(audioBlob);
                }
            });

            this.mediaRecorder.addEventListener('start', () => {
                console.log("Recording started");
                this.isRecording = true;
                this.audioChunks = [];
                this.startTimer();

                if (this.onStart) {
                    this.onStart();
                }
            });

            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Error initializing recorder:', error);
            if (this.onError) {
                this.onError(error);
            }
            return false;
        }
    }

    /**
     * Start recording audio
     */
    async start() {
        if (this.isRecording) {
            console.warn("Cannot start recording: already recording");
            return false;
        }

        // Ensure the recorder is initialized
        if (!this.initialized || !this.mediaRecorder) {
            console.log("Recorder not initialized, initializing now");
            const initialized = await this.init();
            if (!initialized) {
                console.error("Failed to initialize recorder");
                return false;
            }
        }

        try {
            console.log("Starting recording");
            this.mediaRecorder.start(1000); // Collect data every second
            return true;
        } catch (error) {
            console.error('Error starting recording:', error);
            if (this.onError) {
                this.onError(error);
            }
            return false;
        }
    }

    /**
     * Stop recording audio
     */
    stop() {
        if (!this.isRecording) {
            console.warn("Cannot stop recording: not recording");
            return false;
        }

        try {
            console.log("Stopping recording");
            this.mediaRecorder.stop();
            return true;
        } catch (error) {
            console.error('Error stopping recording:', error);
            if (this.onError) {
                this.onError(error);
            }
            return false;
        }
    }

    /**
     * Release all resources
     */
    release() {
        this.stopTimer();

        if (this.stream) {
            console.log("Releasing stream resources");
            this.stream.getTracks().forEach(track => {
                console.log("Stopping track:", track.kind, track.label);
                track.stop();
            });
            this.stream = null;
        }

        this.mediaRecorder = null;
        this.initialized = false;
        this.isRecording = false;
        this.audioChunks = [];
    }

    // Timer methods
    startTimer() {
        this.startTime = Date.now();
        this.updateTimer();

        this.timerInterval = setInterval(() => {
            this.updateTimer();
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimer() {
        const elapsedTime = Date.now() - this.startTime;
        const seconds = Math.floor(elapsedTime / 1000) % 60;
        const minutes = Math.floor(elapsedTime / 60000);

        const timerElement = document.getElementById('timer');
        if (timerElement) {
            timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Check if the browser supports audio recording
     */
    static isSupported() {
        const hasGetUserMedia = !!(navigator.mediaDevices &&
                                   navigator.mediaDevices.getUserMedia);
        const hasMediaRecorder = typeof MediaRecorder !== 'undefined';

        console.log("Browser support check:",
                   "getUserMedia:", hasGetUserMedia,
                   "MediaRecorder:", hasMediaRecorder);

        return hasGetUserMedia && hasMediaRecorder;
    }

    /**
     * Check if the app has microphone permission
     */
    static async hasMicrophonePermission() {
        try {
            console.log("Checking microphone permissions");
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioDevices = devices.filter(device => device.kind === 'audioinput');

            console.log("Audio input devices:", audioDevices);

            // If no audio devices are found, return false
            if (audioDevices.length === 0) {
                console.warn("No audio input devices found");
                return false;
            }

            // Check if at least one audio device has permission (non-empty label)
            const hasPermission = audioDevices.some(device => device.label !== '');
            console.log("Has microphone permission:", hasPermission);
            return hasPermission;
        } catch (error) {
            console.error('Error checking microphone permission:', error);
            return false;
        }
    }
}