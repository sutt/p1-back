"""
OpenAI Service - Basic Proof of Concept

Handles all OpenAI API interactions with function calling for canvas manipulation.

LIMITATIONS:
- No streaming responses (waits for full completion)
- No conversation history/context (each request is isolated)
- Basic system prompt (may need refinement for edge cases)
- No caching of common commands
- No cost tracking/monitoring beyond OpenAI dashboard
- Tool schema is static (not dynamically generated)
- Error handling is basic (no exponential backoff, etc.)

MANUAL INTERVENTIONS REQUIRED:
- Set OPENAI_API_KEY in .env file
- Optionally set OPENAI_MODEL (defaults to gpt-3.5-turbo)
- Monitor costs in OpenAI dashboard
- Consider upgrading to gpt-4-turbo-preview for better quality
- Refine system prompt based on user testing
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

# AI_DEBUG environment variable controls debug output
AI_DEBUG = os.getenv("AI_DEBUG", "false").lower() == "true"


def ai_debug_print(message: str):
    """Print debug messages if AI_DEBUG is enabled."""
    if AI_DEBUG:
        print(f"[AI_DEBUG OpenAI] {message}")


class OpenAIService:
    """
    Service for OpenAI API interactions with function calling.

    This is a basic PoC implementation. For production, consider:
    - Adding retry logic with exponential backoff
    - Implementing response streaming for better UX
    - Adding conversation history/context management
    - Implementing command caching
    - Adding detailed logging/monitoring
    """

    def __init__(self):
        """
        Initialize OpenAI service.

        MANUAL INTERVENTION: Set OPENAI_API_KEY in .env file
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please add OPENAI_API_KEY=sk-... to your .env file"
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        allowed_models_str = os.getenv("OPENAI_MODELS_ALLOWED", "gpt-4o,gpt-5")
        self.allowed_models = [model.strip() for model in allowed_models_str.split(',')]
        self.tools = self._define_tools()
        self.system_prompt = self._get_system_prompt()

        ai_debug_print(f"Initialized OpenAI service with default model: {self.default_model}")
        ai_debug_print(f"Allowed models: {self.allowed_models}")

    def _define_tools(self) -> List[Dict]:
        """
        Define OpenAI function calling tool schema.

        LIMITATION: Static schema, not dynamically generated from canvas capabilities
        TODO: Consider generating schema from shape type definitions
        """
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
        """
        System prompt for AI assistant.

        LIMITATION: Basic prompt, may need refinement for edge cases
        TODO: Consider A/B testing different prompt variations
        """
        return """You are an AI assistant helping users manipulate a collaborative canvas.

CANVAS DETAILS:
- Coordinate system: Top-left is (0,0), X increases right, Y increases down
- Typical viewport: 800x600 pixels at zoom=1.0
- use canvasState.viewport.{x,y} state to understand where the user is currently viewing. This can can ran
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

SPECIAL INSTRUCTIONS:
When asked to create shapes use the canvasState.viewport.(x, y) to understand where the current user if looking and add the shapes to that area in what manner was requested.
When asked to create non-trivial layouts (e.g. re-create a logo or mockup) lay those out 100 - 200 points away from exisiting shapes.

Always provide friendly, concise responses explaining what you're doing."""

    async def process_command(
        self,
        user_message: str,
        canvas_state: Any,
        username: str,
        model: str,
        screenshot: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process user command via OpenAI function calling.

        LIMITATION: No conversation history, each request is isolated
        TODO: Implement context/history management for multi-turn conversations

        Args:
            user_message: User's natural language command
            canvas_state: Current canvas state from frontend
            username: Current username
            model: AI model to use
            screenshot: Optional screenshot data with map context

        Returns:
            Dictionary with:
                - message: AI's text response
                - commands: List of structured commands
                - reasoning: Optional explanation
        """
        from services.screenshot_utils import (
            validate_screenshot,
            dump_screenshot_to_filesystem,
            dump_full_prompt,
            build_geographical_context,
            ai_screenshot_debug_print
        )
        import uuid

        ai_debug_print(f"Processing command for user: {username}")
        ai_debug_print(f"User message: {user_message}")

        # Generate request ID for debugging
        request_id = str(uuid.uuid4())[:8]
        ai_screenshot_debug_print(f"Request ID: {request_id}")

        # Build messages array
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "system",
                "content": f"Current user: {username}\n\nCanvas state:\n{self._format_canvas_state(canvas_state)}"
            }
        ]

        # Build user message content
        user_content = []

        # If screenshot is provided, process it
        # LIMITATION: Basic PoC - no retry on screenshot processing failure
        if screenshot:
            ai_screenshot_debug_print("Screenshot provided, processing...")

            # Convert Pydantic model to dict if needed
            # LIMITATION: Uses Pydantic v2 model_dump(), may need adjustment for v1
            screenshot_dict = screenshot.model_dump() if hasattr(screenshot, 'model_dump') else (screenshot.dict() if hasattr(screenshot, 'dict') else screenshot)

            # Validate screenshot
            is_valid, error_msg = validate_screenshot(screenshot_dict)
            if not is_valid:
                ai_screenshot_debug_print(f"Screenshot validation failed: {error_msg}")
                ai_debug_print(f"Screenshot validation failed: {error_msg}. Falling back to text-only mode.")
                # Fall back to text-only mode
                screenshot = None
            else:
                # Dump screenshot for debugging
                dump_screenshot_to_filesystem(screenshot_dict, request_id)

                # Add image to content
                # LIMITATION: OpenAI expects specific format, this may need adjustment for other AI providers
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{screenshot_dict['format']};base64,{screenshot_dict['data']}"
                    }
                })

                # Build and add geographical context
                geo_context = build_geographical_context(screenshot_dict)
                text_content = f"{geo_context}\n\nUser message: {user_message}"
                user_content.append({
                    "type": "text",
                    "text": text_content
                })

                ai_screenshot_debug_print("Screenshot processed and added to request")

        # If no screenshot or screenshot validation failed, use text-only
        if not screenshot:
            user_content = user_message

        # Add user message to messages
        messages.append({
            "role": "user",
            "content": user_content
        })

        # Dump full prompt for debugging
        dump_full_prompt(messages, request_id)

        ai_debug_print(f"Calling OpenAI API with model: {model}")

        # Call OpenAI with function calling
        # LIMITATION: No timeout handling, no retry logic
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        # Parse response
        assistant_message = response.choices[0].message

        ai_debug_print(f"OpenAI response received")
        ai_debug_print(f"Content: {assistant_message.content}")

        commands = []
        if assistant_message.tool_calls:
            ai_debug_print(f"Tool calls: {len(assistant_message.tool_calls)}")
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                ai_debug_print(f"Tool: {function_name}, Args: {function_args}")

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
        """
        Format canvas state for AI context.

        LIMITATION: Sends full canvas state, may be too verbose for large canvases
        TODO: Consider summarizing or filtering shapes based on viewport
        """
        shapes_summary = []
        for shape in canvas_state.shapes:
            selected_info = f" (selected by {shape.selectedBy[0]})" if shape.selectedBy else ""
            shape_desc = f"- {shape.id}: {shape.type} at ({shape.x}, {shape.y}){selected_info}"

            # Add dimension info
            if shape.type == "rectangle" or shape.type == "text":
                shape_desc += f" size {shape.width}x{shape.height}"
            elif shape.type == "circle":
                shape_desc += f" radius {shape.radius}"

            # Add text content for text shapes
            if shape.type == "text" and shape.text:
                shape_desc += f" text='{shape.text[:30]}...'" if len(shape.text) > 30 else f" text='{shape.text}'"

            shapes_summary.append(shape_desc)

        return f"Total shapes: {len(canvas_state.shapes)}\n" + "\n".join(shapes_summary)

    async def handle_validation_errors(
        self,
        original_message: str,
        errors: List[str],
        canvas_state: Any,
        model: str,
        screenshot: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Ask AI to revise commands after validation errors.

        LIMITATION: Only retries once, not iterative refinement
        TODO: Implement multi-turn refinement with error feedback loop

        Args:
            original_message: User's original message
            errors: List of validation error messages
            canvas_state: Current canvas state
            model: AI model to use
            screenshot: Optional screenshot data (if provided in original request)
        """
        from services.screenshot_utils import (
            validate_screenshot,
            build_geographical_context,
            ai_screenshot_debug_print
        )

        ai_debug_print("Handling validation errors, asking AI to revise")
        ai_debug_print(f"Errors: {errors}")

        error_context = "\n".join([f"- {err}" for err in errors])

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Canvas state:\n{self._format_canvas_state(canvas_state)}"}
        ]

        # Build user content (with or without screenshot)
        user_content = []

        # If screenshot was provided in original request, include it in retry
        # LIMITATION: Screenshot context is included but not re-validated (assumes already validated)
        if screenshot:
            ai_screenshot_debug_print("Including screenshot in validation retry...")

            screenshot_dict = screenshot.model_dump() if hasattr(screenshot, 'model_dump') else (screenshot.dict() if hasattr(screenshot, 'dict') else screenshot)

            # Add image
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{screenshot_dict['format']};base64,{screenshot_dict['data']}"
                }
            })

            # Add geographical context
            geo_context = build_geographical_context(screenshot_dict)
            text_content = f"{geo_context}\n\nUser message: {original_message}"
            user_content.append({
                "type": "text",
                "text": text_content
            })
        else:
            user_content = original_message

        messages.append({"role": "user", "content": user_content})
        messages.append({
            "role": "system",
            "content": f"The following errors occurred:\n{error_context}\n\nPlease suggest alternative commands that avoid these issues."
        })

        response = await self.client.chat.completions.create(
            model=model,
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

        ai_debug_print(f"Revised response with {len(commands)} commands")

        return {
            "message": assistant_message.content or "I've revised my approach.",
            "commands": commands,
            "reasoning": None
        }
