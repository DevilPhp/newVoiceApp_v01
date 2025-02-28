$(document).ready(function () {
    // DOM elements
    const $recordButton = $('#recordButton');
    const $recordingStatus = $('#recordingStatus');
    const $transcript = $('#transcript');
    const $assistantResponse = $('#assistantResponse');
    const $currentChatInfo = $('#currentChatInfo');
    const $newChatBtn = $('#newChatBtn');
    const $chatHistoryContainer = $('#chatHistoryContainer');
    const $chatHistoryList = $('#chatHistoryList');
    const $chatMessagesContainer = $('#chatMessagesContainer');

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

    // Add a message to the chat display
    function addMessageToDisplay(role, content, timestamp) {
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
        }).html(renderMarkdown(content)).appendTo($messageContainer);

        $chatMessagesContainer.append($messageContainer);

        // Scroll to the bottom of the container
        $chatMessagesContainer.scrollTop($chatMessagesContainer[0].scrollHeight);
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

            // Show loading animation
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

            // Remove loading animation
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

                // Add user message to chat display
                addMessageToDisplay('user', response.transcription);
            } else {
                $transcript.text('No transcription available');
                $recordingStatus.text('Could not transcribe audio');
            }

            // Display the assistant's response with typewriter effect
            if (response.response) {
                // Use the typewriter effect for a more dynamic response
                typewriterEffect($assistantResponse, response.response, true);

                // Also add to the chat messages
                addMessageToDisplay('assistant', response.response);
            } else {
                $assistantResponse.text('No response from assistant');
            }

            // Update chat ID
            if (response.chatId) {
                currentChatId = response.chatId;
                $currentChatInfo.text(`Conversation #${currentChatId}`);

                // Load the chat history if this is a new chat ID
                loadChatHistory(currentChatId);
            }
        } catch (error) {
            console.error('Error transcribing audio:', error);
            $recordingStatus.text(`Error: ${error.statusText || error.message || 'Failed to transcribe audio'}`);
            $assistantResponse.removeClass('loading');
            $assistantResponse.text('An error occurred. Please try again.');
        }
    }

    // Typewriter effect for responses
    function typewriterEffect($element, text, parseMarkdown = false) {
        const typingSpeed = 10; // ms per character
        const fullHtml = parseMarkdown ? renderMarkdown(text) : text;

        // First, clear the element
        $element.empty();

        // Create a temporary div to parse the HTML
        const $tempDiv = $('<div>').html(fullHtml);
        const nodes = $tempDiv[0].childNodes;

        let currentNodeIndex = 0;
        let currentTextIndex = 0;

        function typeNextChar() {
            // If we've processed all nodes, we're done
            if (currentNodeIndex >= nodes.length) {
                return;
            }

            const currentNode = nodes[currentNodeIndex];

            // Handle text nodes
            if (currentNode.nodeType === Node.TEXT_NODE) {
                const nodeText = currentNode.textContent;

                if (currentTextIndex < nodeText.length) {
                    // Keep adding one character at a time
                    const displayText = nodeText.substring(0, currentTextIndex + 1);

                    // Replace or add the text node
                    if ($element.contents().length > 0 && $element.contents().last()[0].nodeType === Node.TEXT_NODE) {
                        $element.contents().last()[0].textContent = displayText;
                    } else {
                        $element.append(document.createTextNode(displayText));
                    }

                    currentTextIndex++;
                    setTimeout(typeNextChar, typingSpeed);
                } else {
                    // Move to the next node
                    currentNodeIndex++;
                    currentTextIndex = 0;
                    setTimeout(typeNextChar, typingSpeed);
                }
            }
            // Handle element nodes
            else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                // Clone the node without its children
                const $newNode = $(currentNode.cloneNode(false));
                $element.append($newNode);

                // Process children recursively (if any)
                if (currentNode.childNodes.length > 0) {
                    // Save current state
                    const parentNodeIndex = currentNodeIndex;
                    const parentElement = $element;

                    // Set new state
                    $element = $newNode;
                    const childNodes = Array.from(currentNode.childNodes);
                    nodes.splice(currentNodeIndex + 1, 0, ...childNodes);

                    // Move to first child
                    currentNodeIndex++;
                    currentTextIndex = 0;
                    setTimeout(typeNextChar, typingSpeed);
                } else {
                    // No children, move to next node
                    currentNodeIndex++;
                    currentTextIndex = 0;
                    setTimeout(typeNextChar, typingSpeed);
                }
            } else {
                // Skip other node types
                currentNodeIndex++;
                currentTextIndex = 0;
                setTimeout(typeNextChar, typingSpeed);
            }
        }

        // Start the typewriter effect
        typeNextChar();
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
                    addMessageToDisplay(message.role, message.content, message.createdАt);
                });

                // Show the last assistant response in the assistant response area
                const lastAssistantMessage = response.messages
                    .filter(msg => msg.role === 'assistant')
                    .pop();

                if (lastAssistantMessage) {
                    $assistantResponse.html(renderMarkdown(lastAssistantMessage.content));
                }

                // Show the last user message in the transcript area
                const lastUserMessage = response.messages
                    .filter(msg => msg.role === 'user')
                    .pop();

                if (lastUserMessage) {
                    $transcript.text(lastUserMessage.content);
                }
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
        $transcript.text('Your spoken words will appear here...');
        $assistantResponse.text('Waiting for your voice command...');
        $chatMessagesContainer.empty();
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

    // Add a function to send text messages directly
    function sendTextMessage(message) {
        try {
            // Add to display immediately
            addMessageToDisplay('user', message);

            // Update transcript
            $transcript.text(message);

            // Show loading animation
            $assistantResponse.text('');
            $assistantResponse.addClass('loading');

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
                    $assistantResponse.removeClass('loading');

                    // Update assistant response with typewriter effect
                    typewriterEffect($assistantResponse, response.response, true);

                    // Also add to the chat messages display
                    addMessageToDisplay('assistant', response.response);

                    // Update chat ID if provided
                    if (response.chatId) {
                        currentChatId = response.chatId;
                        $currentChatInfo.text(`Conversation #${currentChatId}`);

                        // Reload chat history
                        loadChatHistory(currentChatId);
                    }
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

    // Add text input functionality (optional)
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
});