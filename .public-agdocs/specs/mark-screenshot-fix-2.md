in docs/debug_mark_asset/ I've added additional assets fro experimentation: a screenshot sent from the client (screenshot_mock.jpeg) along with the request payload sent from the client (actual_request.json).

- Ignore small pixel differences for now (1-10px), the thing we're testing is off is off by ~100 pixels so we'll focus our efforts on the broad difference.

Of use to your logic:
- the `shapes` in actual_request.json:
    - id=shape_1760807547456 has an topleft (x,y) ~= (0,0)
    - id=rect1 has bottomright ~= bottom right of the canvas (x+width, y+height) ~= (1280, 1260)

## Test Pipeline Setup

**Test Script Created**: `test_mock_screenshot.py`

This script:
1. Loads mock screenshot (docs/debug_mark_assets/screenshot_mock.jpeg)
2. Loads request payload (docs/debug_mark_assets/actual_request.json)
3. Applies coordinate markings using current implementation
4. Overlays shapes from request (purple=rectangles, orange=circles, yellow=text)
5. Saves to debug_screenshots/mock_<counter>.png with auto-incrementing counter
6. Saves metadata to debug_screenshots/mock_<counter>_metadata.json

**Usage**:
```bash
# Run with shape overlays and verbose output
python test_mock_screenshot.py --verbose

# Run without shape overlays
python test_mock_screenshot.py --no-shapes

# Quick run
python test_mock_screenshot.py
```

## Test Results

### Initial Test (mock_1.png) - Before Fix

**Observations**:
- Original screenshot: 1097x1080 pixels (actual image dimensions)
- Viewport info claims: 1277x1322 pixels
- **Issue**: No scaling between canvas coords and screenshot pixels
- Result: Image was cropped/scaled incorrectly

**Key Finding**: Canvas coordinates (1277×1322) represent a logical coordinate space, NOT actual screenshot pixels (1097×1080).

### Issue #1 Fix (mock_2.png) - Coordinate Scaling

**Changes Made**:
1. Modified `CoordinateTranslator.__init__()` to accept `actual_screenshot_size` parameter
2. Added scaling factors:
   - `canvas_to_screen_scale_x = screen_width / canvas_width` (1097/1277 = 0.8590)
   - `canvas_to_screen_scale_y = screen_height / canvas_height` (1080/1322 = 0.8169)
3. Updated `canvas_to_screenshot_pixel()` to apply scaling: `screen_x = canvas_x * scale_x`
4. Updated `screenshot_pixel_to_canvas()` to reverse scaling: `canvas_x = screen_x / scale_x`
5. Modified `ScreenshotMarker` to pass actual image size to translator

**Results** (mock_2.png):
- ✅ **Top-left shape** (shape_1760807547456 at canvas -2,4) correctly appears in top-left corner
- ✅ **Bottom-right shape** (rect1 at canvas 1047,1053) correctly appears in bottom-right corner
- ✅ **Full map visible** - no more cropping
- ✅ **Grid coordinates** properly scaled to screenshot pixels
- ✅ **All shapes** overlay in correct positions

**Status**: Issue #1 (coordinate scaling) is **RESOLVED** ✅

### Issue #2 Fix (mock_5.png) - Y-Offset for Menu Bar

**Problem**: Client sends partial screenshot that crops ~62px menu bar from top
- Screenshot pixel Y=0 (top) should map to canvas Y=62
- Screenshot pixel Y=1080 (bottom) should map to canvas Y=1260
- Visible canvas Y range: [62, 1260] = 1198 canvas pixels
- Previous implementation incorrectly assumed visible canvas height was 1322-62=1260

**Changes Made**:
1. Added `canvas_offset_y` parameter to `CoordinateTranslator.__init__()`
2. **Fixed Y-scale calculation**: `scale_y = screen_height / visible_canvas_height`
   - Visible canvas height = 1260 - 62 = 1198 (NOT 1322 - 62)
   - Scale Y = 1080 / 1198 = 0.9015
3. Modified `canvas_to_screenshot_pixel()`: Subtract offset before scaling
   - `canvas_space_y = canvas_space_y - canvas_offset_y`
   - Then scale: `screen_y = canvas_space_y * scale_y`
4. Modified `screenshot_pixel_to_canvas()`: Scale first, then add offset
   - `canvas_space_y = screen_y / scale_y`
   - Then add offset: `canvas_y = canvas_space_y + canvas_offset_y`
5. Added `--offset-y` argument to test script (default: 62px)
6. Environment variable `AI_SCREENSHOT_OFFSET_Y` for production use

**Results** (mock_5.png with --offset-y 62):
- ✅ **Y-scale factor**: Now 0.9015 (correct for 1198 canvas pixels → 1080 screen pixels)
- ✅ **Visible canvas bounds**: Y range is now 62→1260 (perfect!)
- ✅ **Bottom-right shape** (rect1 at canvas Y=1053): Properly positioned
- ✅ **Grid Y-coordinates**: Show correct range 62→1260
- ✅ **Coordinate transform verified**:
  - Screenshot Y=0 → Canvas Y=62 ✓
  - Screenshot Y=1080 → Canvas Y=1260 ✓
  - Canvas Y=62 → Screenshot Y=0 ✓
  - Canvas Y=1260 → Screenshot Y=1080 ✓

**Status**: Issue #2 (Y-offset for menu bar) is **RESOLVED** ✅

## Summary

Both coordinate transform issues are now fixed:
1. ✅ Canvas coordinate space (1277×1322) scales properly to screenshot pixels (1097×1080)
2. ✅ Y-offset accounts for 62px menu bar cropped from top

**Final Coordinate Transform**:
```
Canvas (x, y) → Screenshot pixel:
  1. Apply viewport transform: (x + pan.x) * zoom, (y + pan.y) * zoom
  2. Subtract Y-offset: y' = y - 62
  3. Scale to pixels: x_px = x * 0.8590, y_px = y' * 0.9015

Screenshot pixel (x_px, y_px) → Canvas (x, y):
  1. Scale to canvas space: x' = x_px / 0.8590, y' = y_px / 0.9015
  2. Add Y-offset: y'' = y' + 62
  3. Reverse viewport transform: x = (x' / zoom) - pan.x, y = (y'' / zoom) - pan.y

Where:
  - X scale: 0.8590 = 1097 / 1277 (screen width / canvas width)
  - Y scale: 0.9015 = 1080 / 1198 (screen height / visible canvas height)
  - Visible canvas height: 1260 - 62 = 1198
  - Y offset: 62px (menu bar cropped from top)
```

**Usage**:
```bash
# Test with correct Y-offset
python test_mock_screenshot.py --verbose --offset-y 62

# Or set via environment
export AI_SCREENSHOT_OFFSET_Y=62
python test_mock_screenshot.py --verbose
```
