"""
API routes for the autonomous agent system.
"""


from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, AsyncGenerator
import asyncio
import json
from ..core.engine import engine
from ..llm.provider_factory import provider_factory

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    config: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    metrics: Dict[str, Any]


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint for the terminal UI.
    """
    try:
        # Update config BEFORE initializing engine if provided
        if request.config and request.config.get("api_key"):
            from ..core.config import config
            
            provider_name = request.config.get("provider", "nvidia")
            
            # Use apply_temporary_config to properly set API key in config + env vars
            config.apply_temporary_config(request.config)
            
            # Mark selected provider as default
            if provider_name in config.providers:
                config.providers[provider_name]['default'] = True
                # Mark others as non-default
                for name in config.providers:
                    if name != provider_name:
                        config.providers[name]['default'] = False
        
        # Initialize engine if not already running
        if not engine._running:
            await engine.initialize()
        elif request.config and request.config.get("api_key"):
            # If engine already running but new API key provided, 
            # reload providers WITHOUT calling config.reload() to preserve our API key
            from ..llm.client import llm_client
            llm_client.providers.clear()
            llm_client.default_provider = None
            provider_factory._initialized = False
            provider_factory.initialize()  # Not async - don't await
        
        # Execute the request through full autonomous agent system
        response = await engine.execute(request.message)
        
        # Get metrics
        metrics = engine.get_metrics()
        
        return ChatResponse(
            response=response,
            metrics=metrics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def status():
    """
    Get system status.
    """
    return {
        "system_state": engine.get_system_state(),
        "metrics": engine.get_metrics()
    }


@router.get("/config")
async def get_config():
    """
    Get current provider and model configuration for the UI.
    """
    from ..core.config import config

    return {
        "providers": config.get_all_providers(),
        "models": config.get_all_models(),
        "workflows": config.get_all_workflows()
    }


async def stream_response(query: str, config_data: Optional[Dict]) -> AsyncGenerator[str, None]:
    """
    Stream response from the agent system.
    Yields SSE formatted data.
    """
    try:
        # Update config if provided
        if config_data and config_data.get("api_key"):
            from ..core.config import config
            provider_name = config_data.get("provider", "nvidia")
            config.apply_temporary_config(config_data)
            if provider_name in config.providers:
                config.providers[provider_name]['default'] = True
                for name in config.providers:
                    if name != provider_name:
                        config.providers[name]['default'] = False
        
        # Initialize engine
        if not engine._running:
            await engine.initialize()
        elif config_data and config_data.get("api_key"):
            from ..llm.client import llm_client
            llm_client.providers.clear()
            llm_client.default_provider = None
            provider_factory._initialized = False
            provider_factory.initialize()
        
        # For simple queries, skip full pipeline and stream directly
        is_simple = len(query.strip()) < 30 and not any(word in query.lower() for word in ['analyze', 'research', 'compare', 'explain', 'elaborate', 'detail'])
        
        if is_simple:
            # Fast path for simple queries
            from ..llm.client import llm_client
            
            # Stream simple response
            system_prompt = "You are a helpful AI assistant. Respond briefly and directly. Maximum 2-3 lines."
            full_prompt = f"{system_prompt}\n\nUser: {query}\n\nAssistant:"
            
            # Generate response (non-streaming for now, but simulating streaming)
            response_text = await llm_client.generate(full_prompt)
            
            # Simulate streaming by yielding chunks
            words = response_text.split(' ')
            current_text = ""
            for word in words:
                current_text += word + " "
                yield f"data: {json.dumps({'content': current_text.strip()})}\n\n"
                await asyncio.sleep(0.03)  # Small delay for typing effect
            
            yield f"data: {json.dumps({'metrics': {'completed_nodes': 1, 'total_nodes': 1, 'total_duration_ms': 500}})}\n\n"
            yield "data: [DONE]\n\n"
        else:
            # Full pipeline for complex queries
            # First, let agents work (this blocks but we'll yield status)
            yield f"data: {json.dumps({'content': ''})}\n\n"
            
            # Execute full pipeline
            response = await engine.execute(query)
            
            # Stream the final response word by word
            words = response.split(' ')
            current_text = ""
            for word in words:
                current_text += word + " "
                yield f"data: {json.dumps({'content': current_text.strip()})}\n\n"
                await asyncio.sleep(0.02)
            
            # Send metrics at end
            metrics = engine.get_metrics()
            yield f"data: {json.dumps({'metrics': metrics})}\n\n"
            yield "data: [DONE]\n\n"
            
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/chat-stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint for real-time responses.
    """
    return StreamingResponse(
        stream_response(request.message, request.config),
        media_type="text/event-stream"
    )