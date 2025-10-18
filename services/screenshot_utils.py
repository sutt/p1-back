"""
Screenshot processing utilities for AI chat.

This module provides basic PoC functionality for processing screenshots with map context.

LIMITATIONS:
- Debugging utilities dump files to repo root (./debug_screenshots/)
- No cleanup of debug files (manual intervention required)
- Validation is basic (no malicious content scanning)
- No image optimization/resizing on backend

TODO for production:
- Add automatic cleanup of debug files
- Implement more robust validation
- Add image virus scanning
- Consider image optimization
- Add secure storage for screenshots if persistence is needed
"""

import os
import base64
import math
from typing import Optional, Dict, Any
from datetime import datetime


# Module-level flag for debugging (set via environment variable)
DEBUG_SCREENSHOT = os.getenv("AI_DEBUG_SCREENSHOT", "false").lower() == "true"
DEBUG_DIR = "./debug_screenshots"


def ai_screenshot_debug_print(message: str):
    """Print debug messages if screenshot debugging is enabled."""
    if DEBUG_SCREENSHOT:
        print(f"[AI-SCREENSHOT-DEBUG] {message}")


def validate_screenshot(screenshot: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate screenshot data.

    LIMITATION: Basic validation only. Does not scan for malicious content.
    TODO: Add virus scanning, image format verification

    Args:
        screenshot: Screenshot data dict from request

    Returns:
        Tuple of (is_valid, error_message)
    """
    ai_screenshot_debug_print("Validating screenshot data...")

    # Check required fields
    if not screenshot.get("data"):
        return False, "Missing screenshot data"

    if not screenshot.get("format"):
        return False, "Missing image format"

    if screenshot["format"] not in ["png", "jpeg"]:
        return False, f"Invalid format: {screenshot['format']}. Must be 'png' or 'jpeg'"

    if not screenshot.get("viewportInfo"):
        return False, "Missing viewport info"

    # Validate base64 format (basic check)
    # LIMITATION: This doesn't validate if it's actually a valid image
    data = screenshot["data"]
    try:
        # Try to decode a small portion to check validity
        base64.b64decode(data[:100])
    except Exception as e:
        return False, f"Invalid base64 data: {str(e)}"

    # Check size (max 10MB base64)
    # Formula: base64 is roughly 4/3 the size of original binary
    size_bytes = (len(data) * 3) / 4
    max_size = 10 * 1024 * 1024  # 10MB
    if size_bytes > max_size:
        ai_screenshot_debug_print(f"Screenshot too large: {size_bytes / 1024 / 1024:.2f}MB")
        return False, f"Screenshot too large: {size_bytes / 1024 / 1024:.2f}MB (max 10MB)"

    ai_screenshot_debug_print(f"Screenshot size: {size_bytes / 1024:.2f}KB")

    # Validate viewport info
    viewport = screenshot["viewportInfo"]

    if not isinstance(viewport.get("mapCenter"), list) or len(viewport["mapCenter"]) != 2:
        return False, "Invalid mapCenter: must be [lat, lng]"

    lat, lng = viewport["mapCenter"]

    # Validate coordinates
    if not (-90 <= lat <= 90):
        return False, f"Invalid latitude: {lat} (must be between -90 and 90)"

    if not (-180 <= lng <= 180):
        return False, f"Invalid longitude: {lng} (must be between -180 and 180)"

    # Validate zoom level
    zoom = viewport.get("mapZoom", 0)
    if not (0 <= zoom <= 22):
        return False, f"Invalid zoom level: {zoom} (must be between 0 and 22)"

    ai_screenshot_debug_print("Screenshot validation passed")
    return True, None


def dump_screenshot_to_filesystem(screenshot: Dict[str, Any], request_id: Optional[str] = None):
    """
    Dump decoded screenshot to filesystem for debugging.

    LIMITATION: Dumps to repo root directory. Files must be manually cleaned up.
    MANUAL INTERVENTION: Developers must delete files in ./debug_screenshots/ periodically

    Args:
        screenshot: Screenshot data dict
        request_id: Optional request identifier for filename
    """
    if not DEBUG_SCREENSHOT:
        return

    ai_screenshot_debug_print("Dumping screenshot to filesystem for debugging...")

    # Create debug directory if it doesn't exist
    os.makedirs(DEBUG_DIR, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    req_id = request_id or "unknown"
    format_ext = screenshot.get("format", "png")
    filename = f"screenshot_{timestamp}_{req_id}.{format_ext}"
    filepath = os.path.join(DEBUG_DIR, filename)

    try:
        # Decode base64 and write to file
        image_data = base64.b64decode(screenshot["data"])
        with open(filepath, "wb") as f:
            f.write(image_data)

        ai_screenshot_debug_print(f"Screenshot dumped to: {filepath}")
        ai_screenshot_debug_print(f"File size: {len(image_data) / 1024:.2f}KB")

    except Exception as e:
        ai_screenshot_debug_print(f"Failed to dump screenshot: {str(e)}")


def dump_full_prompt(prompt_content: Any, request_id: Optional[str] = None):
    """
    Dump the full prompt being sent to the API for debugging.

    LIMITATION: Dumps to repo root directory. Files must be manually cleaned up.
    MANUAL INTERVENTION: Developers must delete files in ./debug_screenshots/ periodically

    Args:
        prompt_content: The full prompt/messages array being sent to API
        request_id: Optional request identifier for filename
    """
    if not DEBUG_SCREENSHOT:
        return

    ai_screenshot_debug_print("Dumping full prompt to filesystem for debugging...")

    # Create debug directory if it doesn't exist
    os.makedirs(DEBUG_DIR, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    req_id = request_id or "unknown"
    filename = f"prompt_{timestamp}_{req_id}.txt"
    filepath = os.path.join(DEBUG_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # Write a readable version of the prompt
            f.write("=== FULL PROMPT DEBUG DUMP ===\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Request ID: {req_id}\n")
            f.write("\n=== PROMPT CONTENT ===\n\n")

            # Format based on type
            if isinstance(prompt_content, list):
                for idx, item in enumerate(prompt_content):
                    f.write(f"\n--- Message {idx + 1} ---\n")
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if key == "content" and isinstance(value, list):
                                # Multi-part content (image + text)
                                f.write(f"{key}:\n")
                                for content_idx, content_item in enumerate(value):
                                    f.write(f"  Part {content_idx + 1}: {content_item.get('type', 'unknown')}\n")
                                    if content_item.get("type") == "image":
                                        # Don't dump the full base64, just metadata
                                        source = content_item.get("source", {})
                                        data_len = len(source.get("data", ""))
                                        f.write(f"    media_type: {source.get('media_type', 'unknown')}\n")
                                        f.write(f"    data_length: {data_len} chars (~{data_len * 3 / 4 / 1024:.2f}KB)\n")
                                    elif content_item.get("type") == "text":
                                        f.write(f"    text: {content_item.get('text', '')}\n")
                            else:
                                # Simple key-value
                                value_str = str(value)
                                if len(value_str) > 500:
                                    value_str = value_str[:500] + "... (truncated)"
                                f.write(f"{key}: {value_str}\n")
                    else:
                        f.write(f"{str(item)}\n")
            else:
                f.write(str(prompt_content))

        ai_screenshot_debug_print(f"Full prompt dumped to: {filepath}")

    except Exception as e:
        ai_screenshot_debug_print(f"Failed to dump prompt: {str(e)}")


def calculate_coverage_area_miles(zoom: float, latitude: float) -> float:
    """
    Calculate approximate coverage area in miles based on zoom level.

    Formula based on Web Mercator projection at equator.

    LIMITATION: Approximation only. Actual coverage varies by:
    - Map projection
    - Screen aspect ratio
    - Latitude (coverage is wider at equator)

    Args:
        zoom: Map zoom level (0-22)
        latitude: Latitude of map center (for adjustment)

    Returns:
        Approximate coverage area in miles
    """
    # Earth's circumference at equator in miles
    earth_circumference = 24901

    # At zoom level 0, one tile covers entire earth
    # Each zoom level doubles the number of tiles (halves the coverage)
    tiles_at_zoom = math.pow(2, zoom)
    miles_per_tile = earth_circumference / tiles_at_zoom

    # Adjust for latitude (map is wider at equator, narrower at poles)
    latitude_adjustment = math.cos(math.radians(latitude))

    coverage = miles_per_tile * latitude_adjustment

    ai_screenshot_debug_print(f"Calculated coverage area: {coverage:.2f} miles at zoom {zoom}, lat {latitude}")

    return coverage


def build_geographical_context(screenshot: Dict[str, Any]) -> str:
    """
    Build geographical context string from screenshot viewport info.

    This context helps the AI understand the spatial context of the map view.

    LIMITATION: Assumes standard lat/lng coordinates in WGS84 format.
    TODO: Handle different coordinate systems if needed

    Args:
        screenshot: Screenshot data dict with viewportInfo

    Returns:
        Formatted geographical context string
    """
    ai_screenshot_debug_print("Building geographical context...")

    viewport = screenshot["viewportInfo"]
    lat, lng = viewport["mapCenter"]
    zoom = viewport["mapZoom"]

    # Calculate approximate coverage
    coverage = calculate_coverage_area_miles(zoom, lat)

    # Build context string
    context = f"The user is viewing a map centered at {lat:.6f}°N, {lng:.6f}°E"
    context += f" at zoom level {zoom:.1f}."
    context += f" The visible area covers approximately {coverage:.2f} miles."

    # Add bounds if available
    if viewport.get("mapBounds"):
        bounds = viewport["mapBounds"]
        context += f"\nGeographical bounds: {bounds.get('north', 0):.4f}°N to {bounds.get('south', 0):.4f}°S, "
        context += f"{bounds.get('west', 0):.4f}°W to {bounds.get('east', 0):.4f}°E."

    ai_screenshot_debug_print(f"Geographical context: {context}")

    return context


def generate_marked_screenshot(
    screenshot: Dict[str, Any],
    canvas_state: Dict[str, Any],
    coord_mode: str = "canvas"
) -> Dict[str, Any]:
    """
    Generate marked version of screenshot with coordinate annotations.

    MANUAL-INTERVENTION [MARK-SCREENSHOT]: Requires Pillow installed.
    Run: pip install pillow>=10.0.0

    LIMITATION [MARK-SCREENSHOT]: Basic implementation creates one marked image.
    Plan called for separate AI and debug versions, but this creates one version
    for simplicity.

    Args:
        screenshot: Original screenshot data dict
        canvas_state: Canvas state dict with viewport info
        coord_mode: "canvas" or "latlng" (only canvas implemented)

    Returns:
        Dictionary with:
            - marked_image_base64: Marked image for AI (PNG format)
            - coordinate_context: Text description of coordinate system
    """
    ai_screenshot_debug_print("Generating marked screenshot...")

    try:
        from services.screenshot_markers import ScreenshotMarker

        marker = ScreenshotMarker()
        result = marker.mark_screenshot(screenshot, canvas_state, coord_mode)

        ai_screenshot_debug_print("Marked screenshot generated successfully")

        return result

    except ImportError as e:
        # LIMITATION [MARK-SCREENSHOT]: If Pillow not installed, fall back to unmarked
        ai_screenshot_debug_print(f"Failed to import screenshot_markers (Pillow may not be installed): {e}")
        ai_screenshot_debug_print("Falling back to unmarked screenshot")

        # Return original screenshot with basic context
        return {
            "marked_image_base64": screenshot["data"],
            "coordinate_context": "WARNING: Screenshot marking unavailable (Pillow not installed). Using unmarked image."
        }

    except Exception as e:
        # LIMITATION [MARK-SCREENSHOT]: If marking fails, fall back gracefully
        ai_screenshot_debug_print(f"Failed to generate marked screenshot: {e}")
        ai_screenshot_debug_print("Falling back to unmarked screenshot")

        # Return original screenshot
        return {
            "marked_image_base64": screenshot["data"],
            "coordinate_context": f"WARNING: Screenshot marking failed ({str(e)}). Using unmarked image."
        }


def dump_marked_screenshot(base64_data: str, request_id: str, purpose: str = "marked"):
    """
    Dump marked screenshot to filesystem for debugging.

    MANUAL-INTERVENTION [MARK-SCREENSHOT]: Debug files in ./debug_screenshots/
    must be manually cleaned up. No automatic cleanup is performed.

    Args:
        base64_data: Base64 encoded marked image
        request_id: Request identifier
        purpose: Purpose label for filename (e.g., "marked", "debug")
    """
    if not DEBUG_SCREENSHOT:
        return

    ai_screenshot_debug_print(f"Dumping {purpose} screenshot...")

    # Create debug directory if it doesn't exist
    os.makedirs(DEBUG_DIR, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{purpose}_{timestamp}_{request_id}.png"
    filepath = os.path.join(DEBUG_DIR, filename)

    try:
        # Decode base64 and write to file
        image_data = base64.b64decode(base64_data)
        with open(filepath, "wb") as f:
            f.write(image_data)

        ai_screenshot_debug_print(f"{purpose.capitalize()} screenshot dumped to: {filepath}")
        ai_screenshot_debug_print(f"File size: {len(image_data) / 1024:.2f}KB")

    except Exception as e:
        ai_screenshot_debug_print(f"Failed to dump {purpose} screenshot: {str(e)}")
