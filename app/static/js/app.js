$(document).ready(function () {
    // DOM elements
    const $recordButton = $('#recordButton');
    const $recordingStatus = $('#recordingStatus');
    const $transcript = $('#transcript');

    // Chat history and messaging
    let currentChatId = null;

    // Add a response container to the HTML if it doesn't exist
    if ($('#responseContainer').length === 0) {
        const $responseContainer = $('<div>', {
            id: 'responseContainer',
            class: 'response-container'
        }).insertAfter('.transcript-container');

        $responseContainer.html(`
            <div class="chat-header">
                <div class="current-chat-info" id="currentChatInfo">New conversation</div>
                <button id="newChatBtn" class="new-chat-btn">New Chat</button>
            </div>
            <h3>Assistant Response:</h3>
            <div id="assistantResponse" class="assistant-response">
                Waiting for your voice command...
            </div>
        `);
    }

    // $responseContainer.html(`
    //     <h3>Assistant Response:</h3>
    //     <div id="assistantResponse" class="assistant-response">
    //         Waiting for your voice command...
    //     </div>
    // `);

    const $assistantResponse = $('#assistantResponse');
    const $currentChatInfo = $('#currentChatInfo');
    const $newChatBtn = $('#newChatBtn');

    // Initialize variables
    let recorder = null;
    let recordingTimeout = null;
    const maxRecordingTime = 60000; // 60 seconds

    // Check if recording is supported
    if (!AudioRecorder.isSupported()) {
        alert('Your browser does not support audio recording. Please try another browser.');
        $recordButton.prop('disabled', true);
        $recordingStatus.text('Recording not supported in this browser');
        return;
    }

    // Initialize audio recorder
    async function initRecorder() {
        recorder = new AudioRecorder();

        // Set up event handlers
        recorder.onStart = () => {
            $recordButton.addClass('recording');
            $recordingStatus.text('Recording... (speak now)');

            // Set timeout to automatically stop recording after maxRecordingTime
            recordingTimeout = setTimeout(() => {
                stopRecording();
            }, maxRecordingTime);
        };

        recorder.onStop = async (audioBlob) => {
            $recordButton.removeClass('recording');
            $recordingStatus.text('Processing audio...');

            // Clear the timeout if it exists
            if (recordingTimeout) {
                clearTimeout(recordingTimeout);
                recordingTimeout = null;
            }

            // Send the audio for transcription
            await sendAudioForTranscription(audioBlob);
        };

        recorder.onError = (error) => {
            console.error('Recording error:', error);
            $recordingStatus.text(`Error: ${error.message}`);
            $recordButton.removeClass('recording');
        };

        const initialized = await recorder.init();
        if (!initialized) {
            $recordingStatus.text('Failed to access microphone. Please check permissions.');
            $recordButton.prop('disabled', true);
        } else {
            $recordingStatus.text('Recorder initialized. Ready to record.');
        }
    }

    // Toggle recording
    function toggleRecording() {
        if (!recorder) {
            initRecorder();
            return;
        }

        if (recorder.isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }

    // Start recording
    function startRecording() {
        if (!recorder) {
            initRecorder().then(() => {
                if (recorder) {
                    recorder.start();
                }
            });
        } else {
            recorder.start();
        }
    }

    // Stop recording
    function stopRecording() {
        if (recorder && recorder.isRecording) {
            recorder.stop();
        }
    }

    // Send audio for transcription
    async function sendAudioForTranscription(audioBlob) {
        // Create form data with the audio blob
        const formData = new FormData();

        // Log the blob details for debugging
        console.log("Audio blob:", {
            type: audioBlob.type,
            size: audioBlob.size,
            lastModified: audioBlob.lastModified
        });

        // Check if the blob is too small (likely empty recording)
        if (audioBlob.size < 1000) {  // Less than 1KB
            $recordingStatus.text('Recording too short or empty. Please try again.');
            $assistantResponse.text('Please record a longer message.');
            return;
        }

        // Add chat ID if we have one
        if (currentChatId) {
            formData.append('chatId', currentChatId);
        }

        formData.append('audio', audioBlob, 'recording.' + (audioBlob.type.split('/')[1] || 'webm'));

        try {
            $recordingStatus.text('Sending audio for transcription...');

            // Show streaming animation
            $assistantResponse.text('');
            $assistantResponse.addClass('loading');

            // Send the request
            const response = await $.ajax({
                url: '/transcribe',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                timeout: 30000  // 30 seconds
            });

            // Remove streaming animation
            $assistantResponse.removeClass('loading');

            // Check for errors
            if (response.error) {
                $recordingStatus.text(`Error: ${response.error}`);
                $assistantResponse.text(response.response || 'An error occurred. Please try again.');
                return;
            }

            // Update the transcript
            if (response.transcription) {
                $transcript.text(response.transcription);
                $recordingStatus.text('Transcription complete');
            } else {
                $transcript.text('No transcription available');
                $recordingStatus.text('Could not transcribe audio');
            }

            // Display the assistant's response with typewriter effect
            if (response.response) {
                // Use the typewriter effect for a more dynamic response
                typewriterEffect($assistantResponse, response.response);
            } else {
                $assistantResponse.text('No response from assistant');
            }

            // Update chat ID
            if (response.chatId) {
                currentChatId = response.chatId;
                $currentChatInfo.text(`Conversation #${currentChatId}`);
            }
        } catch (error) {
            console.error('Error transcribing audio:', error);
            $recordingStatus.text(`Error: ${error.statusText || error.message || 'Failed to transcribe audio'}`);
            $assistantResponse.removeClass('loading');
            $assistantResponse.text('An error occurred. Please try again.');
        }
    }

    // Typewriter effect for responses
    function typewriterEffect($element, text) {
        const typingSpeed = 10; // ms per character
        let i = 0;
        $element.text('');

        function typeNextChar() {
            if (i < text.length) {
                $element.text($element.text() + text.charAt(i));
                i++;
                setTimeout(typeNextChar, typingSpeed);
            }
        }

        typeNextChar();
    }

    // Start a new chat
    function startNewChat() {
        currentChatId = null;
        $currentChatInfo.text('New conversation');
        $transcript.text('Your spoken words will appear here...');
        $assistantResponse.text('Waiting for your voice command...');
    }

    // Event listeners
    $recordButton.on('click', toggleRecording);
    $newChatBtn.on('click', startNewChat);

    // Handle page visibility change (pause recording when tab is not visible)
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState !== 'visible' && recorder && recorder.isRecording) {
            stopRecording();
            $recordingStatus.text('Recording stopped: tab lost focus');
        }
    });

    // Initialize
    initRecorder();

    // Add a function to send text messages directly (optional)
    function sendTextMessage(message) {
        try {
            $assistantResponse.text('Processing your request...');
            $assistantResponse.addClass('loading');

            // Send the request
            $.ajax({
                url: '/chat',
                type: 'POST',
                data: JSON.stringify({message: message}),
                contentType: 'application/json',
                success: function (response) {
                    $assistantResponse.removeClass('loading');
                    $assistantResponse.text(response.response);
                },
                error: function (xhr, status, error) {
                    console.error('Error sending text message:', error);
                    $assistantResponse.removeClass('loading');
                    $assistantResponse.text('An error occurred. Please try again.');
                }
            });
        } catch (error) {
            console.error('Error sending text message:', error);
            $assistantResponse.removeClass('loading');
            $assistantResponse.text('An error occurred. Please try again.');
        }
    }

    // Event listeners
    $recordButton.on('click', toggleRecording);
});