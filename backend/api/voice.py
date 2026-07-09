"""
Voice API routes — /stt and /tts

/stt  — Speech-to-Text: accepts an audio file upload, returns { text: "..." }
/tts  — Text-to-Speech: accepts { text: "..." }, returns MP3 audio bytes

Both routes delegate to VoiceProviderFactory. When VOICE_PROVIDER=webapi,
both endpoints return HTTP 501 (Not Implemented) because STT/TTS are
handled by the browser's Web Speech API.
"""
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from voice.factory import VoiceProviderFactory

router = APIRouter(tags=["voice"])
logger = logging.getLogger(__name__)


class TtsRequest(BaseModel):
    text: str


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Accept an audio file upload and return its transcript.

    Expected multipart field name: 'audio'
    Supported formats: webm, wav, mp4, ogg (whatever Deepgram accepts)

    Returns: { "text": "transcribed text" }
    """
    logger.info("[voice] /stt called — file=%s, content_type=%s", audio.filename, audio.content_type)

    try:
        provider = VoiceProviderFactory.create()
        audio_bytes = await audio.read()
        mime_type = audio.content_type or "audio/webm"
        transcript = provider.transcribe(audio_bytes, mime_type)
        return {"text": transcript}

    except NotImplementedError as e:
        logger.warning("[voice] /stt not available for current VOICE_PROVIDER: %s", e)
        raise HTTPException(
            status_code=501,
            detail="STT is not available server-side. Set VOICE_PROVIDER=deepgram to enable it.",
        )
    except Exception as e:
        logger.error("[voice] /stt error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Speech-to-text failed.")


@router.post("/tts")
async def text_to_speech(request: TtsRequest):
    """
    Accept a text payload and return synthesized MP3 audio bytes.

    Request body: { "text": "..." }
    Response: audio/mpeg binary stream
    """
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty.")

    logger.info("[voice] /tts called — text len=%d", len(request.text))

    try:
        provider = VoiceProviderFactory.create()
        audio_bytes = provider.synthesize(request.text)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=tts.mp3"},
        )

    except NotImplementedError as e:
        logger.warning("[voice] /tts not available for current VOICE_PROVIDER: %s", e)
        raise HTTPException(
            status_code=501,
            detail="TTS is not available server-side. Set VOICE_PROVIDER=deepgram to enable it.",
        )
    except Exception as e:
        logger.error("[voice] /tts error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Text-to-speech failed.")
