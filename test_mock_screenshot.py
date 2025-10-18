#!/usr/bin/env python3
"""
Test script for processing the mock screenshot with actual request data.

This script:
1. Loads the mock screenshot (docs/debug_mark_assets/screenshot_mock.jpeg)
2. Loads the request payload (docs/debug_mark_assets/actual_request.json)
3. Applies coordinate markings using the current implementation
4. Overlays the shapes from the request onto the screenshot
5. Saves the result to debug_screenshots/mock_<counter>.png

Usage:
    python test_mock_screenshot.py [--no-shapes] [--verbose]

Options:
    --no-shapes: Don't overlay the shapes from the request
    --verbose: Enable debug output
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_next_counter() -> int:
    """
    Get the next counter value for output filenames.

    Reads from debug_screenshots/.counter file, increments, and writes back.

    Returns:
        int: Next counter value
    """
    counter_file = Path("./debug_screenshots/.counter")
    counter_file.parent.mkdir(exist_ok=True)

    if counter_file.exists():
        try:
            counter = int(counter_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            counter = 0
    else:
        counter = 0

    # Increment and save
    next_counter = counter + 1
    counter_file.write_text(str(next_counter))

    return next_counter


def load_mock_screenshot() -> str:
    """
    Load the mock screenshot and encode to base64.

    Returns:
        str: Base64 encoded screenshot
    """
    screenshot_path = Path("docs/debug_mark_assets/screenshot_mock.jpeg")

    if not screenshot_path.exists():
        raise FileNotFoundError(f"Mock screenshot not found at {screenshot_path}")

    screenshot_bytes = screenshot_path.read_bytes()
    return base64.b64encode(screenshot_bytes).decode('utf-8')


def load_actual_request() -> Dict[str, Any]:
    """
    Load the actual request JSON payload.

    Returns:
        dict: Request payload
    """
    request_path = Path("docs/debug_mark_assets/actual_request.json")

    if not request_path.exists():
        raise FileNotFoundError(f"Request payload not found at {request_path}")

    return json.loads(request_path.read_text())


def draw_shapes_on_image(image, shapes, translator, draw_module):
    """
    Draw the shapes from the request onto the image.

    Args:
        image: PIL Image object
        shapes: List of shape objects from request
        translator: CoordinateTranslator instance
        draw_module: ImageDraw module (PIL.ImageDraw)
    """
    draw = draw_module.Draw(image, 'RGBA')

    # Colors for shapes (semi-transparent)
    shape_colors = {
        'circle': (255, 165, 0, 100),  # Orange
        'rectangle': (128, 0, 128, 100),  # Purple
        'text': (255, 255, 0, 100)  # Yellow
    }
    outline_colors = {
        'circle': (255, 165, 0, 255),  # Orange
        'rectangle': (128, 0, 128, 255),  # Purple
        'text': (255, 255, 0, 255)  # Yellow
    }

    for shape in shapes:
        shape_type = shape.get('type')
        shape_id = shape.get('id')

        # Convert canvas coords to screen coords
        canvas_x = shape.get('x', 0)
        canvas_y = shape.get('y', 0)
        screen_x, screen_y = translator.canvas_to_screenshot_pixel(canvas_x, canvas_y)

        print(f"  Shape {shape_id} ({shape_type}): canvas ({canvas_x}, {canvas_y}) → screen ({screen_x}, {screen_y})")

        if shape_type == 'circle':
            radius = shape.get('radius', 50)
            # Scale radius by canvas zoom
            screen_radius = int(radius * translator.canvas_zoom)

            # Draw circle
            bbox = [
                screen_x - screen_radius,
                screen_y - screen_radius,
                screen_x + screen_radius,
                screen_y + screen_radius
            ]
            draw.ellipse(bbox, fill=shape_colors['circle'], outline=outline_colors['circle'], width=3)

            # Draw center point
            draw.ellipse([screen_x-3, screen_y-3, screen_x+3, screen_y+3], fill=outline_colors['circle'])

        elif shape_type == 'rectangle':
            width = shape.get('width', 100)
            height = shape.get('height', 100)

            # Scale by canvas zoom
            screen_width = int(width * translator.canvas_zoom)
            screen_height = int(height * translator.canvas_zoom)

            # Draw rectangle (x, y is top-left)
            bbox = [
                screen_x,
                screen_y,
                screen_x + screen_width,
                screen_y + screen_height
            ]
            draw.rectangle(bbox, fill=shape_colors['rectangle'], outline=outline_colors['rectangle'], width=3)

            # Draw corner marker
            draw.ellipse([screen_x-3, screen_y-3, screen_x+3, screen_y+3], fill=outline_colors['rectangle'])

        elif shape_type == 'text':
            width = shape.get('width', 200)
            height = shape.get('height', 50)
            text_content = shape.get('text', '')

            # Scale by canvas zoom
            screen_width = int(width * translator.canvas_zoom)
            screen_height = int(height * translator.canvas_zoom)

            # Draw text box
            bbox = [
                screen_x,
                screen_y,
                screen_x + screen_width,
                screen_y + screen_height
            ]
            draw.rectangle(bbox, fill=shape_colors['text'], outline=outline_colors['text'], width=2)

            # Draw text if available
            if text_content:
                try:
                    from PIL import ImageFont
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                    except:
                        font = ImageFont.load_default()

                    # Draw text in center of box
                    text_x = screen_x + 5
                    text_y = screen_y + 5
                    draw.text((text_x, text_y), text_content, fill=(0, 0, 0, 255), font=font)
                except:
                    pass

    return image


def save_marked_image(marked_base64: str, counter: int, metadata: Dict[str, Any]) -> Path:
    """
    Save the marked image to debug_screenshots directory.

    Args:
        marked_base64: Base64 encoded marked image
        counter: Counter value for filename
        metadata: Metadata to save alongside the image

    Returns:
        Path: Path to saved image
    """
    output_dir = Path("./debug_screenshots")
    output_dir.mkdir(exist_ok=True)

    # Save image
    output_path = output_dir / f"mock_{counter}.png"
    image_bytes = base64.b64decode(marked_base64)
    output_path.write_bytes(image_bytes)

    # Save metadata
    metadata_path = output_dir / f"mock_{counter}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return output_path


def main():
    """Main test script."""
    parser = argparse.ArgumentParser(description='Process mock screenshot with markings')
    parser.add_argument('--no-shapes', action='store_true', help='Don\'t overlay shapes from request')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose debug output')
    parser.add_argument('--offset-y', type=int, default=62, help='Y-offset in canvas coords (default: 62px for menu bar)')
    args = parser.parse_args()

    # Enable debug output if requested
    if args.verbose:
        os.environ["AI_DEBUG_SCREENSHOT"] = "true"

    # Set Y-offset for coordinate translation
    os.environ["AI_SCREENSHOT_OFFSET_Y"] = str(args.offset_y)

    print("="*60)
    print("MOCK SCREENSHOT MARKING TEST")
    print("="*60)

    # Load assets
    print("\n[1/5] Loading mock assets...")
    try:
        screenshot_base64 = load_mock_screenshot()
        print("  ✓ Loaded screenshot_mock.jpeg")

        request_data = load_actual_request()
        print("  ✓ Loaded actual_request.json")

        # Print key info about the request
        shapes = request_data.get('canvasState', {}).get('shapes', [])
        viewport_info = request_data.get('screenshot', {}).get('viewportInfo', {})
        print(f"  → Found {len(shapes)} shapes")
        print(f"  → Viewport: {viewport_info.get('width')}x{viewport_info.get('height')}")
        print(f"  → Map center: {viewport_info.get('mapCenter')}")
        print(f"  → Map zoom: {viewport_info.get('mapZoom')}")

    except Exception as e:
        print(f"  ✗ Error loading assets: {e}")
        return 1

    # Prepare screenshot data structure
    print("\n[2/5] Preparing screenshot data...")
    screenshot_data = {
        "data": screenshot_base64,
        "format": "jpeg",
        "capturedAt": request_data['screenshot'].get('capturedAt', '2025-10-18T17:13:30.957Z'),
        "viewportInfo": viewport_info
    }

    canvas_state = request_data.get('canvasState', {
        "shapes": [],
        "viewport": {"zoom": 1.0, "pan": {"x": 0, "y": 0}}
    })

    print(f"  ✓ Canvas viewport: zoom={canvas_state['viewport']['zoom']}, pan={canvas_state['viewport']['pan']}")

    # Generate markings
    print("\n[3/5] Generating coordinate markings...")
    try:
        from services.screenshot_markers import ScreenshotMarker
        from services.coordinate_translator import CoordinateTranslator
        from PIL import Image, ImageDraw
        import io

        marker = ScreenshotMarker()
        result = marker.mark_screenshot(screenshot_data, canvas_state, "canvas")

        print("  ✓ Coordinate markings generated")
        print(f"  → Marked image size: {len(result['marked_image_base64']) / 1024:.1f}KB")

    except Exception as e:
        print(f"  ✗ Error generating markings: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Overlay shapes if requested
    if not args.no_shapes and shapes:
        print(f"\n[4/5] Overlaying {len(shapes)} shapes from request...")
        try:
            # Decode marked image
            marked_bytes = base64.b64decode(result['marked_image_base64'])
            marked_image = Image.open(io.BytesIO(marked_bytes)).convert("RGBA")

            # Create translator with actual screenshot size and Y-offset
            canvas_offset_y = int(os.environ.get("AI_SCREENSHOT_OFFSET_Y", "0"))
            translator = CoordinateTranslator(
                viewport_info,
                canvas_state,
                actual_screenshot_size=(marked_image.size[0], marked_image.size[1]),
                canvas_offset_y=canvas_offset_y
            )

            # Draw shapes
            marked_image = draw_shapes_on_image(marked_image, shapes, translator, ImageDraw)

            # Re-encode
            buffer = io.BytesIO()
            marked_image.save(buffer, format="PNG")
            buffer.seek(0)
            result['marked_image_base64'] = base64.b64encode(buffer.read()).decode('utf-8')

            print("  ✓ Shapes overlaid on marked image")

        except Exception as e:
            print(f"  ⚠ Error overlaying shapes: {e}")
            import traceback
            traceback.print_exc()
            print("  → Continuing with markings only...")
    else:
        print(f"\n[4/5] Skipping shape overlay (--no-shapes or no shapes in request)")

    # Save output
    print("\n[5/5] Saving output...")
    try:
        counter = get_next_counter()

        metadata = {
            "counter": counter,
            "timestamp": request_data['screenshot'].get('capturedAt'),
            "viewport_info": viewport_info,
            "canvas_state": canvas_state,
            "shapes_count": len(shapes),
            "shapes_overlaid": not args.no_shapes and len(shapes) > 0,
            "test_notes": {
                "shape_1760807547456": "Top-left corner shape (x,y) ≈ (0,0)",
                "rect1": "Bottom-right corner shape (x+w, y+h) ≈ (1280, 1260)"
            }
        }

        output_path = save_marked_image(result['marked_image_base64'], counter, metadata)

        print(f"  ✓ Saved to: {output_path}")
        print(f"  ✓ Metadata: {output_path.parent / f'mock_{counter}_metadata.json'}")
        print(f"  → Counter: {counter}")

    except Exception as e:
        print(f"  ✗ Error saving output: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print(f"\nOutput file: {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Open {output_path} to review the markings")
    print(f"  2. Compare with docs/debug_mark_assets/screenshot_mock.jpeg")
    print(f"  3. Check if:")
    print(f"     - shape_1760807547456 (purple rect) appears at top-left")
    print(f"     - rect1 (purple rect) appears at bottom-right")
    print(f"     - Grid coordinates align with shape positions")
    print(f"  4. Note any coordinate discrepancies (expected ~100px off)")
    print(f"  5. Update coord-transform-debug-plan.md with findings")

    return 0


if __name__ == "__main__":
    sys.exit(main())
