import os
import openai
from flask import current_app
from pydub import AudioSegment
from app.models.chat import Chat
from app.models.message import Message
from app.extensions import db

openai.api_key = os.environ.get('OPENAI_API_KEY')

def transcribeAudioUsingOpenAI(audioFilePath):
    """
        Transcribe audio using OpenAI's Whisper API.

        Args:
            audio_file_path (str): Path to the audio file to transcribe

        Returns:
            str: Transcribed text
    """

    try:
        if not openai.api_key:
            raise ValueError("OpenAI API key not found")

        if not os.path.isfile(audioFilePath):
            raise FileNotFoundError(f"Audio file not found at {audioFilePath}")

        fileSize = os.path.getsize(audioFilePath)
        fileExt = os.path.splitext(audioFilePath)[1].lower()
        current_app.logger.info(f"Original audio file: {audioFilePath}, Size: {fileSize} bytes, Format: {fileExt}")

        # Convert to MP3
        convertedFilePath = audioFilePath.replace(fileExt, '.mp3')
        current_app.logger.info(f"Converting audio from {fileExt} to .mp3")

        try:
            # Load the audio file
            audio = AudioSegment.from_file(audioFilePath)

            # Export as MP3
            audio.export(convertedFilePath, format="mp3")

            # Use the converted file path for transcription
            audioFilePath = convertedFilePath
            current_app.logger.info(
                f"Converted audio file: {audioFilePath}, Size: {os.path.getsize(audioFilePath)} bytes")
        except Exception as e:
            current_app.logger.error(f"Error converting audio: {str(e)}")
            raise ValueError(f"Could not convert audio format: {str(e)}")

        with open(audioFilePath, 'rb') as audioFile:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audioFile,
                language="bg"
            )

        text = response.text
        current_app.logger.info(f"Transcription successful: {text[:100]}...")
        return text
    except Exception as e:
        current_app.logger.error(f"Error transcribing audio: {str(e)}")

        # Clean up the converted file if it was created
        if 'convertedFilePath' in locals() and convertedFilePath and os.path.exists(convertedFilePath):
            os.remove(convertedFilePath)

        return

def generateResponse(userMessage, chatId=None):
    """
        Generate a response using OpenAI's GPT API and store in chat history.

    Args:
        user_message (str): The user's message to respond to
        chat_id (int, optional): The ID of an existing chat to continue, or None to create a new chat

    Returns:
        tuple: (response_text, chat_id) - The generated response and the chat ID
    """

    try:
        # Check if API key is configured
        if not openai.api_key:
            raise ValueError("OpenAI API key not found")

        # Get or create chat
        chat = None
        if chatId:
            chat = Chat.query.get(chatId)

        if not chat:
            # Create a new chat
            try:
                chat = Chat(title=userMessage[:50] + "..." if len(userMessage) > 50 else userMessage)
                db.session.add(chat)
                db.session.commit()
                current_app.logger.info(f"Created new chat with ID {chat.id}")
            except Exception as e:
                current_app.logger.error(f"Error creating chat: {str(e)}")
                db.session.rollback()
                raise ValueError(f"Could not create chat: {str(e)}")
        try:
            # Add user message to chat history
            userMsg = Message(chatId=chat.id, role="user", content=userMessage)
            db.session.add(userMsg)
            db.session.commit()

        except Exception as e:
            current_app.logger.error(f"Error adding user message to chat: {str(e)}")
            db.session.rollback()
            raise ValueError(f"Could not add user message to chat: {str(e)}")

        # Get chat history for context (limited to last 10 messages)
        chatMessages = Message.query.filter_by(chatId=chat.id).order_by(Message.createdAt.asc()).limit(10).all()

        # Format messages for OpenAI
        messages = [{"role": "system",
                     "content": "You are a great knitwear production assistant that responds"
                                  "to voice commands and can analyse production stats when have access."},]
        for msg in chatMessages:
            messages.append({"role": msg.role, "content": msg.content})

        # Log the conversation context
        current_app.logger.info(
            f"Generating response for chat {chat.id} with {len(messages) - 1} previous messages")

        # Generate a response using OpenAI's GPT-3 API'
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        responseText = response.choices[0].message.content
        current_app.logger.info(f"Generated response: {responseText[:100]}...")

        assistantMsg = Message(chatId=chat.id, role="assistant", content=responseText)
        try:
            db.session.add(assistantMsg)
            # Update chat timestamp
            chat.updatedAt = db.func.now()
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error adding assistant message to chat: {str(e)}")
            db.session.rollback()
            raise ValueError(f"Could not add assistant message to chat: {str(e)}")

        current_app.logger.info(f"Response generated for chat {chat.id}: {responseText[:100]}...")
        return responseText, chat.id

    except Exception as e:
        current_app.logger.error(f"Error generating response: {str(e)}")
        raise

