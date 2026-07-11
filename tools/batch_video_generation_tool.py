"""Batch video generation tool for parallel video generation.

Generates multiple video variations in parallel using delegation.
Useful for creating variations with different prompts, styles, or parameters.
"""

import json
import asyncio
from typing import List, Dict, Any

from tools.registry import registry


def batch_video_generate(
    prompts: List[str] = None,
    variations: int = 1,
    provider: str = "",
    model: str = "",
    duration: int = 4,
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    parallel_jobs: int = 3,
    task_id: str = None,
) -> str:
    """
    Generate multiple videos in parallel using delegation.
    
    Args:
        prompts: List of prompts to generate (or single prompt to create variations)
        variations: Number of variations to generate per prompt
        provider: Video generation provider (google, runway, luma, etc.)
        model: Model to use for generation
        duration: Video duration in seconds
        resolution: Output resolution (480p, 720p, 1080p, etc.)
        aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1, etc.)
        parallel_jobs: Max parallel generation jobs (default: 3)
        task_id: Task ID for tracking
    
    Returns:
        JSON with success status and list of generated videos
    """
    
    if not prompts:
        return json.dumps({
            "success": False,
            "error": "prompts list is required",
            "error_type": "validation_error",
        })
    
    if variations < 1:
        return json.dumps({
            "success": False,
            "error": "variations must be >= 1",
            "error_type": "validation_error",
        })
    
    if parallel_jobs < 1 or parallel_jobs > 10:
        parallel_jobs = min(10, max(1, parallel_jobs))
    
    try:
        from tools.delegate_tool import delegate_task
        
        # Build list of generation tasks
        tasks = []
        for prompt in prompts:
            for i in range(variations):
                task_goal = f"Generate video from prompt (variation {i+1}/{variations}): {prompt}"
                
                context = f"""
                Requirements:
                - Provider: {provider if provider else 'auto-select'}
                - Model: {model if model else 'default'}
                - Duration: {duration}s
                - Resolution: {resolution}
                - Aspect Ratio: {aspect_ratio}
                - Original Prompt: {prompt}
                """
                
                tasks.append({
                    "goal": task_goal,
                    "context": context,
                })
        
        # Delegate batch tasks
        results = delegate_task(
            tasks=tasks,
            role="leaf",
            max_concurrent=parallel_jobs,
            timeout_seconds=600,
        )
        
        # Parse results
        videos = []
        errors = []
        
        if isinstance(results, dict) and "tasks" in results:
            for i, result in enumerate(results["tasks"]):
                if result.get("success"):
                    videos.append({
                        "index": i,
                        "prompt": prompts[i // variations],
                        "variation": (i % variations) + 1,
                        "video": result.get("output", ""),
                    })
                else:
                    errors.append({
                        "index": i,
                        "prompt": prompts[i // variations],
                        "error": result.get("error", "Unknown error"),
                    })
        
        return json.dumps({
            "success": len(videos) > 0,
            "videos": videos,
            "errors": errors,
            "total_requested": len(tasks),
            "total_generated": len(videos),
            "total_failed": len(errors),
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "execution_error",
        })


registry.register(
    name="batch_video_generate",
    toolset="video",
    schema={
        "name": "batch_video_generate",
        "description": "Generate multiple video variations in parallel. Useful for creating content variations with different prompts or styles.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of prompts to generate (can be a single prompt)",
                },
                "variations": {
                    "type": "integer",
                    "description": "Number of variations per prompt (default: 1)",
                    "default": 1,
                },
                "provider": {
                    "type": "string",
                    "enum": ["google", "runway", "luma", "openai", "fal", "xai", "pika"],
                    "description": "Video generation provider (auto-select if not specified)",
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (provider-specific)",
                },
                "duration": {
                    "type": "integer",
                    "description": "Video duration in seconds",
                    "default": 4,
                },
                "resolution": {
                    "type": "string",
                    "enum": ["480p", "720p", "1080p", "1440p"],
                    "description": "Output resolution",
                    "default": "1080p",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                    "description": "Video aspect ratio",
                    "default": "16:9",
                },
                "parallel_jobs": {
                    "type": "integer",
                    "description": "Max parallel generation jobs (1-10)",
                    "default": 3,
                },
            },
            "required": ["prompts"],
        },
    },
    handler=lambda args, **kw: batch_video_generate(
        prompts=args.get("prompts", []),
        variations=int(args.get("variations", 1)),
        provider=args.get("provider", ""),
        model=args.get("model", ""),
        duration=int(args.get("duration", 4)),
        resolution=args.get("resolution", "1080p"),
        aspect_ratio=args.get("aspect_ratio", "16:9"),
        parallel_jobs=int(args.get("parallel_jobs", 3)),
        task_id=kw.get("task_id"),
    ),
    check_fn=lambda: True,
    requires_env=[],
)
