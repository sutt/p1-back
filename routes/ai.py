"""
AI Chat Endpoint - Basic Proof of Concept

This module provides the /api/ai/chat endpoint for natural language canvas manipulation.
Frontend sends user message + canvas state, backend calls OpenAI, validates commands,
and returns structured commands for frontend execution.

LIMITATIONS:
- Basic PoC implementation, not production-ready
- In-memory rate limiting (resets on server restart)
- No Redis caching or persistent rate limit tracking
- Limited error recovery - only retries validation once
- No streaming responses (full response after AI completes)
- No conversation history/context beyond single request

MANUAL INTERVENTIONS REQUIRED:
- Add OPENAI_API_KEY to .env file (get from OpenAI dashboard)
- Optionally set OPENAI_MODEL in .env (defaults to gpt-3.5-turbo)
- Optionally set AI_RATE_LIMIT_PER_USER (defaults to 10 requests/min)
- Consider enabling authentication by uncommenting Depends(get_current_user)
- For production: Replace in-memory rate limiting with Redis
"""

import os
import time
from typing import List, Optional, Dict, Any
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database import get_db
# Uncomment for authentication:
# from auth import get_current_user, User

# AI_DEBUG environment variable controls debug output
AI_DEBUG = os.getenv("AI_DEBUG", "false").lower() == "true"


def ai_debug_print(message: str):
    """Print debug messages if AI_DEBUG is enabled."""
    if AI_DEBUG:
        print(f"[AI_DEBUG] {message}")


router = APIRouter(prefix="/api/ai", tags=["AI"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CanvasViewport(BaseModel):
    """Canvas viewport information (zoom and pan)."""
    zoom: float = 1.0
    pan: Dict[str, float] = {"x": 0, "y": 0}


class ShapeModel(BaseModel):
    """Shape model matching the existing Shape model in main.py."""
    id: str
    type: str
    x: int
    y: int
    width: Optional[int] = None
    height: Optional[int] = None
    radius: Optional[int] = None
    text: Optional[str] = None
    selectedBy: List[str] = []


class AICanvasState(BaseModel):
    """Canvas state sent from frontend."""
    shapes: List[ShapeModel]
    viewport: CanvasViewport


class AIChatRequest(BaseModel):
    """Request model for AI chat endpoint."""
    user: str = Field(..., description="Username of the requester")
    message: str = Field(..., max_length=500, description="User's natural language command")
    canvasState: AICanvasState
    model: Optional[str] = Field(None, description="The AI model to use for the request")


class AICommand(BaseModel):
    """Structured command returned by AI for frontend execution."""
    action: str = Field(..., description="Command type (createShape, moveShape, etc.)")
    params: Dict[str, Any] = Field(..., description="Command parameters")


class AIChatResponse(BaseModel):
    """Response model for AI chat endpoint."""
    message: str = Field(..., description="AI assistant's text response")
    commands: List[AICommand] = Field(default_factory=list, description="Structured commands to execute")
    reasoning: Optional[str] = Field(None, description="Optional explanation of AI logic")


class AIChatErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[Any] = Field(None, description="Additional debug information")


# ============================================================================
# Rate Limiting (In-Memory - Basic PoC)
# ============================================================================

# LIMITATION: In-memory rate limit tracker resets on server restart
# TODO: For production, replace with Redis-based rate limiting
rate_limit_tracker: Dict[str, list] = defaultdict(list)

AI_RATE_LIMIT_PER_USER = int(os.getenv("AI_RATE_LIMIT_PER_USER", 10))
RATE_LIMIT_WINDOW_SECONDS = 60


async def check_rate_limit(username: str) -> bool:
    """
    Check if user has exceeded rate limit.

    LIMITATION: In-memory only, not distributed across multiple servers

    Returns:
        True if request is allowed, False if rate limit exceeded
    """
    current_time = time.time()

    ai_debug_print(f"Checking rate limit for user: {username}")

    # Get user's recent requests
    user_requests = rate_limit_tracker[username]

    # Remove requests outside the time window
    user_requests[:] = [
        req_time for req_time in user_requests
        if current_time - req_time < RATE_LIMIT_WINDOW_SECONDS
    ]

    ai_debug_print(f"User {username} has {len(user_requests)} requests in last {RATE_LIMIT_WINDOW_SECONDS}s")

    # Check if limit exceeded
    if len(user_requests) >= AI_RATE_LIMIT_PER_USER:
        ai_debug_print(f"Rate limit exceeded for user: {username}")
        return False

    # Add current request
    user_requests.append(current_time)
    ai_debug_print(f"Rate limit check passed for user: {username}")
    return True


# ============================================================================
# Main AI Chat Endpoint
# ============================================================================

@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    # MANUAL INTERVENTION: Uncomment for production authentication
    # current_user: User = Depends(get_current_user)
):
    """
    Process natural language commands for canvas manipulation.

    Flow:
    1. Validate input (message length, rate limits)
    2. Call OpenAI with function calling
    3. Parse and validate AI-generated commands
    4. Return commands for frontend execution

    LIMITATIONS:
    - No authentication in PoC (uncomment current_user for production)
    - Single retry on validation failure (not iterative refinement)
    - No conversation history tracking
    - Commands are validated but not executed by backend
    - Frontend must handle command execution and sync

    Args:
        request: AI chat request with user message and canvas state
        db: Database session

    Returns:
        AIChatResponse with AI message and structured commands

    Raises:
        HTTPException: On rate limit exceeded or processing errors
    """
    ai_debug_print(f"=== AI Chat Request ===")
    ai_debug_print(f"User: {request.user}")
    ai_debug_print(f"Message: {request.message}")
    ai_debug_print(f"Canvas state: {len(request.canvasState.shapes)} shapes")

    # Rate limiting check
    if not await check_rate_limit(request.user):
        ai_debug_print(f"Rate limit exceeded for user: {request.user}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {AI_RATE_LIMIT_PER_USER} requests per minute."
        )

    # Import services here to avoid circular imports
    # LIMITATION: Services must be in services/ directory
    try:
        from services.openai_service import OpenAIService
        from services.ai_validator import AIValidator
    except ImportError as e:
        ai_debug_print(f"Failed to import services: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI services not available: {str(e)}"
        )

    # Initialize services
    ai_debug_print("Initializing OpenAI service and validator")
    try:
        openai_service = OpenAIService()
        validator = AIValidator(db, request.user, request.canvasState)
    except Exception as e:
        ai_debug_print(f"Failed to initialize services: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize AI services: {str(e)}"
        )

    # Determine which model to use
    model_to_use = openai_service.default_model
    if request.model:
        if request.model in openai_service.allowed_models:
            model_to_use = request.model
            ai_debug_print(f"Using client requested model: {model_to_use}")
        else:
            ai_debug_print(f"Requested model '{request.model}' not in allowed models {openai_service.allowed_models}. Falling back to default: {model_to_use}")
    else:
        ai_debug_print(f"No model requested by client. Using default model: {model_to_use}")

    try:
        # Call OpenAI
        ai_debug_print("Calling OpenAI API...")
        ai_response = await openai_service.process_command(
            user_message=request.message,
            canvas_state=request.canvasState,
            username=request.user,
            model=model_to_use
        )

        ai_debug_print(f"OpenAI returned {len(ai_response.get('commands', []))} commands")

        # Validate all commands
        validated_commands = []
        validation_errors = []

        for idx, cmd in enumerate(ai_response.get("commands", [])):
            ai_debug_print(f"Validating command {idx + 1}: {cmd['action']}")
            is_valid, error_msg = await validator.validate_command(cmd)
            if is_valid:
                validated_commands.append(AICommand(**cmd))
                ai_debug_print(f"Command {idx + 1} validated successfully")
            else:
                validation_errors.append(error_msg)
                ai_debug_print(f"Command {idx + 1} validation failed: {error_msg}")

        # LIMITATION: Only retries validation once if all commands fail
        # TODO: Implement iterative refinement with conversation history
        if validation_errors and not validated_commands:
            ai_debug_print("All commands failed validation, asking AI to revise...")
            ai_response = await openai_service.handle_validation_errors(
                original_message=request.message,
                errors=validation_errors,
                canvas_state=request.canvasState,
                model=model_to_use
            )

            # Re-validate
            for cmd in ai_response.get("commands", []):
                is_valid, error_msg = await validator.validate_command(cmd)
                if is_valid:
                    validated_commands.append(AICommand(**cmd))

        ai_debug_print(f"Final validated commands: {len(validated_commands)}")

        response = AIChatResponse(
            message=ai_response.get("message", "I've processed your request."),
            commands=validated_commands,
            reasoning=ai_response.get("reasoning")
        )

        ai_debug_print(f"=== AI Chat Response ===")
        ai_debug_print(f"Message: {response.message}")
        ai_debug_print(f"Commands: {len(response.commands)}")

        return response

    except Exception as e:
        # Log error for monitoring
        ai_debug_print(f"AI chat error for user {request.user}: {str(e)}")
        print(f"AI chat error for user {request.user}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(e)}"
        )
