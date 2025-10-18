# Screenshot Feature - Quick Start

## 🚀 Quick Start (5 minutes)

### 1. Send a request with screenshot

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user": "test_user",
    "message": "What do you see in this map?",
    "canvasState": {
      "shapes": [],
      "viewport": {"zoom": 1, "pan": {"x": 0, "y": 0}}
    },
    "screenshot": {
      "data": "BASE64_ENCODED_IMAGE_HERE",
      "format": "jpeg",
      "capturedAt": "2025-10-17T14:30:00Z",
      "viewportInfo": {
        "width": 1920,
        "height": 1080,
        "mapCenter": [37.7749, -122.4194],
        "mapZoom": 15.0
      }
    }
  }'
```

### 2. Enable debugging (optional)

```bash
# Add to .env
AI_DEBUG_SCREENSHOT=true

# Restart server
python main.py
```

### 3. Check debug output

```bash
# See screenshots
ls -lh ./debug_screenshots/*.jpeg

# See prompts
cat ./debug_screenshots/prompt_*.txt
```

### 4. Clean up

```bash
rm -rf ./debug_screenshots/*
```

## 📋 Key Points

- **Screenshot is optional** - system falls back to text-only if missing or invalid
- **Max size**: 10MB base64 (~7.5MB actual image)
- **Formats**: PNG or JPEG only
- **Debug mode**: Set `AI_DEBUG_SCREENSHOT=true` to dump files
- **Debug files**: Must be manually cleaned up

## 🧪 Run Tests

```bash
# Basic test
python test_screenshot_feature.py

# With debug mode
AI_DEBUG_SCREENSHOT=true python test_screenshot_feature.py
```

## 📖 Full Documentation

- **Debug Guide**: `docs/screenshot-debug-guide.md`
- **Implementation Summary**: `docs/screenshot-implementation-summary.md`
- **Original Plan**: `docs/map-img-plan.md`
- **Quick Reference**: `docs/map-img-guidance.md`

## 🔧 Code Location

- **Request Models**: `routes/ai.py` (lines 77-115)
- **Processing Utils**: `services/screenshot_utils.py`
- **OpenAI Integration**: `services/openai_service.py` (process_command method)
- **Tests**: `test_screenshot_feature.py`

## ⚠️ Limitations

1. No malicious content scanning
2. No auto-cleanup of debug files
3. Basic validation only
4. OpenAI format (may need adjustment for Claude/other providers)
5. No rate limiting on screenshots
6. No user quotas

## 🐛 Troubleshooting

**No debug files created?**
- Check `AI_DEBUG_SCREENSHOT=true` is set
- Restart server after setting env var

**Screenshot validation fails?**
- Check lat (-90 to 90), lng (-180 to 180), zoom (0-22)
- Check base64 encoding is correct
- Check size < 10MB

**Want to test without frontend?**
```bash
python test_screenshot_feature.py
```

## 📞 Need Help?

See full debug guide: `docs/screenshot-debug-guide.md`
