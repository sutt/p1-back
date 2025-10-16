"""
AI Validator Service - Basic Proof of Concept

Validates AI-generated commands against collaboration rules and database state.

LIMITATIONS:
- Basic validation only (no complex business logic)
- No async database queries for shape verification (uses in-memory canvas state)
- Coordinate bounds are hardcoded (not based on actual viewport)
- No validation of command sequences (each command validated independently)
- No rate limiting per shape (could spam operations on single shape)
- arrangeShapes command validation is basic (doesn't check layout feasibility)

MANUAL INTERVENTIONS REQUIRED:
- Review and adjust coordinate bounds based on actual canvas size
- Consider adding validation for overlapping shapes
- Consider adding validation for canvas boundaries
- Add business-specific validation rules as needed
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Shape
from typing import Tuple, Dict, Any
import os

# AI_DEBUG environment variable controls debug output
AI_DEBUG = os.getenv("AI_DEBUG", "false").lower() == "true"


def ai_debug_print(message: str):
    """Print debug messages if AI_DEBUG is enabled."""
    if AI_DEBUG:
        print(f"[AI_DEBUG Validator] {message}")


class AIValidator:
    """
    Validator for AI-generated commands.

    LIMITATION: Uses in-memory canvas state snapshot, not real-time DB queries
    This means there's a race condition window between validation and execution.
    For production, consider re-validating on frontend before execution.
    """

    def __init__(self, db: AsyncSession, username: str, canvas_state: Any):
        """
        Initialize validator with current canvas state.

        Args:
            db: Database session (not used in PoC, but available for future)
            username: Current username
            canvas_state: Canvas state snapshot from frontend
        """
        self.db = db
        self.username = username
        self.canvas_state = canvas_state

        # Build shape lookup for quick validation
        self.shapes_by_id = {s.id: s for s in canvas_state.shapes}

        ai_debug_print(f"Initialized validator for user: {username}")
        ai_debug_print(f"Canvas has {len(self.shapes_by_id)} shapes")

    async def validate_command(self, command: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a single AI command.

        LIMITATION: Each command validated independently, no sequence validation
        TODO: Add validation for command sequences (e.g., select before move)

        Args:
            command: Command dictionary with 'action' and 'params'

        Returns:
            Tuple of (is_valid, error_message)
        """
        action = command["action"]
        params = command["params"]

        ai_debug_print(f"Validating command: {action}")

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
            ai_debug_print(f"Unknown command action: {action}")
            return False, f"Unknown command action: {action}"

    def _validate_create_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shape creation parameters.

        LIMITATION: Hardcoded coordinate bounds, no overlap detection
        TODO: Make bounds configurable, add overlap detection
        """
        # Check shape type
        shape_type = params.get("type")
        if shape_type not in ["rectangle", "circle", "text"]:
            ai_debug_print(f"Invalid shape type: {shape_type}")
            return False, f"Invalid shape type: {shape_type}"

        # Check coordinates are reasonable
        # LIMITATION: Hardcoded bounds (-1000 to 5000)
        # TODO: Make bounds configurable via environment variables
        x, y = params.get("x", 0), params.get("y", 0)
        if x < -1000 or x > 5000 or y < -1000 or y > 5000:
            ai_debug_print(f"Coordinates out of bounds: ({x}, {y})")
            return False, f"Coordinates out of reasonable bounds: ({x}, {y})"

        # Validate type-specific requirements
        if shape_type == "rectangle" or shape_type == "text":
            if "width" not in params or "height" not in params:
                ai_debug_print(f"{shape_type} missing width/height")
                return False, f"{shape_type} requires width and height"

            # Check dimensions are positive
            if params.get("width", 0) <= 0 or params.get("height", 0) <= 0:
                ai_debug_print(f"Invalid dimensions for {shape_type}")
                return False, "Width and height must be positive"

        elif shape_type == "circle":
            if "radius" not in params:
                ai_debug_print("Circle missing radius")
                return False, "circle requires radius"

            # Check radius is positive
            if params.get("radius", 0) <= 0:
                ai_debug_print("Invalid radius for circle")
                return False, "Radius must be positive"

        # Check text content for text shapes
        if shape_type == "text" and "text" not in params:
            ai_debug_print("Text shape missing text content")
            return False, "text shape requires text content"

        ai_debug_print(f"createShape validation passed")
        return True, ""

    async def _validate_move_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shape movement.

        LIMITATION: No collision detection, no boundary checking
        """
        shape_id = params.get("shapeId")
        if not shape_id:
            ai_debug_print("moveShape missing shapeId")
            return False, "shapeId is required"

        # Check shape exists in current canvas state
        if shape_id not in self.shapes_by_id:
            ai_debug_print(f"Shape not found: {shape_id}")
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check if shape is selected by another user
        # CRITICAL: This is the main collaboration constraint
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            ai_debug_print(f"Shape {shape_id} selected by {other_user}")
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Check coordinates
        # LIMITATION: Same hardcoded bounds as createShape
        x, y = params.get("x", 0), params.get("y", 0)
        if x < -1000 or x > 5000 or y < -1000 or y > 5000:
            ai_debug_print(f"Move coordinates out of bounds: ({x}, {y})")
            return False, f"Coordinates out of reasonable bounds: ({x}, {y})"

        ai_debug_print(f"moveShape validation passed for {shape_id}")
        return True, ""

    async def _validate_resize_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shape resizing.

        LIMITATION: No min/max size constraints
        """
        shape_id = params.get("shapeId")
        if not shape_id:
            ai_debug_print("resizeShape missing shapeId")
            return False, "shapeId is required"

        if shape_id not in self.shapes_by_id:
            ai_debug_print(f"Shape not found: {shape_id}")
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check selection
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            ai_debug_print(f"Shape {shape_id} selected by {other_user}")
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Validate dimensions are positive
        if "width" in params and params["width"] <= 0:
            ai_debug_print("Invalid width in resize")
            return False, "Width must be positive"
        if "height" in params and params["height"] <= 0:
            ai_debug_print("Invalid height in resize")
            return False, "Height must be positive"
        if "radius" in params and params["radius"] <= 0:
            ai_debug_print("Invalid radius in resize")
            return False, "Radius must be positive"

        ai_debug_print(f"resizeShape validation passed for {shape_id}")
        return True, ""

    async def _validate_select_shape(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shape selection.

        LIMITATION: Doesn't check if user already has another shape selected
        TODO: Add validation for max selections per user
        """
        shape_id = params.get("shapeId")
        if not shape_id:
            ai_debug_print("selectShape missing shapeId")
            return False, "shapeId is required"

        if shape_id not in self.shapes_by_id:
            ai_debug_print(f"Shape not found: {shape_id}")
            return False, f"Shape {shape_id} does not exist"

        shape = self.shapes_by_id[shape_id]

        # Check if already selected by another user
        if shape.selectedBy and shape.selectedBy[0] != self.username:
            other_user = shape.selectedBy[0]
            ai_debug_print(f"Shape {shape_id} selected by {other_user}")
            return False, f"Shape {shape_id} is currently selected by {other_user}"

        ai_debug_print(f"selectShape validation passed for {shape_id}")
        return True, ""

    async def _validate_arrange_shapes(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shape arrangement command.

        LIMITATION: Basic validation only, doesn't check layout feasibility
        TODO: Validate that resulting layout fits in canvas bounds
        """
        shape_ids = params.get("shapeIds", [])
        if not shape_ids:
            ai_debug_print("arrangeShapes missing shapeIds")
            return False, "shapeIds array is required"

        # Check all shapes exist and are available
        for shape_id in shape_ids:
            if shape_id not in self.shapes_by_id:
                ai_debug_print(f"Shape not found in arrange: {shape_id}")
                return False, f"Shape {shape_id} does not exist"

            shape = self.shapes_by_id[shape_id]
            if shape.selectedBy and shape.selectedBy[0] != self.username:
                other_user = shape.selectedBy[0]
                ai_debug_print(f"Shape {shape_id} in arrange selected by {other_user}")
                return False, f"Shape {shape_id} is currently selected by {other_user}"

        # Validate layout type
        layout = params.get("layout")
        if layout not in ["horizontal", "vertical", "grid"]:
            ai_debug_print(f"Invalid layout type: {layout}")
            return False, f"Invalid layout type: {layout}"

        # Grid layout needs rows/cols
        if layout == "grid":
            if "gridRows" not in params or "gridCols" not in params:
                ai_debug_print("Grid layout missing rows/cols")
                return False, "Grid layout requires gridRows and gridCols"

            # Basic sanity check
            rows = params.get("gridRows", 0)
            cols = params.get("gridCols", 0)
            if rows <= 0 or cols <= 0:
                ai_debug_print("Invalid grid dimensions")
                return False, "Grid rows and columns must be positive"

            # Check if enough shapes for grid
            # LIMITATION: Doesn't enforce exact match, allows extras
            if len(shape_ids) < rows * cols:
                ai_debug_print(f"Not enough shapes for {rows}x{cols} grid")
                return False, f"Not enough shapes for {rows}x{cols} grid"

        ai_debug_print(f"arrangeShapes validation passed for {len(shape_ids)} shapes")
        return True, ""
