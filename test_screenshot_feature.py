#!/usr/bin/env python3
"""
Test script for screenshot feature.

This script tests the basic functionality of the screenshot processing utilities.

MANUAL INTERVENTION REQUIRED:
1. Set OPENAI_API_KEY in .env file before running
2. Set AI_DEBUG_SCREENSHOT=true to see debug output
3. Review debug files in ./debug_screenshots/ after running
4. Clean up debug files manually when done

Usage:
    python test_screenshot_feature.py
"""

import os
import sys
import base64
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.screenshot_utils import (
    validate_screenshot,
    dump_screenshot_to_filesystem,
    dump_full_prompt,
    calculate_coverage_area_miles,
    build_geographical_context,
    ai_screenshot_debug_print
)


def create_test_screenshot_data():
    """
    Create a minimal test screenshot with a tiny 1x1 PNG image.

    This is just for testing the plumbing, not a real screenshot.
    """
    # Tiny 1x1 transparent PNG (67 bytes)
    # This is the smallest valid PNG you can make
    tiny_png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
        0x42, 0x60, 0x82
    ])

    # Encode to base64
    base64_data = base64.b64encode(tiny_png_bytes).decode('utf-8')

    # Create test screenshot data structure
    screenshot_data = {
        "data": base64_data,
        "format": "png",
        "capturedAt": "2025-10-17T14:30:00Z",
        "viewportInfo": {
            "width": 1920,
            "height": 1080,
            "mapCenter": [37.7749, -122.4194],  # San Francisco
            "mapZoom": 15.5,
            "mapBounds": {
                "north": 37.7850,
                "south": 37.7648,
                "east": -122.4094,
                "west": -122.4294
            }
        }
    }

    return screenshot_data


def test_validation():
    """Test screenshot validation."""
    print("\n" + "="*60)
    print("TEST 1: Screenshot Validation")
    print("="*60)

    screenshot = create_test_screenshot_data()
    is_valid, error = validate_screenshot(screenshot)

    print(f"✓ Validation result: {is_valid}")
    if error:
        print(f"✗ Error: {error}")
        return False

    # Test invalid data
    print("\nTesting invalid data...")

    invalid_tests = [
        ({"data": "", "format": "png", "viewportInfo": {"mapCenter": [0, 0], "mapZoom": 10}}, "Missing data"),
        ({"data": "abc", "format": "invalid", "viewportInfo": {"mapCenter": [0, 0], "mapZoom": 10}}, "Invalid format"),
        ({"data": "abc", "format": "png", "viewportInfo": {"mapCenter": [200, 0], "mapZoom": 10}}, "Invalid latitude"),
        ({"data": "abc", "format": "png", "viewportInfo": {"mapCenter": [0, 200], "mapZoom": 10}}, "Invalid longitude"),
        ({"data": "abc", "format": "png", "viewportInfo": {"mapCenter": [0, 0], "mapZoom": 50}}, "Invalid zoom"),
    ]

    for invalid_screenshot, description in invalid_tests:
        is_valid, error = validate_screenshot(invalid_screenshot)
        if is_valid:
            print(f"✗ {description} should have failed validation")
            return False
        else:
            print(f"✓ {description} failed validation as expected: {error}")

    return True


def test_coverage_calculation():
    """Test coverage area calculation."""
    print("\n" + "="*60)
    print("TEST 2: Coverage Area Calculation")
    print("="*60)

    test_cases = [
        (15.5, 37.7749, "San Francisco at zoom 15.5"),
        (13.0, 37.7749, "San Francisco at zoom 13.0"),
        (18.0, 37.7749, "San Francisco at zoom 18.0"),
        (15.0, 0.0, "Equator at zoom 15.0"),
    ]

    for zoom, lat, description in test_cases:
        coverage = calculate_coverage_area_miles(zoom, lat)
        print(f"✓ {description}: {coverage:.2f} miles")

    return True


def test_geographical_context():
    """Test geographical context building."""
    print("\n" + "="*60)
    print("TEST 3: Geographical Context Building")
    print("="*60)

    screenshot = create_test_screenshot_data()
    context = build_geographical_context(screenshot)

    print(f"Context:\n{context}")

    # Verify key elements are present
    required_elements = [
        "37.774900",  # Latitude
        "-122.419400",  # Longitude
        "15.5",  # Zoom
        "miles",  # Coverage unit
        "bounds",  # Bounds info
    ]

    for element in required_elements:
        if element in context:
            print(f"✓ Context contains '{element}'")
        else:
            print(f"✗ Context missing '{element}'")
            return False

    return True


def test_debug_utilities():
    """Test debug file dumping."""
    print("\n" + "="*60)
    print("TEST 4: Debug Utilities")
    print("="*60)

    # Check if debugging is enabled
    debug_enabled = os.getenv("AI_DEBUG_SCREENSHOT", "false").lower() == "true"
    print(f"Debug mode: {'ENABLED' if debug_enabled else 'DISABLED'}")

    if not debug_enabled:
        print("⚠ Set AI_DEBUG_SCREENSHOT=true to test debug utilities")
        return True

    screenshot = create_test_screenshot_data()
    request_id = "test_001"

    # Test screenshot dumping
    print("\nDumping test screenshot...")
    dump_screenshot_to_filesystem(screenshot, request_id)

    # Check if file was created
    debug_dir = Path("./debug_screenshots")
    screenshot_files = list(debug_dir.glob(f"screenshot_*_{request_id}.*"))

    if screenshot_files:
        print(f"✓ Screenshot dumped: {screenshot_files[0]}")
        print(f"  File size: {screenshot_files[0].stat().st_size} bytes")
    else:
        print("✗ Screenshot file not found")
        return False

    # Test prompt dumping
    print("\nDumping test prompt...")
    test_messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "Test user message"}
    ]
    dump_full_prompt(test_messages, request_id)

    # Check if file was created
    prompt_files = list(debug_dir.glob(f"prompt_*_{request_id}.txt"))

    if prompt_files:
        print(f"✓ Prompt dumped: {prompt_files[0]}")
        print(f"  File size: {prompt_files[0].stat().st_size} bytes")

        # Read and display first few lines
        with open(prompt_files[0], 'r') as f:
            lines = f.readlines()[:10]
            print("\n  First few lines of prompt file:")
            for line in lines:
                print(f"    {line.rstrip()}")
    else:
        print("✗ Prompt file not found")
        return False

    return True


def test_pydantic_model_integration():
    """Test that screenshot data works with Pydantic models."""
    print("\n" + "="*60)
    print("TEST 5: Pydantic Model Integration")
    print("="*60)

    try:
        from routes.ai import ScreenshotData, ViewportInfo, MapBounds

        screenshot = create_test_screenshot_data()

        # Try to create Pydantic model from dict
        screenshot_model = ScreenshotData(**screenshot)

        print(f"✓ ScreenshotData model created")
        print(f"  Format: {screenshot_model.format}")
        print(f"  Captured at: {screenshot_model.capturedAt}")
        print(f"  Map center: {screenshot_model.viewportInfo.mapCenter}")
        print(f"  Zoom: {screenshot_model.viewportInfo.mapZoom}")

        # Test .dict() conversion
        screenshot_dict = screenshot_model.dict()
        is_valid, error = validate_screenshot(screenshot_dict)

        if is_valid:
            print(f"✓ Pydantic model converts to valid dict")
        else:
            print(f"✗ Pydantic model dict validation failed: {error}")
            return False

        return True

    except Exception as e:
        print(f"✗ Error testing Pydantic integration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SCREENSHOT FEATURE TEST SUITE")
    print("="*60)

    print(f"\nEnvironment:")
    print(f"  AI_DEBUG_SCREENSHOT: {os.getenv('AI_DEBUG_SCREENSHOT', 'not set')}")
    print(f"  OPENAI_API_KEY: {'set' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")

    tests = [
        ("Validation", test_validation),
        ("Coverage Calculation", test_coverage_calculation),
        ("Geographical Context", test_geographical_context),
        ("Debug Utilities", test_debug_utilities),
        ("Pydantic Model Integration", test_pydantic_model_integration),
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

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
