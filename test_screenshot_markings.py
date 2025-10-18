#!/usr/bin/env python3
"""
Test script for screenshot marking functionality.

MANUAL-INTERVENTION [MARK-SCREENSHOT]: This test requires Pillow to be installed.
Run: pip install pillow>=10.0.0

Usage:
    python test_screenshot_markings.py
"""

import os
import sys
import base64
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_image():
    """
    Create a simple test image using PIL.

    Returns:
        base64 encoded PNG image string
    """
    try:
        from PIL import Image, ImageDraw

        # Create a simple image (800x600, white background)
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)

        # Draw a simple "map" representation
        # Blue water
        draw.rectangle([0, 0, 800, 600], fill='lightblue')

        # Green land
        draw.ellipse([200, 150, 600, 450], fill='lightgreen', outline='darkgreen')

        # Add a label
        draw.text((350, 280), "Boston Common", fill='black')

        # Encode to base64
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')

    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install pillow>=10.0.0")
        sys.exit(1)


def test_coordinate_translation():
    """Test coordinate translation methods."""
    print("\n" + "="*60)
    print("TEST: Coordinate Translation")
    print("="*60)

    from services.coordinate_translator import CoordinateTranslator

    # Test data for Boston Common area
    viewport_info = {
        "width": 800,
        "height": 600,
        "mapCenter": [42.3551, -71.0656],  # Boston Common
        "mapZoom": 15.0,
        "mapBounds": {
            "north": 42.3601,
            "south": 42.3501,
            "east": -71.0606,
            "west": -71.0706
        }
    }

    canvas_state = {
        "viewport": {
            "zoom": 1.0,
            "pan": {"x": 0, "y": 0}
        }
    }

    translator = CoordinateTranslator(viewport_info, canvas_state)

    # Test 1: Map center should be near screen center
    center_lat, center_lng = viewport_info["mapCenter"]
    screen_x, screen_y = translator.latlng_to_screenshot_pixel(center_lat, center_lng)

    print(f"Map center ({center_lat}, {center_lng})")
    print(f"  → Screen coords: ({screen_x}, {screen_y})")
    print(f"  Expected near: ({viewport_info['width']//2}, {viewport_info['height']//2})")

    assert abs(screen_x - 400) < 10, f"Center X should be near 400, got {screen_x}"
    assert abs(screen_y - 300) < 10, f"Center Y should be near 300, got {screen_y}"
    print("  ✓ Center translation correct")

    # Test 2: Reverse translation
    rev_lat, rev_lng = translator.screenshot_pixel_to_latlng(screen_x, screen_y)
    print(f"\nReverse translation ({screen_x}, {screen_y})")
    print(f"  → Lat/lng: ({rev_lat:.6f}, {rev_lng:.6f})")
    print(f"  Original: ({center_lat:.6f}, {center_lng:.6f})")

    assert abs(rev_lat - center_lat) < 0.0001, f"Lat mismatch: {rev_lat} vs {center_lat}"
    assert abs(rev_lng - center_lng) < 0.0001, f"Lng mismatch: {rev_lng} vs {center_lng}"
    print("  ✓ Reverse translation correct")

    # Test 3: Canvas bounds
    min_x, min_y, max_x, max_y = translator.get_visible_canvas_bounds()
    print(f"\nVisible canvas bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  ✓ Canvas bounds calculated")

    return True


def test_screenshot_marking():
    """Test screenshot marking generation."""
    print("\n" + "="*60)
    print("TEST: Screenshot Marking")
    print("="*60)

    # Enable debug mode for this test
    os.environ["AI_DEBUG_SCREENSHOT"] = "true"
    os.environ["AI_SCREENSHOT_COORD_MODE"] = "canvas"

    from services.screenshot_utils import generate_marked_screenshot, dump_marked_screenshot

    # Create test screenshot data
    screenshot_data = {
        "data": create_test_image(),
        "format": "png",
        "capturedAt": "2025-10-17T14:30:00Z",
        "viewportInfo": {
            "width": 800,
            "height": 600,
            "mapCenter": [42.3551, -71.0656],  # Boston Common
            "mapZoom": 15.0,
            "mapBounds": {
                "north": 42.3601,
                "south": 42.3501,
                "east": -71.0606,
                "west": -71.0706
            }
        }
    }

    canvas_state = {
        "shapes": [],
        "viewport": {
            "zoom": 1.0,
            "pan": {"x": 0, "y": 0}
        }
    }

    # Generate marked screenshot
    print("\nGenerating marked screenshot...")
    result = generate_marked_screenshot(screenshot_data, canvas_state, "canvas")

    # Check result
    assert "marked_image_base64" in result, "Missing marked_image_base64"
    assert "coordinate_context" in result, "Missing coordinate_context"

    print("✓ Marked screenshot generated")
    print(f"✓ Marked image size: {len(result['marked_image_base64']) / 1024:.2f}KB (base64)")

    # Check context content
    context = result["coordinate_context"]
    assert "COORDINATE SYSTEM" in context, "Context missing coordinate system info"
    assert "INTEGER" in context, "Context missing integer requirement"
    assert "VISUAL GRID" in context, "Context missing grid info"

    print("✓ Coordinate context generated")
    print(f"\nContext preview:\n{context[:300]}...")

    # Dump to filesystem
    print("\nDumping marked screenshot to debug directory...")
    dump_marked_screenshot(result["marked_image_base64"], "test_markings", "test")

    # Check if file was created
    debug_files = list(Path("./debug_screenshots").glob("screenshot_test_*.png"))
    if debug_files:
        print(f"✓ Debug file created: {debug_files[-1]}")
    else:
        print("⚠ No debug file found (may be expected if debug mode off)")

    return True


def test_full_pipeline():
    """Test the full pipeline with marked screenshots."""
    print("\n" + "="*60)
    print("TEST: Full Pipeline")
    print("="*60)

    os.environ["AI_DEBUG_SCREENSHOT"] = "true"

    from services.screenshot_markers import ScreenshotMarker

    # Create marker
    marker = ScreenshotMarker()
    print("✓ ScreenshotMarker initialized")

    # Create test data
    screenshot_data = {
        "data": create_test_image(),
        "format": "png",
        "capturedAt": "2025-10-17T14:30:00Z",
        "viewportInfo": {
            "width": 800,
            "height": 600,
            "mapCenter": [42.3551, -71.0656],
            "mapZoom": 15.0,
            "mapBounds": {
                "north": 42.3601,
                "south": 42.3501,
                "east": -71.0606,
                "west": -71.0706
            }
        }
    }

    canvas_state = {
        "shapes": [],
        "viewport": {
            "zoom": 1.0,
            "pan": {"x": 0, "y": 0}
        }
    }

    # Generate marked image
    result = marker.mark_screenshot(screenshot_data, canvas_state, "canvas")

    assert "marked_image_base64" in result
    assert "coordinate_context" in result

    print("✓ Full pipeline executed successfully")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SCREENSHOT MARKING TEST SUITE")
    print("="*60)

    print(f"\nEnvironment:")
    print(f"  AI_DEBUG_SCREENSHOT: {os.getenv('AI_DEBUG_SCREENSHOT', 'not set')}")
    print(f"  AI_SCREENSHOT_COORD_MODE: {os.getenv('AI_SCREENSHOT_COORD_MODE', 'not set (defaults to canvas)')}")

    tests = [
        ("Coordinate Translation", test_coordinate_translation),
        ("Screenshot Marking", test_screenshot_marking),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    # Check for debug files
    debug_dir = Path("./debug_screenshots")
    if debug_dir.exists():
        debug_files = list(debug_dir.glob("screenshot_test_*.png"))
        if debug_files:
            print(f"\n✓ Debug files created:")
            for f in debug_files:
                print(f"  - {f}")
            print(f"\nMANUAL-INTERVENTION [MARK-SCREENSHOT]: Review the marked images in ./debug_screenshots/")
            print(f"Look for:")
            print(f"  - Green grid lines every 100 pixels")
            print(f"  - Red crosshair at map center")
            print(f"  - Blue rectangle showing map bounds")
            print(f"  - Coordinate labels on grid lines")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
