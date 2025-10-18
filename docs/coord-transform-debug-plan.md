# Coordinate Transform Debugging Plan

## Problem Statement

The coordinate transformations in the screenshot marking feature are producing inaccurate results. Grid lines, center markers, and bounds are not aligning with the actual map positions.

**Symptoms**:
- Grid line coordinates don't match mouse cursor coordinates in web app
- Map center marker appears in wrong location
- Map bounds rectangle doesn't align with visible map area

## Root Cause Analysis

The coordinate transformation chain involves multiple steps, each with potential issues:

```
Lat/Lng (map) → Web Mercator (meters) → Screen Pixels → Canvas Coords
```

**Potential Issues**:
1. **Assumption Mismatch**: Canvas viewport transformation assumptions incorrect
2. **Projection Issues**: Web Mercator calculations off
3. **Center Alignment**: Map center not actually at screen center
4. **Scale Issues**: Pixels-per-meter calculation incorrect
5. **Coordinate System**: Canvas coordinates don't match expected system
6. **Viewport State**: Canvas zoom/pan not properly accounted for

## Debugging Strategy

Order of investigation (easiest → hardest):

1. **Quick Sanity Checks** - Verify basic assumptions (5-10 min)
2. **Simple Tests** - Test with known coordinates (15-20 min)
3. **Frontend Validation** - Add debug output from frontend (30 min)
4. **Iterative Fixes** - Try solutions in order of likelihood (1-2 hours)
5. **Deep Debugging** - Detailed coordinate logging (1-2 hours if needed)
6. **Advanced Solutions** - Implement better coordinate system (later if needed)

---

## Phase 1: Quick Sanity Checks (Start Here!)

### Check 1: Map Center Alignment

**Quick Test**:
```python
# In your test or debug console
from services.coordinate_translator import CoordinateTranslator

viewport_info = {
    "width": 1920,
    "height": 1080,
    "mapCenter": [42.3551, -71.0656],  # Boston Common
    "mapZoom": 15.0
}

canvas_state = {
    "viewport": {"zoom": 1.0, "pan": {"x": 0, "y": 0}}
}

translator = CoordinateTranslator(viewport_info, canvas_state)

# Map center should convert to near screen center
center_x, center_y = translator.latlng_to_screenshot_pixel(42.3551, -71.0656)

print(f"Map center → Screen: ({center_x}, {center_y})")
print(f"Expected screen center: ({1920//2}, {1080//2}) = (960, 540)")
print(f"Difference: ({abs(center_x - 960)}, {abs(center_y - 540)}) pixels")
```

**Expected Result**: Difference should be < 5 pixels

**If Fails**: Map center calculation is wrong → See Fix 1

---

### Check 2: Canvas Init State

**Question**: What is the initial canvas viewport state?

**Expected** (assumption in code):
```javascript
canvas_state = {
  viewport: {
    zoom: 1.0,
    pan: {x: 0, y: 0}
  }
}
```

**Action**: Verify with frontend team what the actual initial state is.

**Possible Issues**:
- Canvas zoom is not 1.0 initially
- Canvas pan is not (0, 0) initially
- Canvas coordinates don't start at (0, 0)

**If Different**: Canvas transformation assumptions wrong → See Fix 2

---

### Check 3: Screen = Canvas Assumption

**Current Assumption**: Screenshot pixel coordinates ≈ Canvas coordinates (when zoom=1.0, pan=0,0)

**Quick Test**:
```python
# With initial canvas state (zoom=1.0, pan=0,0)
screen_x, screen_y = 500, 300
canvas_x, canvas_y = translator.screenshot_pixel_to_canvas(screen_x, screen_y)

print(f"Screen (500, 300) → Canvas ({canvas_x}, {canvas_y})")
print(f"Expected: (500, 300) or close")
```

**Expected**: Should be identical or very close

**If Not**: Canvas coordinate system is different → See Fix 3

---

### Check 4: Coordinate System Direction

**Question**: Does canvas Y increase downward or upward?

**Current Assumption**: Y increases downward (standard screen coords)

**Quick Test in Web App**:
1. Click top of canvas - note coordinates
2. Click bottom of canvas - note coordinates
3. Compare: Bottom Y should be > Top Y

**If Bottom Y < Top Y**: Y axis is inverted → See Fix 4

---

## Phase 2: Simple Coordinate Tests

### Test 1: Four Corners Test

**Setup**: Request a screenshot with known map bounds

**Test**:
```python
# Using the bounds from the screenshot
bounds = viewport_info["mapBounds"]

# Convert all four corners
nw = translator.latlng_to_screenshot_pixel(bounds["north"], bounds["west"])
ne = translator.latlng_to_screenshot_pixel(bounds["north"], bounds["east"])
sw = translator.latlng_to_screenshot_pixel(bounds["south"], bounds["west"])
se = translator.latlng_to_screenshot_pixel(bounds["south"], bounds["east"])

print(f"NW corner: {nw} (should be near top-left)")
print(f"NE corner: {ne} (should be near top-right)")
print(f"SW corner: {sw} (should be near bottom-left)")
print(f"SE corner: {se} (should be near bottom-right)")

# Sanity checks
assert nw[0] < ne[0], "NW should be left of NE"
assert nw[1] < sw[1], "NW should be above SW"
assert ne[1] < se[1], "NE should be above SE"
assert sw[0] < se[0], "SW should be left of SE"
```

**If Any Fail**: Coordinate transformation is fundamentally wrong → See Fix 5

---

### Test 2: Grid Line Validation

**Manual Test**:
1. Generate marked screenshot with debug mode on
2. Open marked image
3. Find a grid line labeled "x:500"
4. Measure pixel position of that line (should be at x=500 pixels from left)
5. Repeat for "y:300"

**Expected**: Grid line position matches label (±5 pixels)

**If Off**: Grid drawing or labeling logic incorrect → See Fix 6

---

### Test 3: Mouse Coordinate Comparison

**Manual Test** (requires frontend cooperation):
1. Open web app with map visible
2. Enable coordinate display on mouse cursor (see Frontend Debug Plan below)
3. Take screenshot
4. Generate marked screenshot
5. Compare coordinates:
   - Mouse at (800, 600) canvas coords
   - Should align with grid line intersection near "x:800", "y:600"

**If Misaligned**: Full coordinate chain needs investigation → See Fix 7

---

## Phase 3: Frontend Debug Utilities

### Frontend Debug Plan 1: Mouse Coordinate Display (Easiest)

**Request from Frontend Team**:

Add a coordinate display overlay that shows:
- Current mouse position in canvas coordinates
- Current mouse position in screen coordinates
- Current map center lat/lng
- Current canvas viewport state (zoom, pan)

**Implementation** (5-10 minutes for frontend):
```javascript
// Add to map component
const [mouseCoords, setMouseCoords] = useState({ canvas: null, screen: null });

const handleMouseMove = (e) => {
  // Get screen coordinates
  const screen = { x: e.clientX, y: e.clientY };

  // Get canvas coordinates (depends on your canvas implementation)
  const canvas = screenToCanvas(screen);

  // Get map lat/lng at cursor
  const latlng = map.unproject([e.clientX, e.clientY]);

  setMouseCoords({ screen, canvas, latlng });
};

// Display in corner of screen
{mouseCoords.canvas && (
  <div style={{ position: 'fixed', top: 10, right: 10, background: 'rgba(0,0,0,0.7)', color: 'white', padding: 10 }}>
    Canvas: ({mouseCoords.canvas.x}, {mouseCoords.canvas.y})<br/>
    Screen: ({mouseCoords.screen.x}, {mouseCoords.screen.y})<br/>
    Lat/Lng: ({mouseCoords.latlng.lat.toFixed(6)}, {mouseCoords.latlng.lng.toFixed(6)})
  </div>
)}
```

**Usage**:
1. Enable coordinate display
2. Move mouse to map center → note coordinates
3. Move mouse to known location → note coordinates
4. Compare with backend calculations

---

### Frontend Debug Plan 2: Screenshot Metadata Validation (Medium)

**Request from Frontend Team**:

When capturing screenshot, log all metadata to console:

```javascript
const captureScreenshot = () => {
  const mapCenter = map.getCenter();
  const mapZoom = map.getZoom();
  const mapBounds = map.getBounds();
  const canvasViewport = getCanvasViewport(); // Your canvas state

  const metadata = {
    mapCenter: [mapCenter.lat, mapCenter.lng],
    mapZoom: mapZoom,
    mapBounds: {
      north: mapBounds.getNorth(),
      south: mapBounds.getSouth(),
      east: mapBounds.getEast(),
      west: mapBounds.getWest()
    },
    canvasViewport: canvasViewport,
    screenSize: {
      width: window.innerWidth,
      height: window.innerHeight
    }
  };

  console.log("Screenshot Metadata:", JSON.stringify(metadata, null, 2));

  // Also display prominently
  alert(`Map Center: ${metadata.mapCenter}\nZoom: ${metadata.mapZoom}\nCanvas: ${JSON.stringify(metadata.canvasViewport)}`);

  // Proceed with screenshot capture...
};
```

**Usage**:
1. Capture screenshot
2. Copy logged metadata
3. Use in backend test to reproduce exact scenario
4. Compare backend calculations with frontend reality

---

### Frontend Debug Plan 3: Known Point Markers (Later if needed)

**Request from Frontend Team**:

Add feature to place markers at specific canvas coordinates:

```javascript
const placeTestMarkers = () => {
  const testPoints = [
    { canvas: {x: 0, y: 0}, label: "Origin" },
    { canvas: {x: 500, y: 500}, label: "Test Point" },
    { canvas: {x: 1000, y: 1000}, label: "Test Point 2" },
  ];

  testPoints.forEach(point => {
    // Convert canvas to lat/lng
    const latlng = canvasToLatLng(point.canvas);

    // Place marker on map
    new mapboxgl.Marker({ color: 'red' })
      .setLngLat([latlng.lng, latlng.lat])
      .setPopup(new mapboxgl.Popup().setText(`${point.label}\nCanvas: (${point.canvas.x}, ${point.canvas.y})`))
      .addTo(map);
  });
};
```

**Usage**:
1. Place markers at known canvas coordinates
2. Capture screenshot
3. Check if backend grid lines align with markers
4. Reveals if canvas→lat/lng conversion differs between frontend/backend

---

## Phase 4: Iterative Fixes (Most Likely → Least Likely)

### Fix 1: Canvas Viewport Transformation [MOST LIKELY]

**Hypothesis**: The canvas viewport transformation formula is wrong.

**Current Code**:
```python
# In screenshot_pixel_to_canvas()
canvas_x = int((screen_x / self.canvas_zoom) - self.canvas_pan["x"])
canvas_y = int((screen_y / self.canvas_zoom) - self.canvas_pan["y"])
```

**Potential Issues**:
- Pan direction might be reversed (+ vs -)
- Zoom might be applied differently
- Order of operations might be wrong

**Fix Attempts** (try in order):

**Attempt 1a**: Reverse pan direction
```python
canvas_x = int((screen_x / self.canvas_zoom) + self.canvas_pan["x"])
canvas_y = int((screen_y / self.canvas_zoom) + self.canvas_pan["y"])
```

**Attempt 1b**: Change zoom application
```python
canvas_x = int(screen_x - self.canvas_pan["x"]) / self.canvas_zoom
canvas_y = int(screen_y - self.canvas_pan["y"]) / self.canvas_zoom
```

**Attempt 1c**: Different formula entirely
```python
# Pan first, then scale
canvas_x = int((screen_x - self.canvas_pan["x"]) / self.canvas_zoom)
canvas_y = int((screen_y - self.canvas_pan["y"]) / self.canvas_zoom)
```

**How to Test**:
1. Make the change in `coordinate_translator.py`
2. Run test: `python test_screenshot_markings.py`
3. Generate marked screenshot
4. Check if grid aligns better

**Validation**:
Ask frontend: "What is your formula for screen→canvas conversion?"

---

### Fix 2: Screen ≠ Canvas (Simplest Assumption Fix)

**Hypothesis**: With initial state, screen coordinates ARE canvas coordinates.

**Current Code Assumes**: Complex transformation even at zoom=1.0, pan=(0,0)

**Simpler Fix**:
```python
def screenshot_pixel_to_canvas(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
    """Convert screenshot pixel coordinates to canvas coordinates."""

    # SIMPLIFICATION: If canvas at initial state, screen = canvas
    if self.canvas_zoom == 1.0 and self.canvas_pan["x"] == 0 and self.canvas_pan["y"] == 0:
        return (screen_x, screen_y)

    # Otherwise, apply transformation
    canvas_x = int((screen_x - self.canvas_pan["x"]) / self.canvas_zoom)
    canvas_y = int((screen_y - self.canvas_pan["y"]) / self.canvas_zoom)
    return (canvas_x, canvas_y)
```

**How to Test**:
1. Ensure request has canvas zoom=1.0, pan=(0,0)
2. Regenerate marked screenshot
3. Check if grid coordinates match screen positions

---

### Fix 3: Pixels Per Meter Calculation

**Hypothesis**: The zoom→pixels_per_meter formula is incorrect.

**Current Formula**:
```python
self.pixels_per_meter = (256 * math.pow(2, self.map_zoom)) / (2 * math.pi * self.EARTH_RADIUS)
```

**This Assumes**: 256x256 tiles at zoom 0, which is standard but might not match your map.

**Alternative Formulas**:

**Attempt 3a**: Use different tile size
```python
# If using 512x512 tiles
self.pixels_per_meter = (512 * math.pow(2, self.map_zoom)) / (2 * math.pi * self.EARTH_RADIUS)
```

**Attempt 3b**: Calculate from known distance
```python
# If you know map bounds and screen size, calculate directly
def _calculate_pixels_per_meter_from_bounds(self):
    """Calculate based on actual visible distance."""
    # Convert bounds to meters
    nw_x, nw_y = self.latlng_to_web_mercator(bounds["north"], bounds["west"])
    se_x, se_y = self.latlng_to_web_mercator(bounds["south"], bounds["east"])

    width_meters = se_x - nw_x
    height_meters = nw_y - se_y  # Y is inverted

    # Pixels per meter based on screen size
    ppm_x = self.screen_width / width_meters
    ppm_y = self.screen_height / height_meters

    # Use average
    return (ppm_x + ppm_y) / 2
```

**How to Test**:
1. Measure known distance on map (e.g., 1 mile = 1609 meters)
2. Measure corresponding pixel distance in screenshot
3. Calculate actual pixels per meter
4. Compare with formula output

---

### Fix 4: Y-Axis Inversion

**Hypothesis**: Y-axis direction is inverted somewhere.

**Current Code**:
```python
# In latlng_to_screenshot_pixel()
pixel_offset_y = -offset_y * self.pixels_per_meter  # Y is inverted
```

**If Y-axis is actually not inverted**:
```python
pixel_offset_y = offset_y * self.pixels_per_meter  # Don't invert
```

**How to Test**:
1. Pick a point north of center
2. Convert to screen coordinates
3. Y should be < screen_height/2 (above center)
4. If Y > screen_height/2, inversion is wrong

---

### Fix 5: Map Not Centered in Screenshot

**Hypothesis**: Map viewport doesn't fill entire screenshot. UI elements (toolbars, etc.) offset the map.

**Current Assumption**: Map fills entire screenshot from (0,0) to (width, height)

**Reality Check**: Are there UI elements that reduce the visible map area?

**Fix**:
```python
class CoordinateTranslator:
    def __init__(self, viewport_info, canvas_state, map_offset=(0, 0), map_size=None):
        # ...existing code...

        # Map might not start at (0,0)
        self.map_offset_x = map_offset[0]
        self.map_offset_y = map_offset[1]

        # Map might be smaller than screen
        self.map_width = map_size[0] if map_size else self.screen_width
        self.map_height = map_size[1] if map_size else self.screen_height

    def latlng_to_screenshot_pixel(self, lat, lng):
        # ... convert to map-relative coordinates ...
        map_relative_x = int((self.map_width / 2) + pixel_offset_x)
        map_relative_y = int((self.map_height / 2) + pixel_offset_y)

        # Convert to screen coordinates
        screen_x = map_relative_x + self.map_offset_x
        screen_y = map_relative_y + self.map_offset_y

        return (screen_x, screen_y)
```

**How to Test**:
1. Measure map viewport in screenshot (might not be full screen)
2. If map is offset or smaller, provide those values
3. Regenerate with correct map bounds

---

### Fix 6: Web Mercator Projection Issues

**Hypothesis**: Web Mercator formulas are incorrect.

**Current Implementation**: Standard Web Mercator

**Alternative**: Use Mapbox's projection directly if available

**Fix**: Ask frontend to provide Web Mercator coordinates for test points:
```javascript
// In frontend
const testLatLng = [42.3551, -71.0656];
const mercatorCoords = mapboxgl.MercatorCoordinate.fromLngLat(testLatLng);
console.log("Mercator X:", mercatorCoords.x);
console.log("Mercator Y:", mercatorCoords.y);
```

Then verify backend calculations match.

---

### Fix 7: Complete Coordinate System Redesign [LAST RESORT]

**If all else fails**: Don't use Web Mercator at all.

**Alternative Approach**: Use frontend-provided coordinate mappings.

**New Request Schema**:
```typescript
interface ScreenshotData {
  data: string;
  format: string;
  viewportInfo: {
    // ... existing fields ...

    // NEW: Frontend provides coordinate mapping
    coordinateMapping: {
      // Known points: screen pixel → canvas coords
      referencePoints: [
        { screen: {x: 0, y: 0}, canvas: {x: 100, y: 200} },
        { screen: {x: 1920, y: 0}, canvas: {x: 2020, y: 200} },
        { screen: {x: 0, y: 1080}, canvas: {x: 100, y: 1280} },
        { screen: {x: 1920, y: 1080}, canvas: {x: 2020, y: 1280} },
      ],
      // Or simpler: transformation matrix
      transform: {
        scale: {x: 1.0, y: 1.0},
        offset: {x: 0, y: 0}
      }
    }
  }
}
```

**Backend**: Use provided mappings directly instead of calculating.

---

## Phase 5: Deep Debugging (If Still Broken)

### Debug Tool 1: Coordinate Logging

Add verbose logging to track every transformation:

```python
def latlng_to_screenshot_pixel(self, lat: float, lng: float) -> Tuple[int, int]:
    """Convert lat/lng to screenshot pixel with verbose logging."""

    print(f"\n=== Converting ({lat}, {lng}) to screen ===")

    # Step 1: Convert to Web Mercator
    merc_x, merc_y = self.latlng_to_web_mercator(lat, lng)
    print(f"Step 1 - Web Mercator: ({merc_x:.2f}, {merc_y:.2f}) meters")

    # Step 2: Get center in Web Mercator
    center_merc_x, center_merc_y = self.latlng_to_web_mercator(*self.map_center)
    print(f"Step 2 - Center Mercator: ({center_merc_x:.2f}, {center_merc_y:.2f}) meters")

    # Step 3: Calculate offset
    offset_x = merc_x - center_merc_x
    offset_y = merc_y - center_merc_y
    print(f"Step 3 - Offset: ({offset_x:.2f}, {offset_y:.2f}) meters")

    # Step 4: Convert to pixels
    pixel_offset_x = offset_x * self.pixels_per_meter
    pixel_offset_y = -offset_y * self.pixels_per_meter
    print(f"Step 4 - Pixel offset: ({pixel_offset_x:.2f}, {pixel_offset_y:.2f}) px")
    print(f"    (pixels_per_meter: {self.pixels_per_meter:.6f})")

    # Step 5: Add to screen center
    screen_x = int((self.screen_width / 2) + pixel_offset_x)
    screen_y = int((self.screen_height / 2) + pixel_offset_y)
    print(f"Step 5 - Screen coords: ({screen_x}, {screen_y})")
    print(f"    (screen center: ({self.screen_width/2}, {self.screen_height/2}))")

    return (screen_x, screen_y)
```

**Usage**: Run with test coordinates and analyze each step.

---

### Debug Tool 2: Visual Comparison Tool

Create a simple HTML tool to overlay marked image on original:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Coordinate Debug Comparison</title>
  <style>
    .container {
      position: relative;
      display: inline-block;
    }
    .original, .marked {
      position: absolute;
      top: 0;
      left: 0;
    }
    .marked {
      opacity: 0.5;
    }
  </style>
</head>
<body>
  <div class="container">
    <img class="original" src="screenshot_original.jpeg">
    <img class="marked" src="screenshot_marked.png">
  </div>
  <div>
    <label>Overlay Opacity: <input type="range" min="0" max="100" value="50" oninput="document.querySelector('.marked').style.opacity = this.value/100"></label>
  </div>
  <div>
    <button onclick="document.querySelector('.marked').style.display = 'none'">Hide Marked</button>
    <button onclick="document.querySelector('.marked').style.display = 'block'">Show Marked</button>
  </div>
</body>
</html>
```

Slide opacity to compare alignment.

---

## Phase 6: Validation Checklist

Once you think it's fixed, validate with these tests:

### ✅ Test 1: Map Center
- [ ] Red crosshair appears at visual center of map
- [ ] Crosshair label coordinates match expected canvas coords
- [ ] Crosshair is within 10 pixels of actual center

### ✅ Test 2: Grid Alignment
- [ ] Grid line labeled "x:500" is at 500 pixels from left edge
- [ ] Grid line labeled "y:500" is at 500 pixels from top edge
- [ ] Grid spacing is correct (default 100 pixels)

### ✅ Test 3: Bounds Rectangle
- [ ] Blue rectangle roughly matches visible map area
- [ ] Corner labels have reasonable coordinates
- [ ] Rectangle is not way off screen

### ✅ Test 4: Known Location
- [ ] Place cursor on known landmark (e.g., Boston Common)
- [ ] Note canvas coordinates from frontend debug display
- [ ] Those coordinates should align with nearest grid intersection
- [ ] Accuracy within ±20 pixels is acceptable

### ✅ Test 5: Different Zoom Levels
- [ ] Test at zoom 13 (wider area)
- [ ] Test at zoom 15 (medium)
- [ ] Test at zoom 17 (close up)
- [ ] All should have accurate markings

### ✅ Test 6: Different Canvas States
- [ ] Test with canvas zoom = 1.0
- [ ] Test with canvas zoom = 0.5
- [ ] Test with canvas pan offset
- [ ] All should transform correctly

---

## Debugging Priority Matrix

| Issue | Likelihood | Ease to Fix | Test Time | Priority |
|-------|-----------|-------------|-----------|----------|
| Canvas viewport formula wrong | High | Easy | 5 min | 🔴 **Do First** |
| Screen = Canvas assumption | High | Very Easy | 2 min | 🔴 **Do First** |
| Map not centered | Medium | Easy | 5 min | 🟡 Do Second |
| Pixels per meter calc | Medium | Medium | 10 min | 🟡 Do Second |
| Y-axis inversion | Low | Easy | 5 min | 🟢 Do Third |
| Web Mercator issues | Low | Hard | 30 min | 🟢 Do Third |
| Complete redesign | Last Resort | Very Hard | 2+ hours | ⚫ Last Resort |

---

## Quick Reference: Most Common Fixes

### 90% of issues are one of these:

1. **Canvas transform formula wrong**: Try all variations in Fix 1
2. **Screen = Canvas when zoom=1**: Implement Fix 2
3. **Map has UI offset**: Measure and implement Fix 5
4. **Wrong pixels per meter**: Recalculate using Fix 3

---

## Next Steps

1. **Start with Phase 1 sanity checks** (10 minutes)
2. **Request Frontend Debug Plan 1** (mouse coordinates)
3. **Try Fix 1 variations** (30 minutes)
4. **If still broken, add verbose logging** (Debug Tool 1)
5. **Compare with frontend coordinate formulas**
6. **Iterate until validated**

---

## Success Criteria

✅ Grid lines align with mouse coordinates (±10 pixels)
✅ Map center marker at visual center
✅ Bounds rectangle matches visible area
✅ AI can accurately place shapes using grid

---

## Notes for Future

Once fixed, document:
- The actual canvas→screen transformation formula
- Any offsets or quirks discovered
- Add unit tests with known coordinate pairs
- Update code comments with correct assumptions

Good luck! 🎯
