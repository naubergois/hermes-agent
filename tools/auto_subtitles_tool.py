"""Auto-subtitle generation tool using Whisper.

Generates subtitles from video audio using OpenAI's Whisper model.
Supports multiple languages and output formats (SRT, VTT, JSON).
"""

import json
import os
import tempfile
import base64
import subprocess
from typing import Optional

from tools.registry import registry


def check_requirements() -> bool:
    """Check if required dependencies are available."""
    try:
        import openai
        return True
    except ImportError:
        return False


def generate_subtitles(
    video_input: str = "",
    language: str = "auto",  # auto, en, pt, es, fr, de, etc.
    output_format: str = "srt",  # srt, vtt, json
    prompt: str = "",  # Optional context for Whisper
    task_id: str = None,
) -> str:
    """
    Generate subtitles from video using Whisper.
    
    Args:
        video_input: Base64-encoded video or file path
        language: Language code (auto-detect or specific)
        output_format: Output format (srt, vtt, json)
        prompt: Optional context prompt for Whisper
        task_id: Task ID for tracking
    
    Returns:
        JSON with success status and subtitle data
    """
    if not check_requirements():
        return json.dumps({
            "success": False,
            "error": "openai library not installed",
            "error_type": "dependency_error",
        })
    
    if not video_input:
        return json.dumps({
            "success": False,
            "error": "video_input is required",
            "error_type": "validation_error",
        })
    
    if output_format not in ["srt", "vtt", "json"]:
        return json.dumps({
            "success": False,
            "error": f"Unsupported output_format: {output_format}",
            "error_type": "validation_error",
        })
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return json.dumps({
            "success": False,
            "error": "OPENAI_API_KEY not set",
            "error_type": "auth_error",
        })
    
    try:
        from openai import OpenAI
        
        # Decode or load video
        if video_input.startswith("data:") or len(video_input) > 1000:
            if video_input.startswith("data:"):
                video_data = base64.b64decode(video_input.split(",")[1])
            else:
                video_data = base64.b64decode(video_input)
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_data)
                video_path = f.name
        else:
            video_path = video_input
        
        # Extract audio from video (ffmpeg)
        audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        audio_path = audio_file.name
        audio_file.close()
        
        cmd = ["ffmpeg", "-i", video_path, "-q:a", "9", "-n", audio_path]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": "Failed to extract audio from video",
                "error_type": "processing_error",
            })
        
        # Call Whisper API
        client = OpenAI(api_key=api_key)
        
        with open(audio_path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language=None if language == "auto" else language,
                prompt=prompt if prompt else None,
                response_format="verbose_json",
            )
        
        # Convert to requested format
        if output_format == "json":
            # Return raw Whisper response
            subtitles = json.dumps(transcript.model_dump(), indent=2)
        
        elif output_format == "srt":
            # Convert to SRT format
            subtitles = _convert_to_srt(transcript)
        
        elif output_format == "vtt":
            # Convert to VTT format
            subtitles = _convert_to_vtt(transcript)
        
        # Cleanup
        if os.path.exists(video_path) and video_path != video_input:
            os.unlink(video_path)
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        
        return json.dumps({
            "success": True,
            "subtitles": subtitles,
            "format": output_format,
            "language": transcript.language,
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "execution_error",
        })


def _convert_to_srt(transcript) -> str:
    """Convert Whisper transcript to SRT format."""
    srt_content = []
    
    if hasattr(transcript, 'segments'):
        for i, segment in enumerate(transcript.segments, 1):
            start = _ms_to_timestamp(segment.start * 1000)
            end = _ms_to_timestamp(segment.end * 1000)
            text = segment.text.strip()
            
            srt_content.append(f"{i}")
            srt_content.append(f"{start} --> {end}")
            srt_content.append(text)
            srt_content.append("")
    
    return "\n".join(srt_content)


def _convert_to_vtt(transcript) -> str:
    """Convert Whisper transcript to VTT format."""
    vtt_content = ["WEBVTT", ""]
    
    if hasattr(transcript, 'segments'):
        for segment in transcript.segments:
            start = _ms_to_timestamp(segment.start * 1000)
            end = _ms_to_timestamp(segment.end * 1000)
            text = segment.text.strip()
            
            vtt_content.append(f"{start} --> {end}")
            vtt_content.append(text)
            vtt_content.append("")
    
    return "\n".join(vtt_content)


def _ms_to_timestamp(ms: float) -> str:
    """Convert milliseconds to SRT/VTT timestamp."""
    hours = int(ms // 3_600_000)
    minutes = int((ms % 3_600_000) // 60_000)
    seconds = int((ms % 60_000) // 1000)
    millis = int(ms % 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


registry.register(
    name="generate_subtitles",
    toolset="video",
    schema={
        "name": "generate_subtitles",
        "description": "Generate subtitles from video using OpenAI Whisper. Supports multiple languages and output formats.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_input": {
                    "type": "string",
                    "description": "Base64-encoded video or file path",
                },
                "language": {
                    "type": "string",
                    "description": "Language code (auto, en, pt, es, fr, de, etc.)",
                    "default": "auto",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["srt", "vtt", "json"],
                    "description": "Output subtitle format",
                    "default": "srt",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional context prompt for Whisper to improve accuracy",
                },
            },
            "required": ["video_input"],
        },
    },
    handler=lambda args, **kw: generate_subtitles(
        video_input=args.get("video_input", ""),
        language=args.get("language", "auto"),
        output_format=args.get("output_format", "srt"),
        prompt=args.get("prompt", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=["OPENAI_API_KEY"],
)
