# Backend Quick Reference - Screenshot Feature

## TL;DR for Backend Developers

The frontend now sends an optional `screenshot` field in AI chat requests. Here's what you need to do:

## 1. Update Your Request Interface

```typescript
interface AIRequest {
  // ... existing fields ...
  screenshot?: {
    data: string;                    // base64 PNG or JPEG
    format: 'png' | 'jpeg';
    capturedAt: string;              // ISO timestamp
    viewportInfo: {
      width: number;                 // pixels
      height: number;                // pixels
      mapCenter: [number, number];   // [latitude, longitude]
      mapZoom: number;               // 0-22 (higher = more zoomed in)
      mapBounds?: {
        north: number;               // degrees
        south: number;
        east: number;
        west: number;
      };
    };
  };
}
```

## 2. Example Request Payload

```json
{
  "user": "john_doe",
  "message": "What restaurants are in this area?",
  "canvasState": { ... },
  "model": "gpt-4o",
  "screenshot": {
    "data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "format": "jpeg",
    "capturedAt": "2025-10-17T22:30:45.123Z",
    "viewportInfo": {
      "width": 1920,
      "height": 1080,
      "mapCenter": [37.7749, -122.4194],
      "mapZoom": 15.5,
      "mapBounds": {
        "north": 37.7850,
        "south": 37.7648,
        "east": -122.4094,
        "west": -122.4294
      }
    }
  }
}
```

## 3. Processing Logic (Python Example)

```python
import base64
import math

def calculate_coverage_area(zoom: float, latitude: float) -> float:
    """Calculate approximate coverage in miles"""
    earth_circumference = 24901  # miles
    tiles_at_zoom = 2 ** zoom
    miles_per_tile = earth_circumference / tiles_at_zoom
    latitude_adjustment = math.cos(math.radians(latitude))
    return miles_per_tile * latitude_adjustment

def build_context(screenshot: dict) -> str:
    """Build geographical context string for AI"""
    viewport = screenshot["viewportInfo"]
    lat, lng = viewport["mapCenter"]
    zoom = viewport["mapZoom"]

    coverage = calculate_coverage_area(zoom, lat)

    context = f"""The user is viewing a map centered at {lat:.6f}°N, {lng:.6f}°E
at zoom level {zoom:.1f}, covering approximately {coverage:.2f} miles."""

    if "mapBounds" in viewport:
        bounds = viewport["mapBounds"]
        context += f"""
Geographical bounds: {bounds['north']:.4f}°N to {bounds['south']:.4f}°S,
{bounds['west']:.4f}°W to {bounds['east']:.4f}°E."""

    return context

def process_ai_request(request: dict) -> dict:
    """Process AI request with optional screenshot"""

    # Build content array for AI
    content = []

    # Add screenshot if present
    if "screenshot" in request and request["screenshot"]:
        screenshot = request["screenshot"]

        # Validate (optional but recommended)
        validate_screenshot(screenshot)

        # Add image to content
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": f"image/{screenshot['format']}",
                "data": screenshot["data"]
            }
        })

        # Add geographical context
        geo_context = build_context(screenshot)
        text_content = f"{geo_context}\n\nUser message: {request['message']}"
        content.append({
            "type": "text",
            "text": text_content
        })
    else:
        # No screenshot, just text
        content.append({
            "type": "text",
            "text": request["message"]
        })

    # Send to Claude
    response = send_to_claude(content)
    return response

def validate_screenshot(screenshot: dict):
    """Basic validation"""
    # Check required fields
    assert "data" in screenshot, "Missing screenshot data"
    assert "format" in screenshot, "Missing format"
    assert "viewportInfo" in screenshot, "Missing viewportInfo"

    # Check size (max 10MB)
    size_bytes = len(screenshot["data"]) * 3 / 4
    assert size_bytes <= 10 * 1024 * 1024, "Screenshot too large"

    # Validate coordinates
    viewport = screenshot["viewportInfo"]
    lat, lng = viewport["mapCenter"]
    zoom = viewport["mapZoom"]

    assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
    assert -180 <= lng <= 180, f"Invalid longitude: {lng}"
    assert 0 <= zoom <= 22, f"Invalid zoom: {zoom}"
```

## 4. Send to Claude (Python)

```python
import anthropic

def send_to_claude(content: list) -> str:
    client = anthropic.Anthropic(api_key="your-api-key")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    return response.content[0].text
```

## 5. Important Notes

### Screenshot is Optional
Always handle the case where `screenshot` is `None`/`undefined`. Not all requests will include screenshots.

### Error Handling
If screenshot processing fails, fall back to text-only mode:

```python
try:
    response = process_with_screenshot(request)
except Exception as e:
    logger.error(f"Screenshot processing failed: {e}")
    # Retry without screenshot
    request_without_screenshot = {**request, "screenshot": None}
    response = process_ai_request(request_without_screenshot)
```

### Cost Implications
- Vision API calls cost **more** than text-only
- Monitor usage and costs
- Consider rate limiting screenshot requests

### Performance
- Screenshot payloads are large (150-400 KB)
- May need to increase request size limits
- Processing time is longer with images

## 6. Testing

### Test with curl:

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user": "test_user",
    "message": "What do you see in this map?",
    "canvasState": {"shapes": [], "viewport": {"zoom": 1, "pan": {"x": 0, "y": 0}}},
    "screenshot": {
      "data": "iVBORw0KGgo...",
      "format": "png",
      "capturedAt": "2025-10-17T22:30:00Z",
      "viewportInfo": {
        "width": 1920,
        "height": 1080,
        "mapCenter": [37.7749, -122.4194],
        "mapZoom": 15.0
      }
    }
  }'
```

### Test without screenshot:

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user": "test_user",
    "message": "Create a red circle",
    "canvasState": {"shapes": [], "viewport": {"zoom": 1, "pan": {"x": 0, "y": 0}}}
  }'
```

## 7. Coverage Area Reference

Quick reference for zoom levels to approximate coverage:

| Zoom Level | Approximate Coverage |
|------------|---------------------|
| 10         | ~50 miles           |
| 12         | ~12 miles           |
| 13         | ~8 miles            |
| 14         | ~4 miles            |
| 15         | ~2-3 miles          |
| 16         | ~1 mile             |
| 17         | ~0.5 miles          |
| 18         | ~0.3 miles          |
| 20         | ~500 feet           |

*Note: Coverage varies by latitude*

## 8. Common Issues

### Issue: "Screenshot too large"
- Frontend is configured to max 1920x1080 at 0.8 JPEG quality
- Should result in ~150-400 KB
- If larger, frontend may need to reduce quality

### Issue: "Invalid base64"
- Frontend strips the `data:image/png;base64,` prefix
- You receive just the base64 data
- Decode with: `base64.b64decode(screenshot["data"])`

### Issue: "Coordinates out of bounds"
- Validate latitude: -90 to 90
- Validate longitude: -180 to 180
- Validate zoom: 0 to 22

## 9. Monitoring

Suggested metrics to track:
- % of requests with screenshots
- Average screenshot size
- Screenshot processing time
- Vision API cost per request
- Validation failure rate

## 10. Security

- Validate all fields before processing
- Check file size limits
- Sanitize base64 input
- Rate limit per user
- Consider screenshot quotas

## Need More Info?

See full documentation: `docs/screenshot-capture-feature.md`
