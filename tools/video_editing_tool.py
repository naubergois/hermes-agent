"""Video editing tool for extending, trimming, and joining videos.

Supports common operations on generated videos:
- Extend: Add more frames/duration to a video
- Trim: Cut specific segments
- Join: Combine multiple videos
- Upscale: Increase resolution using AI
"""

import json
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

from tools.registry import registry


def check_requirements() -> bool:
    """Check if ffmpeg is available."""
    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    return result.returncode == 0


def video_edit(
    operation: str,  # "extend", "trim", "join", "upscale"
    video_input: str = "",  # base64 video or path
    video_input2: str = "",  # second video for join
    start_time: float = 0.0,  # for trim
    end_time: float = 0.0,  # for trim
    duration: int = 0,  # for extend (additional seconds)
    scale: str = "2x",  # for upscale (2x, 4x)
    task_id: str = None,
) -> str:
    """
    Edit videos with various operations.
    
    Operations:
    - extend: Add duration to existing video
    - trim: Cut specific time segment
    - join: Combine two videos
    - upscale: Increase resolution
    
    Args:
        operation: Type of operation
        video_input: Base64-encoded video or file path
        video_input2: Second video for join operation
        start_time: Start time for trim (seconds)
        end_time: End time for trim (seconds)
        duration: Additional duration for extend (seconds)
        scale: Upscale factor (2x or 4x)
        task_id: Task ID for tracking
    
    Returns:
        JSON with success status and output video/path
    """
    if not check_requirements():
        return json.dumps({
            "success": False,
            "error": "ffmpeg not installed",
            "error_type": "dependency_error",
        })
    
    if operation not in ["extend", "trim", "join", "upscale"]:
        return json.dumps({
            "success": False,
            "error": f"Unknown operation: {operation}",
            "error_type": "validation_error",
        })
    
    if not video_input:
        return json.dumps({
            "success": False,
            "error": "video_input is required",
            "error_type": "validation_error",
        })
    
    try:
        # Decode video input if base64
        if video_input.startswith("data:") or len(video_input) > 1000:
            import base64
            if video_input.startswith("data:"):
                video_data = base64.b64decode(video_input.split(",")[1])
            else:
                video_data = base64.b64decode(video_input)
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_data)
                input_path = f.name
        else:
            input_path = video_input
        
        # Create output file
        output_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = output_file.name
        output_file.close()
        
        # Execute operation
        if operation == "trim":
            if not end_time:
                return json.dumps({
                    "success": False,
                    "error": "end_time required for trim operation",
                    "error_type": "validation_error",
                })
            
            cmd = [
                "ffmpeg", "-i", input_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c", "copy",
                "-y", output_path
            ]
        
        elif operation == "extend":
            if duration <= 0:
                return json.dumps({
                    "success": False,
                    "error": "duration > 0 required for extend operation",
                    "error_type": "validation_error",
                })
            
            # Loop video to extend duration
            cmd = [
                "ffmpeg", "-stream_loop", str(max(1, duration // 4)),
                "-i", input_path,
                "-c", "copy",
                "-t", str(duration + 4),  # Original + additional
                "-y", output_path
            ]
        
        elif operation == "join":
            if not video_input2:
                return json.dumps({
                    "success": False,
                    "error": "video_input2 required for join operation",
                    "error_type": "validation_error",
                })
            
            # Prepare second video
            if video_input2.startswith("data:") or len(video_input2) > 1000:
                import base64
                if video_input2.startswith("data:"):
                    video_data2 = base64.b64decode(video_input2.split(",")[1])
                else:
                    video_data2 = base64.b64decode(video_input2)
                
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                    f.write(video_data2)
                    input_path2 = f.name
            else:
                input_path2 = video_input2
            
            # Create concat file
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False)
            concat_file.write(f"file '{input_path}'\n")
            concat_file.write(f"file '{input_path2}'\n")
            concat_file.close()
            
            cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", concat_file.name,
                "-c", "copy",
                "-y", output_path
            ]
        
        elif operation == "upscale":
            # Simple 2x/4x scaling using FFmpeg
            scale_factor = int(scale.rstrip('x'))
            
            cmd = [
                "ffmpeg", "-i", input_path,
                "-vf", f"scale=iw*{scale_factor}:ih*{scale_factor}:flags=lanczos",
                "-y", output_path
            ]
        
        # Run ffmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"FFmpeg error: {result.stderr}",
                "error_type": "processing_error",
            })
        
        # Read output video
        import base64
        with open(output_path, 'rb') as f:
            output_data = base64.b64encode(f.read()).decode()
        
        # Cleanup
        if os.path.exists(input_path) and input_path != video_input:
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
        
        return json.dumps({
            "success": True,
            "video": output_data,
            "operation": operation,
            "output_path": output_path,
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "execution_error",
        })


registry.register(
    name="video_edit",
    toolset="video",
    schema={
        "name": "video_edit",
        "description": "Edit videos: extend duration, trim segments, join multiple videos, or upscale resolution",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["extend", "trim", "join", "upscale"],
                    "description": "Type of video operation",
                },
                "video_input": {
                    "type": "string",
                    "description": "Base64-encoded video or file path",
                },
                "video_input2": {
                    "type": "string",
                    "description": "Second video for join operation",
                },
                "start_time": {
                    "type": "number",
                    "description": "Start time in seconds for trim operation",
                },
                "end_time": {
                    "type": "number",
                    "description": "End time in seconds for trim operation",
                },
                "duration": {
                    "type": "integer",
                    "description": "Additional duration in seconds for extend operation",
                },
                "scale": {
                    "type": "string",
                    "enum": ["2x", "4x"],
                    "description": "Upscale factor (2x or 4x)",
                },
            },
            "required": ["operation", "video_input"],
        },
    },
    handler=lambda args, **kw: video_edit(
        operation=args.get("operation", ""),
        video_input=args.get("video_input", ""),
        video_input2=args.get("video_input2", ""),
        start_time=float(args.get("start_time", 0)),
        end_time=float(args.get("end_time", 0)),
        duration=int(args.get("duration", 0)),
        scale=args.get("scale", "2x"),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=[],
)
