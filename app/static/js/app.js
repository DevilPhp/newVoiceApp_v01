$(document).ready(function () {
    // DOM elements
    const $recordButton = $('#recordButton');
    const $recordingStatus = $('#recordingStatus');
    const $chatMessagesContainer = $('#chatMessagesContainer');
    const $currentChatInfo = $('#currentChatInfo');
    const $newChatBtn = $('#newChatBtn');
    const $chatHistoryContainer = $('#chatHistoryContainer');
    const $chatHistoryList = $('#chatHistoryList');

    // Chat history and messaging
    let currentChatId = null;

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

    // Parse and render markdown text
    function renderMarkdown(text) {
        if (!text) return '';

        // Replace new lines with <br> tags
        let html = text.replace(/\n/g, '<br>');

        // Bold text
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic text
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Headers
        html = html.replace(/#{3}\s+(.*?)(?:\n|$)/g, '<h3>$1</h3>');
        html = html.replace(/#{2}\s+(.*?)(?:\n|$)/g, '<h2>$1</h2>');
        html = html.replace(/#{1}\s+(.*?)(?:\n|$)/g, '<h1>$1</h1>');

        // Bullet lists
        html = html.replace(/^-\s+(.*?)(?:\n|$)/gm, '<li>$1</li>');

        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, function(match, p1) {
            return '<pre><code>' + p1 + '</code></pre>';
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        return html;
    }

    // Format date and time
    function formatDateTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString('bg-BG', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Create a message element with or without content
    function createMessageElement(role, timestamp) {
        const formattedTime = timestamp ? formatDateTime(timestamp) : formatDateTime(new Date().toISOString());
        const $messageContainer = $('<div>', {
            class: `message ${role}`
        });

        const $messageHeader = $('<div>', {
            class: 'message-header'
        }).text(role === 'user' ? 'You' : 'Assistant').appendTo($messageContainer);

        const $timestamp = $('<span>', {
            class: 'message-time'
        }).text(formattedTime).appendTo($messageHeader);

        const $messageContent = $('<div>', {
            class: 'message-content'
        }).appendTo($messageContainer);

        return { $messageContainer, $messageContent };
    }

    // Add a message to the chat display
    function addMessageToDisplay(role, content, timestamp) {
        const { $messageContainer, $messageContent } = createMessageElement(role, timestamp);

        // Add content if provided
        if (content) {
            $messageContent.html(renderMarkdown(content));
        }

        $chatMessagesContainer.append($messageContainer);

        // Scroll to the bottom of the container
        $chatMessagesContainer.scrollTop($chatMessagesContainer[0].scrollHeight);

        return { $messageContainer, $messageContent };
    }

    // Add a loading message to the chat display
    function addLoadingMessage(role) {
        const { $messageContainer, $messageContent } = createMessageElement(role);

        $messageContainer.addClass('loading');
        $messageContent.text('Thinking...');

        $chatMessagesContainer.append($messageContainer);
        $chatMessagesContainer.scrollTop($chatMessagesContainer[0].scrollHeight);

        return { $messageContainer, $messageContent };
    }

    // Update message content with typewriter effect - simplified version
    function typewriterEffect($messageContent, text) {
        const typingSpeed = 35; // ms per character

        // Clear the element initially
        $messageContent.empty();

        let formattedText = text;
        let index = 0;
        let htmlBuffer = '';
        let inTag = false;
        let tagBuffer = '';

        // Set placeholder text while typing
        $messageContent.html('<span class="typing-cursor">|</span>');

        function processNextChunk() {
            // Process 3 characters at a time for better performance
            for (let i = 0; i < 3; i++) {
                if (index >= formattedText.length) {
                    // Render the final result with proper markdown
                    $messageContent.html(renderMarkdown(text));

                    // Scroll to the bottom
                    $chatMessagesContainer.scrollTop($chatMessagesContainer[0].scrollHeight);
                    return;
                }

                const char = formattedText[index];

                htmlBuffer += char;
                index++;
            }

            // Update content with what we have so far - simple incremental approach
            $messageContent.text(htmlBuffer);
            $messageContent.append('<span class="typing-cursor">|</span>');

            // Scroll to the bottom change this is you want auto scroll enabled
            // $chatMessagesContainer.scrollTop($chatMessagesContainer[0].scrollHeight);

            // Process the next chunk
            setTimeout(processNextChunk, typingSpeed);
        }

        // Start processing
        processNextChunk();
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
            return;
        }

        // Add chat ID if we have one
        if (currentChatId) {
            formData.append('chatId', currentChatId);
        }

        formData.append('audio', audioBlob, 'recording.' + (audioBlob.type.split('/')[1] || 'webm'));

        try {
            $recordingStatus.text('Sending audio for transcription...');

            // Add user message with loading state first
            const userMessage = addLoadingMessage('user');

            // Add assistant message with loading state
            const assistantMessage = addLoadingMessage('assistant');

            // Send the request
            const response = await $.ajax({
                url: '/transcribe',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                timeout: 30000  // 30 seconds
            });

            // Check for errors
            if (response.error) {
                $recordingStatus.text(`Error: ${response.error}`);
                userMessage.$messageContainer.remove();
                assistantMessage.$messageContent.text(response.response || 'An error occurred. Please try again.');
                assistantMessage.$messageContainer.removeClass('loading');
                return;
            }

            // Update the user message with transcription
            if (response.transcription) {
                userMessage.$messageContent.html(renderMarkdown(response.transcription));
                userMessage.$messageContainer.removeClass('loading');
                $recordingStatus.text('Transcription complete');
            } else {
                userMessage.$messageContainer.remove();
                $recordingStatus.text('Could not transcribe audio');
            }

            // Update the assistant message with response
            if (response.response) {
                assistantMessage.$messageContainer.removeClass('loading');
                typewriterEffect(assistantMessage.$messageContent, response.response);
            } else {
                assistantMessage.$messageContent.text('No response available');
                assistantMessage.$messageContainer.removeClass('loading');
            }

            // Update chat ID
            if (response.chatId) {
                currentChatId = response.chatId;
                $currentChatInfo.text(`Conversation #${currentChatId}`);
            }
        } catch (error) {
            console.error('Error transcribing audio:', error);
            $recordingStatus.text(`Error: ${error.statusText || error.message || 'Failed to transcribe audio'}`);
        }
    }

    // Load chat messages for a specific chat
    async function loadChatHistory(chatId) {
        if (!chatId) return;

        try {
            $chatMessagesContainer.empty(); // Clear existing messages

            const response = await $.ajax({
                url: `/chats/${chatId}`,
                type: 'GET'
            });

            if (response && response.messages && response.messages.length > 0) {
                console.log("Loaded chat history:", response);

                // Update chat title
                $currentChatInfo.text(response.title || `Conversation #${chatId}`);

                // Display messages
                response.messages.forEach(message => {
                    addMessageToDisplay(message.role, message.content, message.createdAt);
                });
            }

            // Display the chat history container
            $chatHistoryContainer.show();

        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    // Load available chats
    async function loadChats() {
        try {
            const response = await $.ajax({
                url: '/chats',
                type: 'GET'
            });

            if (response && response.chats && response.chats.length > 0) {
                console.log("Loaded chats:", response);

                $chatHistoryList.empty(); // Clear existing list

                // Display chats
                response.chats.forEach(chat => {
                    const $chatItem = $('<div>', {
                        class: 'chat-item',
                        'data-id': chat.id
                    }).text(`${chat.title || `Chat #${chat.id}`} - ${formatDateTime(chat.updatedAt)}`);

                    $chatItem.on('click', () => {
                        currentChatId = chat.id;
                        loadChatHistory(chat.id);
                    });

                    $chatHistoryList.append($chatItem);
                });

                // Show the chat history container
                $chatHistoryContainer.show();
            } else {
                $chatHistoryList.html('<p>No previous conversations</p>');
            }
        } catch (error) {
            console.error('Error loading chats:', error);
            $chatHistoryList.html('<p>Error loading chat history</p>');
        }
    }

    // Start a new chat
    function startNewChat() {
        currentChatId = null;
        $currentChatInfo.text('New conversation');
        $chatMessagesContainer.empty();

        // Add a welcome message
        addMessageToDisplay('assistant', 'Hello! I\'m your voice assistant. You can speak to me by clicking the microphone button or type your message below.');
    }

    // Add a function to send text messages directly
    function sendTextMessage(message) {
        try {
            // Add user message with content
            addMessageToDisplay('user', message);

            // Add assistant message with loading state
            const assistantMessage = addLoadingMessage('assistant');

            // Send the request
            $.ajax({
                url: '/chat',
                type: 'POST',
                data: JSON.stringify({
                    message: message,
                    chatId: currentChatId
                }),
                contentType: 'application/json',
                success: function (response) {
                    // Update assistant response with typewriter effect
                    assistantMessage.$messageContainer.removeClass('loading');
                    typewriterEffect(assistantMessage.$messageContent, response.response);

                    // Update chat ID if provided
                    if (response.chatId && !currentChatId) {
                        currentChatId = response.chatId;
                        $currentChatInfo.text(`Conversation #${currentChatId}`);
                    }
                },
                error: function (xhr, status, error) {
                    console.error('Error sending text message:', error);
                    assistantMessage.$messageContent.text('An error occurred. Please try again.');
                    assistantMessage.$messageContainer.removeClass('loading');
                }
            });
        } catch (error) {
            console.error('Error sending text message:', error);
        }
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

    // Add text input functionality
    const $textInputForm = $('#textInputForm');
    const $userTextInput = $('#userTextInput');

    if ($textInputForm.length) {
        $textInputForm.on('submit', function(e) {
            e.preventDefault();
            const userText = $userTextInput.val().trim();
            if (userText) {
                sendTextMessage(userText);
                $userTextInput.val('');
            }
        });
    }

    // Initialize
    initRecorder();

    // Load available chats on startup
    loadChats();

    // Start with a welcome message
    startNewChat();
});