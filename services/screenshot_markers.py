"""
Screenshot marking utilities.

Draws visual annotations on screenshots to help AI understand coordinate systems.

MANUAL-INTERVENTION [MARK-SCREENSHOT]: Requires Pillow installed (pip install pillow>=10.0.0)
"""

import os
import io
import base64
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from services.coordinate_translator import CoordinateTranslator


# Module-level flag for coordinate mode
COORD_MODE = os.getenv("AI_SCREENSHOT_COORD_MODE", "canvas")


def ai_marking_debug_print(message: str):
    """Print debug messages if screenshot debugging is enabled."""
    debug_enabled = os.getenv("AI_DEBUG_SCREENSHOT", "false").lower() == "true"
    if debug_enabled:
        print(f"[AI-MARKING-DEBUG] {message}")


class ScreenshotMarker:
    """
    Adds visual coordinate markings to screenshots.

    LIMITATION [MARK-SCREENSHOT]: Basic implementation with simplified drawing.
    Does not support:
    - Custom fonts (uses PIL default)
    - Advanced anti-aliasing
    - Dynamic marking density based on image size
    - Intelligent marking placement to avoid map features
    """

    def __init__(self):
        """
        Initialize screenshot marker.

        LIMITATION [MARK-SCREENSHOT]: Configuration is hardcoded for simplicity.
        In production, should be configurable via environment or config object.
        """
        # Visual style settings
        # LIMITATION [MARK-SCREENSHOT]: Colors are hardcoded
        self.grid_color = (0, 255, 0, 80)  # Semi-transparent green
        self.center_color = (255, 0, 0, 255)  # Red
        self.bounds_color = (0, 0, 255, 150)  # Blue
        self.text_color = (255, 255, 255, 255)  # White
        self.text_bg_color = (0, 0, 0, 180)  # Semi-transparent black

        # Grid spacing
        self.canvas_grid_spacing = int(os.getenv("AI_SCREENSHOT_GRID_SPACING", "100"))

        # Font (use PIL default)
        # LIMITATION [MARK-SCREENSHOT]: Uses default PIL font which is small
        # Production should use a proper font file
        try:
            # Try to load a better font if available
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            # Fallback to default
            self.font = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

    def mark_screenshot(
        self,
        screenshot_data: Dict[str, Any],
        canvas_state: Dict[str, Any],
        coord_mode: str = "canvas"
    ) -> Dict[str, Any]:
        """
        Add markings to screenshot and return marked version.

        LIMITATION [MARK-SCREENSHOT]: Only generates one marked version.
        Plan called for separate AI and debug versions, but for simplicity
        this implementation creates one version used for both.

        Args:
            screenshot_data: Original screenshot with base64 image
            canvas_state: Canvas state with viewport info
            coord_mode: "canvas" or "latlng" (currently only canvas implemented)

        Returns:
            dict with:
                - marked_image_base64: Marked image for AI
                - coordinate_context: Text description of coordinate system
        """
        ai_marking_debug_print(f"Starting screenshot marking (mode: {coord_mode})...")

        # Decode base64 image
        image = self._decode_image(screenshot_data["data"])
        ai_marking_debug_print(f"Decoded image: {image.size[0]}x{image.size[1]}")

        # Create translator with actual screenshot size
        # This allows scaling from canvas coordinates to actual screenshot pixels
        translator = CoordinateTranslator(
            screenshot_data["viewportInfo"],
            canvas_state,
            actual_screenshot_size=(image.size[0], image.size[1])
        )

        ai_marking_debug_print(f"Canvas coords: {translator.canvas_width}x{translator.canvas_height}")
        ai_marking_debug_print(f"Screenshot pixels: {translator.screen_width}x{translator.screen_height}")
        ai_marking_debug_print(f"Scale factors: x={translator.canvas_to_screen_scale_x:.4f}, y={translator.canvas_to_screen_scale_y:.4f}")

        # Create marked version
        # LIMITATION [MARK-SCREENSHOT]: Only canvas mode implemented for basic PoC
        if coord_mode == "canvas":
            marked_image = self._mark_canvas_mode(image, translator)
            context = self._generate_canvas_context(translator)
        else:
            # LIMITATION [MARK-SCREENSHOT]: Lat/lng mode not yet implemented
            ai_marking_debug_print("Lat/lng mode not implemented, falling back to canvas mode")
            marked_image = self._mark_canvas_mode(image, translator)
            context = self._generate_canvas_context(translator)

        # Encode back to base64
        marked_base64 = self._encode_image(marked_image, screenshot_data.get("format", "jpeg"))
        ai_marking_debug_print(f"Marked image encoded")

        return {
            "marked_image_base64": marked_base64,
            "coordinate_context": context
        }

    def _decode_image(self, base64_data: str) -> Image.Image:
        """
        Decode base64 image data to PIL Image.

        Args:
            base64_data: Base64 encoded image

        Returns:
            PIL Image object
        """
        image_bytes = base64.b64decode(base64_data)
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    def _encode_image(self, image: Image.Image, format: str = "png") -> str:
        """
        Encode PIL Image to base64.

        LIMITATION [MARK-SCREENSHOT]: Always outputs as PNG regardless of input format.
        PNG is better for marked images (graphics/text) but larger than JPEG.

        Args:
            image: PIL Image object
            format: Desired format (ignored, always uses PNG)

        Returns:
            Base64 encoded image string
        """
        # Convert to RGB if saving as JPEG
        # For marked images, PNG is better (lossless, supports transparency)
        buffer = io.BytesIO()

        # Always save as PNG for marked images
        # LIMITATION [MARK-SCREENSHOT]: Ignores format parameter
        image.save(buffer, format="PNG")

        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')

    def _mark_canvas_mode(self, image: Image.Image, translator: CoordinateTranslator) -> Image.Image:
        """
        Add canvas coordinate markings to image.

        LIMITATION [MARK-SCREENSHOT]: Basic marking implementation.
        Could be improved with:
        - Adaptive grid density based on zoom level
        - More sophisticated label placement
        - Highlighting of specific areas of interest

        Args:
            image: Original image
            translator: Coordinate translator

        Returns:
            Marked image
        """
        # Create a copy to draw on
        marked = image.copy()
        draw = ImageDraw.Draw(marked, 'RGBA')

        ai_marking_debug_print("Drawing canvas coordinate markings...")

        # 1. Draw grid
        self._draw_canvas_grid(draw, translator, image.size)

        # 2. Draw map center marker
        self._draw_map_center(draw, translator, image.size)

        # 3. Draw map bounds rectangle (if available)
        self._draw_map_bounds(draw, translator, image.size)

        # 4. Draw canvas bounds label
        self._draw_canvas_bounds_label(draw, translator, image.size)

        ai_marking_debug_print("Finished drawing markings")

        return marked

    def _draw_canvas_grid(self, draw: ImageDraw.Draw, translator: CoordinateTranslator, image_size: Tuple[int, int]):
        """
        Draw canvas coordinate grid.

        LIMITATION [MARK-SCREENSHOT]: Fixed grid spacing (100 pixels by default).
        Should adapt to zoom level and image size for optimal density.
        """
        width, height = image_size
        min_x, min_y, max_x, max_y = translator.get_visible_canvas_bounds()

        ai_marking_debug_print(f"Visible canvas bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")

        # Draw vertical lines (constant X canvas coordinates)
        # LIMITATION [MARK-SCREENSHOT]: May draw too many or too few lines
        # depending on zoom level and canvas size
        grid_spacing = self.canvas_grid_spacing
        start_x = (min_x // grid_spacing) * grid_spacing

        for canvas_x in range(start_x, max_x + grid_spacing, grid_spacing):
            screen_x, _ = translator.canvas_to_screenshot_pixel(canvas_x, 0)

            if 0 <= screen_x <= width:
                # Draw vertical line
                draw.line([(screen_x, 0), (screen_x, height)], fill=self.grid_color, width=1)

                # Label at top
                label = f"x:{canvas_x}"
                # LIMITATION [MARK-SCREENSHOT]: Text positioning is approximate
                self._draw_text_with_background(draw, (screen_x + 2, 2), label, self.font)

        # Draw horizontal lines (constant Y canvas coordinates)
        start_y = (min_y // grid_spacing) * grid_spacing

        for canvas_y in range(start_y, max_y + grid_spacing, grid_spacing):
            _, screen_y = translator.canvas_to_screenshot_pixel(0, canvas_y)

            if 0 <= screen_y <= height:
                # Draw horizontal line
                draw.line([(0, screen_y), (width, screen_y)], fill=self.grid_color, width=1)

                # Label at left
                label = f"y:{canvas_y}"
                self._draw_text_with_background(draw, (2, screen_y + 2), label, self.font)

    def _draw_map_center(self, draw: ImageDraw.Draw, translator: CoordinateTranslator, image_size: Tuple[int, int]):
        """
        Draw marker at map center.

        LIMITATION [MARK-SCREENSHOT]: Simple crosshair. Could be more visually distinct.
        """
        center_screen_x, center_screen_y = translator.get_map_center_in_screen_coords()

        # Get canvas coordinates of center for label
        center_canvas_x, center_canvas_y = translator.screenshot_pixel_to_canvas(center_screen_x, center_screen_y)

        ai_marking_debug_print(f"Map center: screen ({center_screen_x}, {center_screen_y}), canvas ({center_canvas_x}, {center_canvas_y})")

        # Draw crosshair
        crosshair_size = 20
        # Horizontal line
        draw.line([
            (center_screen_x - crosshair_size, center_screen_y),
            (center_screen_x + crosshair_size, center_screen_y)
        ], fill=self.center_color, width=2)
        # Vertical line
        draw.line([
            (center_screen_x, center_screen_y - crosshair_size),
            (center_screen_x, center_screen_y + crosshair_size)
        ], fill=self.center_color, width=2)

        # Draw circle at center
        circle_radius = 5
        draw.ellipse([
            (center_screen_x - circle_radius, center_screen_y - circle_radius),
            (center_screen_x + circle_radius, center_screen_y + circle_radius)
        ], outline=self.center_color, width=2)

        # Label
        label = f"Center: ({center_canvas_x}, {center_canvas_y})"
        # Position label to the right of crosshair
        label_x = center_screen_x + crosshair_size + 5
        label_y = center_screen_y - 10
        self._draw_text_with_background(draw, (label_x, label_y), label, self.font_large, bg_color=self.center_color)

    def _draw_map_bounds(self, draw: ImageDraw.Draw, translator: CoordinateTranslator, image_size: Tuple[int, int]):
        """
        Draw rectangle showing map bounds.

        LIMITATION [MARK-SCREENSHOT]: Only draws if bounds provided in viewport info.
        """
        bounds_screen = translator.get_map_bounds_in_screen_coords()

        if not bounds_screen:
            ai_marking_debug_print("No map bounds to draw")
            return

        x_min, y_min, x_max, y_max = bounds_screen
        ai_marking_debug_print(f"Map bounds: screen ({x_min}, {y_min}) to ({x_max}, {y_max})")

        # Draw rectangle
        draw.rectangle([x_min, y_min, x_max, y_max], outline=self.bounds_color, width=2)

        # Label corners with canvas coordinates
        # Top-left
        tl_canvas = translator.screenshot_pixel_to_canvas(x_min, y_min)
        self._draw_text_with_background(draw, (x_min + 5, y_min + 5),
                                        f"({tl_canvas[0]}, {tl_canvas[1]})",
                                        self.font, bg_color=self.bounds_color)

        # Bottom-right
        br_canvas = translator.screenshot_pixel_to_canvas(x_max, y_max)
        self._draw_text_with_background(draw, (x_max - 80, y_max - 20),
                                        f"({br_canvas[0]}, {br_canvas[1]})",
                                        self.font, bg_color=self.bounds_color)

    def _draw_canvas_bounds_label(self, draw: ImageDraw.Draw, translator: CoordinateTranslator, image_size: Tuple[int, int]):
        """
        Draw label showing visible canvas area.

        LIMITATION [MARK-SCREENSHOT]: Positioned at bottom-left corner.
        May overlap with map content or other markings.
        """
        min_x, min_y, max_x, max_y = translator.get_visible_canvas_bounds()

        label = f"Canvas visible: ({min_x}, {min_y}) to ({max_x}, {max_y})"

        # Position at bottom-left
        width, height = image_size
        self._draw_text_with_background(draw, (10, height - 30), label, self.font_large)

    def _draw_text_with_background(
        self,
        draw: ImageDraw.Draw,
        position: Tuple[int, int],
        text: str,
        font,
        bg_color: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Draw text with semi-transparent background for readability.

        LIMITATION [MARK-SCREENSHOT]: Text bounding box calculation is approximate.
        May not perfectly fit all text.

        Args:
            draw: ImageDraw object
            position: (x, y) position for text
            text: Text to draw
            font: Font to use
            bg_color: Optional background color (defaults to text_bg_color)
        """
        x, y = position

        # Get text bounding box
        # LIMITATION [MARK-SCREENSHOT]: textbbox may not be available in older PIL versions
        try:
            bbox = draw.textbbox((x, y), text, font=font)
            # Add padding
            padding = 2
            bg_box = [
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding
            ]
        except AttributeError:
            # Fallback for older PIL versions
            # LIMITATION [MARK-SCREENSHOT]: Approximate size
            text_width = len(text) * 7
            text_height = 15
            bg_box = [x - 2, y - 2, x + text_width + 2, y + text_height + 2]

        # Draw background
        draw.rectangle(bg_box, fill=bg_color or self.text_bg_color)

        # Draw text
        draw.text((x, y), text, fill=self.text_color, font=font)

    def _generate_canvas_context(self, translator: CoordinateTranslator) -> str:
        """
        Generate textual description of canvas coordinate system.

        This context is added to the AI prompt to explain the marking system.

        LIMITATION [MARK-SCREENSHOT]: Static template. Could be more dynamic
        based on actual visible features and coordinate ranges.

        Args:
            translator: Coordinate translator

        Returns:
            Formatted context string
        """
        min_x, min_y, max_x, max_y = translator.get_visible_canvas_bounds()
        center_screen_x, center_screen_y = translator.get_map_center_in_screen_coords()
        center_canvas_x, center_canvas_y = translator.screenshot_pixel_to_canvas(center_screen_x, center_screen_y)

        context = f"""
VISUAL COORDINATE MARKINGS:

The image contains visual markings to help you understand the coordinate system:

1. COORDINATE SYSTEM:
   - Canvas uses INTEGER pixel coordinates
   - Origin (0,0) is at the TOP-LEFT corner
   - X axis increases RIGHTWARD (left to right)
   - Y axis increases DOWNWARD (top to bottom)
   - All shape coordinates MUST be integers

2. VISUAL GRID:
   - GREEN grid lines are drawn every {self.canvas_grid_spacing} canvas units
   - Grid line labels show canvas coordinates (e.g., "x:500", "y:300")
   - Use these gridlines to estimate canvas coordinates for locations in the image

3. MAP CENTER:
   - RED crosshair marks the map center
   - Map center is at canvas coordinates: ({center_canvas_x}, {center_canvas_y})
   - This helps you orient the coordinate system

4. MAP BOUNDS:
   - BLUE rectangle shows the geographical bounds of the map
   - Corner labels show canvas coordinates of the bounds

5. VISIBLE CANVAS AREA:
   - Currently visible canvas area: ({min_x}, {min_y}) to ({max_x}, {max_y})
   - Width: {max_x - min_x} pixels, Height: {max_y - min_y} pixels

INSTRUCTIONS FOR CREATING SHAPES:
1. Look at the map and identify where you want to place a shape
2. Use the green grid lines to estimate the canvas coordinates
3. The grid spacing is {self.canvas_grid_spacing} pixels - use this to interpolate between lines
4. Remember: coordinates increase right and down from the top-left origin
5. Create shapes using INTEGER canvas coordinates (x, y)

EXAMPLE: To place a shape at "Boston Common":
- Find the Boston Common in the image
- Count gridlines to estimate its position
- If Boston Common appears near the center, it's approximately at ({center_canvas_x}, {center_canvas_y})
- Adjust based on the actual visual location relative to gridlines
""".strip()

        return context
