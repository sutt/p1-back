# Backend plan

## Executive Summary

This section outlines the backend architecture for the AI-powered chat feature that enables natural language canvas manipulation. The backend will handle OpenAI API calls, interpret commands via function calling, validate operations against collaboration rules, and return structured commands to the frontend for execution.

## Architecture Overview

### Design Philosophy: Thin Backend, Smart AI, Rich Frontend

**Decision:** Backend acts as a **stateless AI proxy + validator** rather than a command executor.

**Flow:**
1. Frontend sends: user message + current canvas state
2. Backend calls OpenAI with function calling
3. OpenAI returns structured commands
4. Backend validates commands (shape availability, bounds checking)
5. Backend returns commands to frontend
6. **Frontend executes commands** (creates/moves shapes)
7. Frontend syncs via existing `POST /api/shapes` endpoint

**Rationale:**
- **Leverage existing architecture:** Frontend already has shape manipulation logic
- **Minimize backend changes:** Reuse existing sync mechanism (`POST /api/shapes`)
- **Keep frontend responsive:** Optimistic updates, no round-trip for execution
- **Simplify testing:** Command validation can be unit tested independently
- **Match collaboration model:** Frontend owns canvas state, backend persists

---

## Backend Components

### 1. New API Endpoint: `POST /api/ai/chat`

**Location:** `routes/ai.py` (new file)

**Purpose:** Proxy AI requests to OpenAI and validate responses

**Request Model:**

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CanvasViewport(BaseModel):
    zoom: float = 1.0
    pan: Dict[str, float] = {"x": 0, "y": 0}

class AICanvasState(BaseModel):
    shapes: List[ShapeModel]  # Reuse existing ShapeModel from main.py
    viewport: CanvasViewport

class AIChatRequest(BaseModel):
    user: str = Field(..., description="Username of the requester")
    message: str = Field(..., max_length=500, description="User's natural language command")
    canvasState: AICanvasState
```

**Response Models:**

```python
class AICommand(BaseModel):
    action: str = Field(..., description="Command type (createShape, moveShape, etc.)")
    params: Dict[str, Any] = Field(..., description="Command parameters")

class AIChatResponse(BaseModel):
    message: str = Field(..., description="AI assistant's text response")
    commands: List[AICommand] = Field(default_factory=list, description="Structured commands to execute")
    reasoning: Optional[str] = Field(None, description="Optional explanation of AI logic")

class AIChatErrorResponse(BaseModel):
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[Any] = Field(None, description="Additional debug information")
```

**Endpoint Implementation:**

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.openai_service import OpenAIService
from services.ai_validator import AIValidator
from auth import get_current_user  # Optional: for authentication

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: str = Depends(get_current_user)  # TODO: Enable for production
):
    """
    Process natural language commands for canvas manipulation.

    Flow:
    1. Validate input (message length, rate limits)
    2. Call OpenAI with function calling
    3. Parse and validate AI-generated commands
    4. Return commands for frontend execution
    """

    # Rate limiting check
    if not await check_rate_limit(request.user):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {AI_RATE_LIMIT_PER_USER} requests per minute."
        )

    # Initialize services
    openai_service = OpenAIService()
    validator = AIValidator(db, request.user, request.canvasState)

    try:
        # Call OpenAI
        ai_response = await openai_service.process_command(
            user_message=request.message,
            canvas_state=request.canvasState,
            username=request.user
        )

        # Validate all commands
        validated_commands = []
        validation_errors = []

        for cmd in ai_response.commands:
            is_valid, error_msg = await validator.validate_command(cmd)
            if is_valid:
                validated_commands.append(cmd)
            else:
                validation_errors.append(error_msg)

        # If validation failed, ask AI to revise
        if validation_errors and not validated_commands:
            ai_response = await openai_service.handle_validation_errors(
                original_message=request.message,
                errors=validation_errors,
                canvas_state=request.canvasState
            )
            # Re-validate
            for cmd in ai_response.commands:
                is_valid, error_msg = await validator.validate_command(cmd)
                if is_valid:
                    validated_commands.append(cmd)

        return AIChatResponse(
            message=ai_response.message,
            commands=validated_commands,
            reasoning=ai_response.reasoning
        )

    except Exception as e:
        # Log error for monitoring
        print(f"AI chat error for user {request.user}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(e)}"
        )
```

---

### 2. OpenAI Service: `services/openai_service.py`

**Purpose:** Handle all OpenAI API interactions with function calling

**Key Components:**

```python
import os
from openai import AsyncOpenAI
from typing import List, Dict, Any
import json

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.tools = self._define_tools()
        self.system_prompt = self._get_system_prompt()

    def _define_tools(self) -> List[Dict]:
        """Define OpenAI function calling tool schema."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "createShape",
                    "description": "Create a new shape on the canvas. Use this for single shapes or as part of complex layouts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["rectangle", "circle", "text"],
                                "description": "Type of shape to create"
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate (0 = left edge, increases rightward)"
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (0 = top edge, increases downward)"
                            },
                            "width": {
                                "type": "number",
                                "description": "Width in pixels (for rectangle/text)"
                            },
                            "height": {
                                "type": "number",
                                "description": "Height in pixels (for rectangle/text)"
                            },
                            "radius": {
                                "type": "number",
                                "description": "Radius in pixels (for circle)"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text content (for text shapes)"
                            }
                        },
                        "required": ["type", "x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "moveShape",
                    "description": "Move an existing shape to a new position. Check that the shape is not selectedBy another user first.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shapeId": {
                                "type": "string",
                                "description": "ID of the shape to move"
                            },
                            "x": {
                                "type": "number",
                                "description": "New X coordinate"
                            },
                            "y": {
                                "type": "number",
                                "description": "New Y coordinate"
                            }
                        },
                        "required": ["shapeId", "x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "resizeShape",
                    "description": "Resize an existing shape. Check that the shape is not selectedBy another user first.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shapeId": {
                                "type": "string",
                                "description": "ID of the shape to resize"
                            },
                            "width": {
                                "type": "number",
                                "description": "New width (for rectangle/text)"
                            },
                            "height": {
                                "type": "number",
                                "description": "New height (for rectangle/text)"
                            },
                            "radius": {
                                "type": "number",
                                "description": "New radius (for circle)"
                            }
                        },
                        "required": ["shapeId"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "selectShape",
                    "description": "Select a shape on behalf of the current user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shapeId": {
                                "type": "string",
                                "description": "ID of the shape to select"
                            }
                        },
                        "required": ["shapeId"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "arrangeShapes",
                    "description": "Arrange multiple shapes in a layout pattern (horizontal, vertical, grid).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shapeIds": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "IDs of shapes to arrange"
                            },
                            "layout": {
                                "type": "string",
                                "enum": ["horizontal", "vertical", "grid"],
                                "description": "Layout pattern to apply"
                            },
                            "spacing": {
                                "type": "number",
                                "description": "Space between shapes in pixels",
                                "default": 20
                            },
                            "gridRows": {
                                "type": "number",
                                "description": "Number of rows (for grid layout)"
                            },
                            "gridCols": {
                                "type": "number",
                                "description": "Number of columns (for grid layout)"
                            }
                        },
                        "required": ["shapeIds", "layout"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "findShapes",
                    "description": "Find shapes by type or description. Returns shape IDs that can be used in subsequent commands.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["rectangle", "circle", "text", "all"],
                                "description": "Filter by shape type"
                            }
                        }
                    }
                }
            }
        ]

    def _get_system_prompt(self) -> str:
        """System prompt for AI assistant."""
        return """You are an AI assistant helping users manipulate a collaborative canvas.

CANVAS DETAILS:
- Coordinate system: Top-left is (0,0), X increases right, Y increases down
- Typical viewport: 800x600 pixels
- Shape types: rectangle, circle, text

CRITICAL RULES:
1. Only ONE user can select a shape at a time
2. NEVER manipulate shapes where selectedBy contains a user other than the current user
3. If a shape is unavailable, explain why and suggest alternatives
4. For complex operations (e.g., "login form"), call createShape multiple times with proper positioning
5. Use reasonable defaults for dimensions (e.g., buttons 200x40, input fields 200x30)

CANVAS STATE:
You will receive the current canvas state including all shapes and their properties.
Use findShapes to locate shapes when IDs are not explicitly mentioned.

Always provide friendly, concise responses explaining what you're doing."""

    async def process_command(
        self,
        user_message: str,
        canvas_state: Any,
        username: str
    ) -> Dict[str, Any]:
        """
        Process user command via OpenAI function calling.

        Returns:
            {
                "message": "AI's text response",
                "commands": [{"action": "createShape", "params": {...}}, ...],
                "reasoning": "Optional explanation"
            }
        """

        # Build messages array
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "system",
                "content": f"Current user: {username}\n\nCanvas state:\n{self._format_canvas_state(canvas_state)}"
            },
            {"role": "user", "content": user_message}
        ]

        # Call OpenAI with function calling
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        # Parse response
        assistant_message = response.choices[0].message

        commands = []
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                commands.append({
                    "action": function_name,
                    "params": function_args
                })

        return {
            "message": assistant_message.content or "I've processed your request.",
            "commands": commands,
            "reasoning": None  # Could add chain-of-thought here if needed
        }

    def _format_canvas_state(self, canvas_state: Any) -> str:
        """Format canvas state for AI context."""
        shapes_summary = []
        for shape in canvas_state.shapes:
            selected_info = f" (selected by {shape.selectedBy[0]})" if shape.selectedBy else ""
            shapes_summary.append(
                f"- {shape.id}: {shape.type} at ({shape.x}, {shape.y}){selected_info}"
            )

        return f"Total shapes: {len(canvas_state.shapes)}\n" + "\n".join(shapes_summary)

    async def handle_validation_errors(
        self,
        original_message: str,
        errors: List[str],
        canvas_state: Any
    ) -> Dict[str, Any]:
        """Ask AI to revise commands after validation errors."""

        error_context = "\n".join([f"- {err}" for err in errors])

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Canvas state:\n{self._format_canvas_state(canvas_state)}"},
            {"role": "user", "content": original_message},
            {
                "role": "system",
                "content": f"The following errors occurred:\n{error_context}\n\nPlease suggest alternative commands that avoid these issues."
            }
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        # Parse revised response (similar to process_command)
        assistant_message = response.choices[0].message
        commands = []
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                commands.append({
                    "action": tool_call.function.name,
                    "params": json.loads(tool_call.function.arguments)
                })

        return {
            "message": assistant_message.content or "I've revised my approach.",
            "commands": commands,
            "reasoning": None
        }
```

---

### 3. Validation Service: `services/ai_validator.py`

**Purpose:** Validate AI-generated commands against collaboration rules and database state

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Shape
from typing import Tuple, Dict, Any

class AIValidator:
    def __init__(self, db: AsyncSession, username: str, canvas_state: Any):
        self.db = db
        self.username = username
        self.canvas_state = canvas_state

        # Build shape lookup for quick validation
        self.shapes_by_id = {s.id: s for s in canvas_state.shapes}

    async def validate_command(self, command: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a single AI command.

        Returns:
            (is_valid, error_message)
        """
        action = command["action"]
        params = command["params"]

        if action == "createShape":
            return self._validate_create_shape(params)
        elif action == "moveShape":
            return await self._validate_move_shape(params)
        elif action == "resizeShape":
            return await self._validate_resize_shape(params)
        elif action == "selectShape":
            return await self._validate_select_shape(params)
        elif action == "arrangeShapes":
            return await self._validate_arrange_shapes(params)
        elif action == "findShapes":
            return True, ""  # Query operation, always safe
        else:
            return False, f"Unknown command action: {action}"

    def _validate_create_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate shape creation parameters."""

        # Check shape type
        shape_type = params.get("type")
        if shape_type not in ["rectangle", "circle", "text"]:
            return False, f"Invalid shape type: {shape_type}"

        # Check coordinates are reasonable
        x, y = params.get("x", 0), params.get("y", 0)
        if x < -1000 or x > 5000 or y < -1000 or y > 5000:
            return False, f"Coordinates out of reasonable bounds: ({x}, {y})"

        # Validate type-specific requirements
        if shape_type == "rectangle" or shape_type == "text":
            if "width" not in params or "height" not in params:
                return False, f"{shape_type} requires width and height"
        elif shape_type == "circle":
            if "radius" not in params:
                return False, "circle requires radius"

        # Check text content for text shapes
        if shape_type == "text" and "text" not in params:
            return False, "text shape requires text content"

        return True, ""

    async def _validate_move_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate shape movement."""

        shape_id = params.get("shapeId")
        if not shape_id:
            return False, "shapeId is required"

        # Check shape exists in current canvas state
        if shape_id not in self.shapes_by_id:
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check if shape is selected by another user
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Check coordinates
        x, y = params.get("x", 0), params.get("y", 0)
        if x < -1000 or x > 5000 or y < -1000 or y > 5000:
            return False, f"Coordinates out of reasonable bounds: ({x}, {y})"

        return True, ""

    async def _validate_resize_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate shape resizing."""

        shape_id = params.get("shapeId")
        if not shape_id:
            return False, "shapeId is required"

        if shape_id not in self.shapes_by_id:
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check selection
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Validate dimensions are positive
        if "width" in params and params["width"] <= 0:
            return False, "Width must be positive"
        if "height" in params and params["height"] <= 0:
            return False, "Height must be positive"
        if "radius" in params and params["radius"] <= 0:
            return False, "Radius must be positive"

        return True, ""

    async def _validate_select_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate shape selection."""

        shape_id = params.get("shapeId")
        if not shape_id:
            return False, "shapeId is required"

        if shape_id not in self.shapes_by_id:
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check if already selected by another user
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        return True, ""

    async def _validate_arrange_shapes(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate shape arrangement command."""

        shape_ids = params.get("shapeIds", [])
        if not shape_ids:
            return False, "shapeIds array is required"

        # Check all shapes exist and are available
        for shape_id in shape_ids:
            if shape_id not in self.shapes_by_id:
                return False, f"Shape {shape_id} does not exist"

            shape = self.shapes_by_id[shape_id]
            if shape.selectedBy and shape.selectedBy[0] != self.username:
                other_user = shape.selectedBy[0]
                return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Validate layout type
        layout = params.get("layout")
        if layout not in ["horizontal", "vertical", "grid"]:
            return False, f"Invalid layout type: {layout}"

        # Grid layout needs rows/cols
        if layout == "grid":
            if "gridRows" not in params or "gridCols" not in params:
                return False, "Grid layout requires gridRows and gridCols"

        return True, ""
```

---

### 4. Rate Limiting: In-Memory Tracker

**Purpose:** Prevent abuse of AI API (cost control)

```python
# Add to routes/ai.py or create services/rate_limiter.py

import time
from collections import defaultdict
from typing import Dict

# In-memory rate limit tracker
# Format: {username: [timestamp1, timestamp2, ...]}
rate_limit_tracker: Dict[str, list] = defaultdict(list)

AI_RATE_LIMIT_PER_USER = int(os.getenv("AI_RATE_LIMIT_PER_USER", 10))
RATE_LIMIT_WINDOW_SECONDS = 60

async def check_rate_limit(username: str) -> bool:
    """
    Check if user has exceeded rate limit.

    Returns:
        True if request is allowed, False if rate limit exceeded
    """
    current_time = time.time()

    # Get user's recent requests
    user_requests = rate_limit_tracker[username]

    # Remove requests outside the time window
    user_requests[:] = [
        req_time for req_time in user_requests
        if current_time - req_time < RATE_LIMIT_WINDOW_SECONDS
    ]

    # Check if limit exceeded
    if len(user_requests) >= AI_RATE_LIMIT_PER_USER:
        return False

    # Add current request
    user_requests.append(current_time)
    return True
```

---

### 5. Register AI Routes

**Update:** `main.py`

```python
# Add to main.py imports
from routes.ai import router as ai_router

# Add after existing route registrations
app.include_router(ai_router)
```

---

### 6. Environment Variables

**Update:** `.env`

```bash
# Existing variables
SHAPES_PORT=8000
SHAPES_DEBUG=1
DB_USER=postgres
DB_PASSWORD=demopassword
DB_NAME=p1db_1
DB_PORT=5433
DB_HOST=127.0.0.1
SECRET_KEY=your-super-secret-key-that-is-at-least-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# NEW: AI Feature Configuration
OPENAI_API_KEY=sk-proj-...  # Get from OpenAI dashboard
OPENAI_MODEL=gpt-3.5-turbo  # Or gpt-4-turbo-preview for better quality
AI_RATE_LIMIT_PER_USER=10   # Max requests per user per minute
AI_MAX_COMMANDS_PER_RESPONSE=20  # Safety limit
AI_ENABLE=true  # Feature flag
```

---

### 7. Dependencies

**Update:** `requirements.txt`

```txt
# Existing dependencies
fastapi
uvicorn
sqlalchemy
asyncpg
pydantic
passlib[bcrypt]
python-jose[cryptography]
python-multipart

# NEW: AI dependencies
openai>=1.0.0  # Official OpenAI SDK with async support
```

---

## Key Architectural Decisions

### Decision 1: Backend as Proxy, Not Executor

**Chosen Approach:** Backend validates and returns commands; frontend executes them.

**Alternative Considered:** Backend executes commands directly (updates database).

**Rationale:**
- Frontend already has shape manipulation logic (reuse code)
- Avoids duplicate state management (frontend is source of truth pre-sync)
- Simpler error handling (frontend can show optimistic updates)
- Matches existing architecture (frontend calls `POST /api/shapes` for sync)
- Easier to add undo functionality (frontend manages undo stack)

### Decision 2: Async OpenAI Calls

**Chosen Approach:** Use `AsyncOpenAI` client with async/await.

**Rationale:**
- FastAPI is async-first (existing architecture)
- OpenAI calls take 2-5 seconds (non-blocking is critical)
- Allows concurrent requests from multiple users
- Database operations already async (consistent pattern)

### Decision 3: Two-Phase Validation

**Chosen Approach:** Validate after AI call, re-prompt AI if validation fails.

**Alternative Considered:** Only validate, don't re-prompt.

**Rationale:**
- AI can learn from mistakes (e.g., "shape is selected, try a different one")
- Better user experience (AI explains why something didn't work)
- Handles edge cases gracefully (stale canvas state)
- Minimal performance impact (second call only on errors)

### Decision 4: In-Memory Rate Limiting

**Chosen Approach:** Simple in-memory dictionary tracking recent requests.

**Alternative Considered:** Redis-based rate limiting.

**Rationale:**
- PoC implementation (production can upgrade to Redis)
- No additional infrastructure needed
- Sufficient for single-instance deployment
- Resets on server restart (acceptable for PoC)

### Decision 5: Function Calling Over Prompt Engineering

**Chosen Approach:** Use OpenAI's function calling feature.

**Alternative Considered:** Parse structured responses from text completions.

**Rationale:**
- Function calling is more reliable (structured output guaranteed)
- Better error handling (invalid JSON vs. invalid function args)
- Easier to extend (add new tools without prompt changes)
- OpenAI optimizes models for function calling
- Industry best practice for tool use

---

## Security & Validation

### Security Layers

1. **API Key Protection:** Environment variable, never exposed to frontend
2. **Input Sanitization:** Max message length (500 chars), strip HTML
3. **Rate Limiting:** 10 requests/user/minute
4. **Command Validation:** All commands validated against collaboration rules
5. **Coordinate Bounds:** Prevent creating shapes at extreme coordinates
6. **Authentication:** Optional (can enable with `Depends(get_current_user)`)

### Validation Rules

| Rule | Validation Point | Error Message |
|------|------------------|---------------|
| **Shape exists** | moveShape, resizeShape, selectShape | "Shape {id} does not exist" |
| **Shape available** | moveShape, resizeShape, selectShape | "Shape {id} is selected by {user}" |
| **Valid coordinates** | createShape, moveShape | "Coordinates out of bounds" |
| **Positive dimensions** | createShape, resizeShape | "Width/height/radius must be positive" |
| **Required params** | All shape types | "{shape_type} requires {param}" |
| **Rate limit** | All requests | "Rate limit exceeded. Try again in {n} seconds" |

---

## Error Handling Strategy

### Types of Errors

1. **OpenAI API Errors:**
   - Timeout (30s limit)
   - Rate limit (OpenAI side)
   - Invalid API key
   - Model unavailable

   **Handling:** Catch exception, return 500 with friendly message

2. **Validation Errors:**
   - Shape selected by another user
   - Shape doesn't exist
   - Invalid parameters

   **Handling:** Re-prompt AI with error context (second attempt)

3. **Rate Limit Errors:**
   - User exceeded request quota

   **Handling:** Return 429 with retry-after time

4. **Malformed Requests:**
   - Missing required fields
   - Invalid JSON

   **Handling:** FastAPI automatic validation, return 422

### Error Response Format

```json
{
  "error": "SHAPE_UNAVAILABLE",
  "message": "I couldn't move that rectangle because Alice is currently editing it. Would you like me to move a different shape?",
  "details": {
    "shapeId": "rect1",
    "selectedBy": "Alice"
  }
}
```

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_ai_validator.py`

```python
import pytest
from services.ai_validator import AIValidator

@pytest.mark.asyncio
async def test_validate_create_shape_valid():
    validator = AIValidator(db=mock_db, username="testuser", canvas_state=mock_canvas)
    is_valid, error = validator._validate_create_shape({
        "type": "rectangle",
        "x": 100,
        "y": 200,
        "width": 300,
        "height": 150
    })
    assert is_valid is True
    assert error == ""

@pytest.mark.asyncio
async def test_validate_move_shape_selected_by_other_user():
    # Test that moving a shape selected by another user fails
    ...
```

**Test File:** `tests/test_openai_service.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_process_command_with_mocked_openai():
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        service = OpenAIService()
        result = await service.process_command(
            user_message="Create a red rectangle",
            canvas_state=mock_canvas,
            username="testuser"
        )

        assert "rectangle" in result["message"].lower()
        assert len(result["commands"]) == 1
        assert result["commands"][0]["action"] == "createShape"
```

### Integration Tests

**Test File:** `tests/test_ai_endpoint.py`

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ai_chat_endpoint():
    response = client.post("/api/ai/chat", json={
        "user": "testuser",
        "message": "Create a blue circle at 100, 100",
        "canvasState": {
            "shapes": [],
            "viewport": {"zoom": 1.0, "pan": {"x": 0, "y": 0}}
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "commands" in data
    assert len(data["commands"]) > 0
```

---

## Performance Considerations

### Optimization Strategies

1. **Use GPT-3.5-Turbo for PoC:**
   - 10x cheaper than GPT-4
   - 2-3x faster response time
   - Sufficient for structured function calling

2. **Minimize Context Size:**
   - Send shape summaries, not full shape objects
   - Only include relevant shapes (visible in viewport)
   - Truncate long text fields

3. **Response Streaming (Future):**
   - OpenAI supports streaming responses
   - Can show AI "thinking" in real-time
   - Not critical for PoC

4. **Caching (Future):**
   - Cache common commands (e.g., "create login form")
   - Reduce OpenAI API calls by 20-30%
   - Not critical for PoC

### Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| **API Response Time** | < 5s | 2-4s |
| **Command Validation** | < 100ms | 20-50ms |
| **Rate Limit Check** | < 10ms | 1-5ms |
| **Total Round Trip** | < 6s | 3-5s |

---

## Concerns & Mitigations

### Concern 1: OpenAI API Costs

**Issue:** Each request costs $0.0005-$0.002 (GPT-3.5) or $0.01-$0.03 (GPT-4)

**Mitigation:**
- Use GPT-3.5-turbo for PoC
- Rate limit: 10 requests/user/minute = max $0.03/user/hour
- Set budget alerts in OpenAI dashboard
- Add usage tracking/logging

### Concern 2: AI Hallucinations

**Issue:** AI might generate invalid shape IDs or misunderstand commands

**Mitigation:**
- Strong system prompt with clear rules
- Validation layer catches all errors
- Two-phase validation (re-prompt on errors)
- Function calling schema enforces structure

### Concern 3: Concurrent Edits

**Issue:** Canvas state changes while AI is processing

**Mitigation:**
- Validation checks shape availability at execution time
- Frontend re-fetches latest state before applying commands
- If conflict, show error and suggest refresh

### Concern 4: Complex Command Failures

**Issue:** Multi-step commands (e.g., "login form") might partially fail

**Mitigation:**
- Validate all commands before returning
- If any command fails, AI revises entire plan
- Frontend applies commands atomically (all or nothing)
- Provide clear feedback on partial failures

### Concern 5: Database Load

**Issue:** Frequent shape updates might strain database

**Mitigation:**
- AI commands batch shape updates (single `POST /api/shapes` call)
- Existing polling mechanism limits sync frequency (2s intervals)
- No additional database load beyond current architecture
- PostgreSQL handles concurrent writes efficiently

---

## Implementation Checklist

### Phase 1: Core Backend (Week 1)

- [ ] Install OpenAI SDK (`pip install openai>=1.0.0`)
- [ ] Create `routes/ai.py` with `/api/ai/chat` endpoint
- [ ] Implement `services/openai_service.py` with function calling
- [ ] Define all tool schemas (6+ functions)
- [ ] Implement `services/ai_validator.py` with validation logic
- [ ] Add rate limiting function
- [ ] Update `main.py` to register AI routes
- [ ] Add environment variables to `.env`
- [ ] Test with Postman/curl (manual requests)

### Phase 2: Testing & Refinement (Week 1-2)

- [ ] Write unit tests for validator
- [ ] Write unit tests for OpenAI service (mocked)
- [ ] Write integration tests for `/api/ai/chat` endpoint
- [ ] Test all 6+ command types
- [ ] Test validation rules (shape unavailable, etc.)
- [ ] Test rate limiting
- [ ] Test error handling (invalid inputs, API timeouts)
- [ ] Refine system prompt based on results

### Phase 3: Production Readiness (Week 3)

- [ ] Add authentication to `/api/ai/chat` (optional for PoC)
- [ ] Add logging/monitoring (track costs, errors, latency)
- [ ] Add feature flag support (`AI_ENABLE` env var)
- [ ] Document API in OpenAPI schema (FastAPI automatic)
- [ ] Create developer documentation
- [ ] Performance testing (load test with multiple concurrent users)
- [ ] Security audit (input sanitization, SQL injection prevention)

---

## File Structure

```
pkgs/p1-back/trees/t2/
├── routes/
│   ├── ai.py                      [NEW] AI chat endpoint
├── services/
│   ├── openai_service.py          [NEW] OpenAI integration
│   ├── ai_validator.py            [NEW] Command validation
├── tests/
│   ├── test_ai_validator.py       [NEW] Validator unit tests
│   ├── test_openai_service.py     [NEW] OpenAI service unit tests
│   ├── test_ai_endpoint.py        [NEW] Endpoint integration tests
├── main.py                        [MODIFIED] Register AI routes
├── requirements.txt               [MODIFIED] Add openai package
├── .env                           [MODIFIED] Add OpenAI config
└── docs/
    └── aitool-plan.md             [THIS FILE]
```

---

## Summary

This backend architecture provides a **minimal viable implementation** of the AI chat feature while maintaining:

1. **Security:** API keys protected, rate limiting, validation layers
2. **Compatibility:** Works with existing database, auth, and sync mechanisms
3. **Simplicity:** Backend as proxy/validator, frontend executes commands
4. **Extensibility:** Easy to add new commands, improve AI prompts, upgrade models
5. **Testability:** Clear separation of concerns, mockable OpenAI client

The backend acts as an intelligent intermediary between the frontend and OpenAI, ensuring all AI-generated commands are safe, valid, and respect the collaborative editing constraints.

**Next Steps:** Implement Phase 1 (core backend), then integrate with frontend (see Frontend Plan section above).

# Frontend plan

## Executive Summary

This document outlines the architecture for implementing an AI-powered chat widget that allows users to manipulate the collaborative canvas through natural language commands. The feature will use OpenAI's function calling capabilities to interpret user commands and execute canvas operations while respecting the existing multi-user collaboration constraints.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Frontend Components](#frontend-components)
4. [Backend Components](#backend-components)
5. [AI Function Calling Schema](#ai-function-calling-schema)
6. [Implementation Plan](#implementation-plan)
7. [Security & Concerns](#security--concerns)
8. [Testing Strategy](#testing-strategy)

---

## Feature Overview

### User Experience Flow

1. User clicks an "AI Assistant" button to open a chat widget
2. User types a natural language command (e.g., "Create a blue rectangle in the center")
3. The system sends the command to the backend along with current canvas state
4. Backend uses OpenAI's function calling to parse the command and determine actions
5. Backend returns structured commands to frontend
6. Frontend executes the commands (create shapes, move shapes, etc.)
7. Changes are synced through existing collaboration system
8. User sees the result on canvas immediately (optimistic update)

### Required Command Categories (6+ commands)

**Creation Commands:**
- Create rectangle/circle/text with specific properties
- Create multiple shapes (e.g., "grid of 3x3 squares")
- Create complex layouts (e.g., "login form")

**Manipulation Commands:**
- Move shape to position or by delta
- Resize shape by dimensions or factor
- Rotate shape (future - not in current schema)

**Layout Commands:**
- Arrange shapes horizontally/vertically
- Space shapes evenly
- Align shapes (left, center, right, top, middle, bottom)

**Selection Commands:**
- Select shape by description (e.g., "select the blue rectangle")
- Select all shapes of a type
- Clear selection

**Query Commands:**
- Get canvas state
- Count shapes
- Find shapes by property

**Complex Commands:**
- Multi-step operations combining creation and layout

---

## Architecture Decisions

### Key Decision: Backend-Driven AI Processing

**Decision:** AI processing happens on the backend, not frontend.

**Rationale:**
1. **Security:** Keep OpenAI API keys server-side
2. **Consistency:** Ensure all users receive the same interpretation of commands
3. **State Management:** Backend has authoritative canvas state
4. **Cost Control:** Server can implement rate limiting and usage tracking
5. **Complexity:** LLM reasoning about canvas state is easier server-side

### Frontend vs Backend Responsibilities

| Responsibility | Location | Rationale |
|---------------|----------|-----------|
| **Chat UI Rendering** | Frontend | User interface, React components |
| **User Input Capture** | Frontend | Text input, send button |
| **Chat History Display** | Frontend | Message bubbles, scrolling |
| **OpenAI API Call** | Backend | Security, API key protection |
| **Function Calling Interpretation** | Backend | Stateful, requires canvas context |
| **Command Validation** | Backend | Check shape IDs exist, user has permission |
| **Canvas Manipulation** | Frontend | Execute commands via existing React state |
| **Collision Detection** | Backend | Verify shapes aren't selected by others |
| **Rate Limiting** | Backend | Prevent abuse |
| **Logging/Analytics** | Backend | Track AI usage, costs |

---

## Frontend Components

### 1. AI Chat Widget Component

**Location:** `my-react-app/src/components/AIChatWidget.tsx` (new file)

**Component Structure:**
```typescript
interface AIChatWidgetProps {
  currentUser: string;
  shapes: Shape[];
  onExecuteCommands: (commands: AICommand[]) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  commands?: AICommand[]; // For assistant messages
  status?: 'pending' | 'success' | 'error'; // Command execution status
}

interface AICommand {
  action: string; // 'createShape', 'moveShape', 'resizeShape', etc.
  params: Record<string, any>;
}
```

**State Management:**
- `messages: ChatMessage[]` - Chat history
- `inputText: string` - Current user input
- `isLoading: boolean` - Waiting for AI response
- `isOpen: boolean` - Widget visibility
- `error: string | null` - Error message display

**Features:**
- Collapsible floating panel (bottom-right corner)
- Scrollable message history
- Text input with send button
- Loading indicator while processing
- Error handling display
- Success/failure feedback for commands

### 2. Integration with DemoFigma Component

**Location:** `my-react-app/src/DemoFigma.tsx` (modifications)

**Required Changes:**

1. **Add AI Chat State:**
```typescript
const [aiChatOpen, setAiChatOpen] = useState(false);
```

2. **Add AI Button to Top Bar:**
```tsx
<button
  onClick={() => setAiChatOpen(!aiChatOpen)}
  className={aiChatOpen ? 'active' : ''}
>
  AI Assistant
</button>
```

3. **Implement Command Executor:**
```typescript
const executeAICommands = useCallback(async (commands: AICommand[]) => {
  for (const cmd of commands) {
    switch (cmd.action) {
      case 'createShape':
        // Create shape with specific properties
        break;
      case 'moveShape':
        // Move shape by ID
        break;
      case 'resizeShape':
        // Resize shape by ID
        break;
      case 'selectShape':
        // Select shape by ID
        break;
      case 'arrangeShapes':
        // Layout algorithm
        break;
      // ... more commands
    }
  }
  // Update server after all commands
  await updateShapesOnServer(shapes);
}, [shapes, currentUser, updateShapesOnServer]);
```

4. **Render Widget:**
```tsx
{aiChatOpen && (
  <AIChatWidget
    currentUser={currentUser}
    shapes={shapes}
    onExecuteCommands={executeAICommands}
  />
)}
```

### 3. AI Service Layer

**Location:** `my-react-app/src/services/aiService.ts` (new file)

**Purpose:** Handle API communication with backend

```typescript
export interface AIRequest {
  user: string;
  message: string;
  canvasState: {
    shapes: Shape[];
    viewport: { zoom: number; pan: { x: number; y: number } };
  };
}

export interface AIResponse {
  message: string; // AI's text response
  commands: AICommand[]; // Structured commands to execute
  reasoning?: string; // Optional explanation
}

export const sendAIMessage = async (request: AIRequest): Promise<AIResponse> => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const response = await fetch(`${apiUrl}/ai/chat`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`AI request failed: ${response.status}`);
  }

  return await response.json();
};
```

### 4. Command Execution Utilities

**Location:** `my-react-app/src/utils/aiCommands.ts` (new file)

**Purpose:** Helper functions for executing AI commands

```typescript
export const createShapeFromAI = (
  type: ShapeType,
  x: number,
  y: number,
  properties: Record<string, any>
): Shape => {
  // Similar to existing createShape but with custom properties
};

export const findShapeCenter = (viewport: { width: number; height: number }) => {
  // Calculate center coordinates
};

export const arrangeHorizontally = (shapes: Shape[], spacing: number) => {
  // Layout algorithm
};

export const arrangeGrid = (shapes: Shape[], rows: number, cols: number) => {
  // Grid layout algorithm
};
```

---

## Backend Components

### 1. New API Endpoint: `/api/ai/chat`

**Location:** Backend API (FastAPI)

**Method:** POST

**Request Body:**
```json
{
  "user": "username",
  "message": "Create a blue rectangle in the center",
  "canvasState": {
    "shapes": [...],
    "viewport": {
      "zoom": 1.0,
      "pan": { "x": 0, "y": 0 }
    }
  }
}
```

**Response Body:**
```json
{
  "message": "I've created a blue rectangle in the center of the canvas.",
  "commands": [
    {
      "action": "createShape",
      "params": {
        "type": "rectangle",
        "x": 400,
        "y": 300,
        "width": 200,
        "height": 150,
        "color": "blue"
      }
    }
  ],
  "reasoning": "Calculated center based on typical viewport size."
}
```

**Error Response:**
```json
{
  "error": "Shape with ID 'shape_123' is currently selected by another user",
  "message": "I couldn't move that shape because it's being edited by Alice."
}
```

### 2. OpenAI Integration Service

**Purpose:** Handle OpenAI API calls with function calling

**Key Components:**

1. **Function Definitions (Tool Schema):**
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "createShape",
            "description": "Create a new shape on the canvas",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["rectangle", "circle", "text"],
                        "description": "The type of shape to create"
                    },
                    "x": {
                        "type": "number",
                        "description": "X coordinate"
                    },
                    "y": {
                        "type": "number",
                        "description": "Y coordinate"
                    },
                    "width": {
                        "type": "number",
                        "description": "Width for rectangle/text"
                    },
                    "height": {
                        "type": "number",
                        "description": "Height for rectangle/text"
                    },
                    "radius": {
                        "type": "number",
                        "description": "Radius for circle"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text content for text shapes"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color of the shape (for future styling)"
                    }
                },
                "required": ["type", "x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "moveShape",
            "description": "Move an existing shape to a new position",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to move. If not known, use description to find shape first."
                    },
                    "x": {
                        "type": "number",
                        "description": "New X coordinate"
                    },
                    "y": {
                        "type": "number",
                        "description": "New Y coordinate"
                    }
                },
                "required": ["shapeId", "x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resizeShape",
            "description": "Resize an existing shape",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to resize"
                    },
                    "width": {
                        "type": "number",
                        "description": "New width (for rectangles/text)"
                    },
                    "height": {
                        "type": "number",
                        "description": "New height (for rectangles/text)"
                    },
                    "radius": {
                        "type": "number",
                        "description": "New radius (for circles)"
                    },
                    "scaleFactor": {
                        "type": "number",
                        "description": "Scale factor (e.g., 2.0 for twice as big)"
                    }
                },
                "required": ["shapeId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "selectShape",
            "description": "Select a shape on behalf of the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to select"
                    }
                },
                "required": ["shapeId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "findShapes",
            "description": "Find shapes by description or properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["rectangle", "circle", "text", "all"],
                        "description": "Filter by shape type"
                    },
                    "description": {
                        "type": "string",
                        "description": "Natural language description (e.g., 'the blue rectangle')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "arrangeShapes",
            "description": "Arrange multiple shapes in a layout",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeIds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IDs of shapes to arrange"
                    },
                    "layout": {
                        "type": "string",
                        "enum": ["horizontal", "vertical", "grid"],
                        "description": "Layout pattern"
                    },
                    "spacing": {
                        "type": "number",
                        "description": "Space between shapes in pixels"
                    },
                    "gridRows": {
                        "type": "number",
                        "description": "Number of rows for grid layout"
                    },
                    "gridCols": {
                        "type": "number",
                        "description": "Number of columns for grid layout"
                    }
                },
                "required": ["shapeIds", "layout"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "createComplexLayout",
            "description": "Create a multi-shape layout like a form, navbar, or card",
            "parameters": {
                "type": "object",
                "properties": {
                    "layoutType": {
                        "type": "string",
                        "enum": ["loginForm", "navbar", "card", "custom"],
                        "description": "Type of layout to create"
                    },
                    "position": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "description": "Top-left position of the layout"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Layout-specific properties (e.g., number of navbar items)"
                    }
                },
                "required": ["layoutType", "position"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "getCanvasState",
            "description": "Get information about the current canvas state",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
```

2. **System Prompt:**
```text
You are an AI assistant helping users manipulate a collaborative canvas.
The canvas contains shapes (rectangles, circles, text) that can be created, moved, and resized.

Current canvas dimensions: 800x600 (typical viewport)
Coordinate system: Top-left is (0,0), X increases right, Y increases down

IMPORTANT CONSTRAINTS:
- Only one user can select a shape at a time
- Do NOT manipulate shapes that are selectedBy another user
- Always check canvasState.shapes[].selectedBy before moving/resizing
- If a shape is unavailable, explain why and suggest alternatives

Canvas state information will be provided with each request.
Use the available functions to execute user commands.
For complex operations, call multiple functions in sequence.
Always provide a friendly response explaining what you did.
```

3. **Request Processing Flow:**
```
1. Receive user message + canvas state
2. Build OpenAI messages array:
   - System prompt
   - Canvas state summary
   - User message
3. Call OpenAI with tools/function calling
4. Parse function calls from response
5. Validate each function call:
   - Check shape exists
   - Check not selected by another user
   - Validate coordinates in bounds
6. If validation fails, call OpenAI again with error context
7. Return commands + AI message to frontend
```

### 3. Validation & Security Layer

**Purpose:** Ensure AI commands are safe and respect collaboration rules

**Validations:**
1. **Shape Ownership:** Verify shape isn't selected by another user
2. **Shape Existence:** Verify shapeId exists in current state
3. **Coordinate Bounds:** Prevent creating shapes at extreme coordinates
4. **Rate Limiting:** Max N requests per user per minute
5. **Command Limits:** Max N commands per AI response
6. **User Authentication:** Only authenticated users can use AI (optional)

**Example Validation Function:**
```python
def validate_move_shape(shape_id: str, user: str, canvas_state: dict) -> tuple[bool, str]:
    shape = next((s for s in canvas_state['shapes'] if s['id'] == shape_id), None)

    if not shape:
        return False, f"Shape {shape_id} does not exist"

    if shape['selectedBy'] and shape['selectedBy'][0] != user:
        return False, f"Shape is currently selected by {shape['selectedBy'][0]}"

    return True, ""
```

### 4. Configuration & Environment

**New Environment Variables:**
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview  # Or gpt-3.5-turbo for cost savings
AI_RATE_LIMIT_PER_USER=10  # Requests per minute
AI_MAX_COMMANDS_PER_RESPONSE=20  # Prevent abuse
AI_ENABLE=true  # Feature flag
```

---

## AI Function Calling Schema

### Complete Tool Definitions

See Backend Components section for full schema.

### Example Function Call Sequences

**Simple Command:**
```
User: "Create a red circle at 100, 200"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "createShape",
        "arguments": {
          "type": "circle",
          "x": 100,
          "y": 200,
          "radius": 50,
          "color": "red"
        }
      }
    }
  ]
}
```

**Complex Command:**
```
User: "Create a login form"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "createComplexLayout",
        "arguments": {
          "layoutType": "loginForm",
          "position": {"x": 300, "y": 200},
          "properties": {
            "includeRememberMe": false
          }
        }
      }
    }
  ]
}

Backend expands to:
[
  createShape(type="text", x=300, y=200, text="Username:", width=200, height=30),
  createShape(type="rectangle", x=300, y=240, width=200, height=40),
  createShape(type="text", x=300, y=290, text="Password:", width=200, height=30),
  createShape(type="rectangle", x=300, y=330, width=200, height=40),
  createShape(type="rectangle", x=300, y=380, width=200, height=40, text="Login")
]
```

**Multi-Step Command:**
```
User: "Find all circles and arrange them horizontally"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "findShapes",
        "arguments": {"type": "circle"}
      }
    }
  ]
}

(After receiving shape IDs)

{
  "tool_calls": [
    {
      "function": {
        "name": "arrangeShapes",
        "arguments": {
          "shapeIds": ["shape_1", "shape_2", "shape_3"],
          "layout": "horizontal",
          "spacing": 20
        }
      }
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Backend Foundation (Week 1)

**Tasks:**
1. Add OpenAI SDK to backend dependencies
2. Create `/api/ai/chat` endpoint skeleton
3. Implement OpenAI function calling integration
4. Define all tool schemas
5. Implement validation layer
6. Add rate limiting
7. Unit tests for validation logic
8. Environment variable configuration

**Deliverables:**
- Backend can receive AI requests
- Backend can call OpenAI with function calling
- Backend returns structured commands
- Backend validates commands against collaboration rules

### Phase 2: Frontend UI (Week 1-2)

**Tasks:**
1. Create `AIChatWidget` component
2. Implement chat UI (messages, input, loading states)
3. Create `aiService.ts` for API communication
4. Add AI button to DemoFigma top bar
5. Wire up state management
6. Add error handling and feedback
7. Style the widget to match existing design

**Deliverables:**
- Functional chat widget UI
- Can send messages to backend
- Displays AI responses
- Shows loading and error states

### Phase 3: Command Execution (Week 2)

**Tasks:**
1. Implement `executeAICommands` function in DemoFigma
2. Handle `createShape` commands
3. Handle `moveShape` commands
4. Handle `resizeShape` commands
5. Handle `selectShape` commands
6. Handle `arrangeShapes` commands
7. Implement layout algorithms (horizontal, vertical, grid)
8. Test with existing collaboration system
9. Ensure proper sync via `updateShapesOnServer`

**Deliverables:**
- All AI commands execute correctly
- Changes sync to other users
- Respects selection constraints
- Optimistic updates work

### Phase 4: Complex Commands (Week 3)

**Tasks:**
1. Implement `createComplexLayout` on backend
2. Define templates for loginForm, navbar, card
3. Handle multi-shape creation
4. Implement intelligent positioning
5. Test complex commands end-to-end
6. Refine AI prompts for better interpretation

**Deliverables:**
- Can create login forms
- Can create navigation bars
- Can create card layouts
- AI understands context

### Phase 5: Polish & Testing (Week 3-4)

**Tasks:**
1. Comprehensive testing of all 6+ required commands
2. Edge case testing (offline users, shape collisions)
3. Performance optimization
4. Error message improvements
5. User experience refinements
6. Documentation
7. Demo video creation

**Deliverables:**
- Feature complete and tested
- Documentation for PM review
- Demo showing all required commands
- Ready for submission

---

## Security & Concerns

### Security Considerations

1. **API Key Protection**
   - **Concern:** OpenAI API key must not be exposed to frontend
   - **Solution:** All AI calls go through backend proxy
   - **Implementation:** Store key in environment variables, never in code

2. **Rate Limiting**
   - **Concern:** Users could abuse AI API causing high costs
   - **Solution:** Per-user rate limits (10 requests/minute)
   - **Implementation:** Redis-based rate limiting or in-memory tracking

3. **Input Validation**
   - **Concern:** Malicious prompts could try to manipulate AI behavior
   - **Solution:** Sanitize user input, length limits (500 chars)
   - **Implementation:** Backend validates input before sending to OpenAI

4. **Command Validation**
   - **Concern:** AI might generate invalid or malicious commands
   - **Solution:** Strict validation layer checks all commands
   - **Implementation:** Validate against schema, check bounds, verify permissions

5. **Cost Control**
   - **Concern:** AI API usage could be expensive
   - **Solution:** Monitor costs, set budget alerts, use cheaper models
   - **Implementation:** CloudWatch/logging, GPT-3.5-turbo vs GPT-4

### Collaboration Concerns

1. **Shape Selection Conflicts**
   - **Issue:** AI might try to manipulate shapes selected by others
   - **Solution:** Validation layer checks `selectedBy` before allowing operations
   - **Implementation:** Backend validates, AI gets error feedback, suggests alternatives

2. **Race Conditions**
   - **Issue:** AI command execution happens while other users are editing
   - **Solution:** Use existing polling-based sync mechanism
   - **Implementation:** Commands go through `updateShapesOnServer` which does merge logic

3. **Concurrent AI Requests**
   - **Issue:** User sends multiple AI requests while first is processing
   - **Solution:** Disable send button while loading, queue requests
   - **Implementation:** Frontend `isLoading` state prevents concurrent sends

4. **Stale Canvas State**
   - **Issue:** Canvas state changes between request and execution
   - **Solution:** Include timestamp, backend re-validates before execution
   - **Implementation:** Backend checks shape still exists and available

### User Experience Concerns

1. **AI Interpretation Errors**
   - **Issue:** AI might misunderstand user intent
   - **Solution:** Provide clear feedback, allow undo, show reasoning
   - **Implementation:** Display AI's text response, add undo button

2. **Performance**
   - **Issue:** OpenAI API calls take 2-5 seconds
   - **Solution:** Show loading indicators, optimize prompts for speed
   - **Implementation:** Skeleton loaders, use streaming if available

3. **Learning Curve**
   - **Issue:** Users might not know what commands are possible
   - **Solution:** Provide examples, autocomplete suggestions
   - **Implementation:** Placeholder text with examples, help button

4. **Error Communication**
   - **Issue:** Users need to understand why commands fail
   - **Solution:** Clear error messages in natural language
   - **Implementation:** Backend returns user-friendly error messages

### Technical Concerns

1. **Backend API Schema Extension**
   - **Issue:** Need to add new endpoint to existing FastAPI backend
   - **Solution:** Follow existing patterns, add to OpenAPI schema
   - **Implementation:** Standard FastAPI route with proper models

2. **Frontend State Management**
   - **Issue:** DemoFigma is already 1,182 lines, adding more complexity
   - **Solution:** Extract AI logic to separate components/services
   - **Implementation:** Create `AIChatWidget`, `aiService.ts`, `aiCommands.ts`

3. **Testing Complexity**
   - **Issue:** AI responses are non-deterministic
   - **Solution:** Mock OpenAI in tests, test validation logic separately
   - **Implementation:** Unit tests for validation, integration tests with mocked AI

4. **Backward Compatibility**
   - **Issue:** Must not break existing functionality
   - **Solution:** Feature flag, isolated code, optional feature
   - **Implementation:** `AI_ENABLE` env var, widget only shows if enabled

### Mitigation Strategies Summary

| Concern | Risk Level | Mitigation | Status |
|---------|-----------|------------|--------|
| API Key Exposure | High | Backend proxy only | Planned |
| High Costs | Medium | Rate limiting + monitoring | Planned |
| Selection Conflicts | High | Validation layer | Planned |
| Race Conditions | Medium | Existing merge logic | Leverages existing |
| AI Misinterpretation | Medium | Clear feedback + undo | Planned |
| Performance | Low | Loading indicators | Planned |
| Backward Compatibility | Low | Feature flag | Planned |

---

## Testing Strategy

### Unit Tests

**Backend:**
- Validation functions (shape ownership, existence, bounds)
- Command parsing and generation
- Rate limiting logic
- Error handling

**Frontend:**
- Command execution functions
- Layout algorithms (arrangeHorizontally, arrangeGrid)
- Component rendering (AIChatWidget)
- Service layer (aiService.ts)

### Integration Tests

**Backend:**
- `/api/ai/chat` endpoint with mocked OpenAI
- Full request/response cycle
- Validation with actual canvas state
- Error scenarios

**Frontend:**
- Chat widget interaction flow
- Command execution with actual shapes
- Sync with backend via API
- Multi-step command sequences

### End-to-End Tests

**Required Command Testing (6+ commands):**

1. **Creation Commands:**
   - "Create a red rectangle at 100, 200"
   - "Add a text that says 'Hello World' at 300, 300"
   - "Make a circle with radius 50 at 400, 200"

2. **Manipulation Commands:**
   - "Move the rectangle to 200, 200"
   - "Resize the circle to be twice as big"
   - "Make the text box 300 pixels wide"

3. **Layout Commands:**
   - "Arrange these three shapes horizontally"
   - "Create a grid of 3x3 squares"
   - "Space the circles evenly"

4. **Complex Commands:**
   - "Create a login form with username and password fields"
   - "Build a navigation bar with 4 menu items"
   - "Make a card layout with title and description"

**Collaboration Scenarios:**
- User A selects shape, User B tries to move it via AI (should fail gracefully)
- AI creates shape while another user is panning/zooming (should work)
- Multiple users use AI simultaneously (should handle correctly)

**Error Scenarios:**
- Invalid shape ID
- Shape selected by another user
- Malformed command
- OpenAI API timeout
- Rate limit exceeded

### Manual Testing Checklist

- [ ] Chat widget opens and closes smoothly
- [ ] Messages display correctly (user vs assistant)
- [ ] Loading state shows during AI processing
- [ ] Error messages display clearly
- [ ] All 6 required command types work
- [ ] Complex commands create proper layouts
- [ ] Commands respect selection constraints
- [ ] Changes sync to other users
- [ ] Widget is responsive on different screen sizes
- [ ] Works with authenticated and anonymous users
- [ ] Works after page refresh (state restoration)
- [ ] Handles network errors gracefully

---

## Appendix A: File Structure

```
my-react-app/
├── src/
│   ├── components/
│   │   └── AIChatWidget.tsx          [NEW] Chat UI component
│   │   └── AIChatWidget.css          [NEW] Widget styles
│   ├── services/
│   │   └── aiService.ts              [NEW] API communication
│   ├── utils/
│   │   └── aiCommands.ts             [NEW] Command execution helpers
│   ├── DemoFigma.tsx                 [MODIFIED] Add AI integration
│   ├── DemoFigma.css                 [MODIFIED] Add AI button styles
│   └── main.tsx                      [NO CHANGE]

backend/
├── routes/
│   └── ai.py                         [NEW] AI chat endpoint
├── services/
│   └── openai_service.py             [NEW] OpenAI integration
│   └── ai_validator.py               [NEW] Command validation
├── models/
│   └── ai_models.py                  [NEW] Request/response models
├── main.py                           [MODIFIED] Register AI routes
└── requirements.txt                  [MODIFIED] Add openai package

docs/
└── aitool-plan.md                    [THIS FILE]
```

## Appendix B: Environment Configuration

**.env (Frontend):**
```
VITE_API_URL=http://127.0.0.1:8000/api
VITE_POLLING_INTERVAL_MS=2000
VITE_USER_POLLING_INTERVAL_MS=5000
VITE_HIDE_DEBUG_MENU=false
VITE_AI_ENABLED=true                  [NEW]
```

**.env (Backend):**
```
OPENAI_API_KEY=sk-...                 [NEW]
OPENAI_MODEL=gpt-3.5-turbo           [NEW]
AI_RATE_LIMIT_PER_USER=10            [NEW]
AI_MAX_COMMANDS_PER_RESPONSE=20      [NEW]
AI_ENABLE=true                        [NEW]
```

## Appendix C: API Endpoint Specification

**POST `/api/ai/chat`**

Request:
```typescript
{
  user: string;              // Current username
  message: string;           // User's natural language command
  canvasState: {
    shapes: Shape[];         // Current shapes array
    viewport: {
      zoom: number;
      pan: { x: number; y: number };
    };
  };
}
```

Response (Success):
```typescript
{
  message: string;           // AI's text response
  commands: AICommand[];     // Structured commands to execute
  reasoning?: string;        // Optional explanation of AI's logic
}
```

Response (Error):
```typescript
{
  error: string;             // Error code/type
  message: string;           // User-friendly error message
  details?: any;             // Additional debug info
}
```

---

## Conclusion

This architecture plan provides a comprehensive blueprint for implementing the AI Canvas Agent feature. The design prioritizes:

1. **Security:** API keys protected, validation at every step
2. **Collaboration:** Respects existing multi-user constraints
3. **User Experience:** Clear feedback, natural language understanding
4. **Maintainability:** Modular code, clear separation of concerns
5. **Scalability:** Rate limiting, cost controls, feature flags

The implementation will be phased over 3-4 weeks, with clear milestones and deliverables at each stage. The feature will enable users to manipulate the canvas through natural language while maintaining the integrity of the collaborative system.

Next steps: Review this plan with the team, get approval, and begin Phase 1 implementation.
