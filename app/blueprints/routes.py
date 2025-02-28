import os
from flask import render_template, request, jsonify, current_app
import mimetypes
from app.blueprints import bp
from app.services.openaiServices import transcribeAudioUsingOpenAI, generateResponse
from app.models.chat import Chat


@bp.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')


@bp.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response


# Add OPTIONS method handler for preflight requests
@bp.route('/transcribe', methods=['OPTIONS'])
def options_transcribe():
    return '', 204


@bp.route('/transcribe', methods=['POST'])
def transcribe():
    """Endpoint to transcribe audio from the microphone."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    # Get chat_id from form data if it exists
    chatId = request.form.get('chatId')
    if chatId:
        try:
            chatId = int(chatId)
        except ValueError:
            chatId = None

    audioFile = request.files['audio']

    # Get file info
    filename = audioFile.filename
    contentType = audioFile.content_type

    # Log file details for debugging
    current_app.logger.info(f"Received audio file: {filename}, Content-Type: {contentType}")

    # Check if the file is in a supported format
    ext = mimetypes.guess_extension(contentType) or '.webm'
    if ext.startswith('.'):
        ext = ext[1:]

    # Save the audio file temporarily
    tempFilename = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_audio.{ext}")
    audioFile.save(tempFilename)

    # Log file size
    fileSize = os.path.getsize(tempFilename)
    current_app.logger.info(f"Saved audio file: {tempFilename}, Size: {fileSize} bytes")

    try:
        # Check if the file is empty or too small
        if fileSize < 100:  # Arbitrary minimum size, adjust as needed
            return jsonify({
                "transcription": "",
                "response": "I couldn't hear anything. Please try speaking again.",
                "error": "Audio file is too small or empty."
            })

        transcription = transcribeAudioUsingOpenAI(tempFilename)

        # Only generate a response if there's text to respond to
        responseText = ""
        newChatId = None

        if transcription and transcription.strip():
            # Generate response
            responseText, newChatId = generateResponse(transcription, chatId)
        else:
            responseText = "Не разбирам това което казваш. Моля повтори съобщението."

        return jsonify({
            "transcription": transcription,
            "response": responseText,
            "chatId": newChatId,
            "file_info": {
                "filename": filename,
                "content_type": contentType,
                "size_bytes": fileSize
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error processing audio file: {str(e)}")
        return jsonify({
            "transcription": "",
            "response": "Sorry, there was an error processing your audio. Please try again.",
            "error": str(e)
        }), 500
    finally:
        # Clean up the temp file if it exists
        if os.path.exists(tempFilename):
            os.remove(tempFilename)


@bp.route('/chat', methods=['OPTIONS'])
def options_chat():
    return '', 204


@bp.route('/chat', methods=['POST'])
def chat():
    """Endpoint to chat with the OpenAI model directly using text."""
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    userMessage = data['message']
    chatId = data.get('chatId')

    try:
        # Generate response
        responseText, newChatId = generateResponse(userMessage, chatId)
        return jsonify({
            "response": responseText,
            "chatId": newChatId
        })
    except Exception as e:
        current_app.logger.error(f"Error generating chat response: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/chats', methods=['GET'])
def get_chats():
    """Get a list of all chats."""
    chats = Chat.query.order_by(Chat.updatedAt.desc()).all()
    return jsonify({
        "chats": [
            {
                "id": chat.id,
                "title": chat.title,
                "updatedAt": chat.updatedAt.isoformat('dd.mm.yyyy')
            }
            for chat in chats
        ]
    })


@bp.route('/chats/<int:chatId>', methods=['GET'])
def get_chat(chatId):
    """Get details of a specific chat."""
    chat = Chat.query.get_or_404(chatId)
    return jsonify(chat.to_dict())
