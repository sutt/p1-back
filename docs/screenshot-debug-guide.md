# Screenshot Feature Debugging Guide

This guide explains how to enable and use the debugging utilities for the screenshot feature.

## Overview

The screenshot feature includes debugging utilities that allow developers to:
1. Dump decoded images to the filesystem for visual inspection
2. Dump the full prompt being sent to the OpenAI API
3. See detailed logs of screenshot processing

## Enabling Debug Mode

Set the following environment variable:

```bash
AI_DEBUG_SCREENSHOT=true
```

You can add this to your `.env` file:

```bash
# Enable screenshot debugging
AI_DEBUG_SCREENSHOT=true

# Optionally enable general AI debugging for additional context
AI_DEBUG=true
```

## What Gets Logged

When `AI_DEBUG_SCREENSHOT=true` is set, the system will:

### 1. Dump Screenshot Images

**Location**: `./debug_screenshots/screenshot_YYYYMMDD_HHMMSS_<request_id>.<format>`

Each screenshot received from the frontend will be decoded and saved to the filesystem so you can visually verify:
- The screenshot was received correctly
- The image matches what the user is viewing
- The image quality is acceptable

**Example**:
```
./debug_screenshots/screenshot_20251017_143052_a3b4c5d6.jpeg
```

### 2. Dump Full Prompts

**Location**: `./debug_screenshots/prompt_YYYYMMDD_HHMMSS_<request_id>.txt`

The full prompt array being sent to the OpenAI API will be dumped to a text file, showing:
- System prompts
- Canvas state
- Geographical context (if screenshot is included)
- User message
- Image metadata (size, type) without the full base64 data

**Example**:
```
./debug_screenshots/prompt_20251017_143052_a3b4c5d6.txt
```

### 3. Console Debug Logs

Additional debug information will be printed to the console:
- Request ID for tracking
- Screenshot validation results
- Geographical context calculations
- Coverage area in miles
- Processing status

**Example Console Output**:
```
[AI-SCREENSHOT-DEBUG] Request ID: a3b4c5d6
[AI-SCREENSHOT-DEBUG] Screenshot provided, processing...
[AI-SCREENSHOT-DEBUG] Validating screenshot data...
[AI-SCREENSHOT-DEBUG] Screenshot size: 287.45KB
[AI-SCREENSHOT-DEBUG] Screenshot validation passed
[AI-SCREENSHOT-DEBUG] Screenshot dumped to: ./debug_screenshots/screenshot_20251017_143052_a3b4c5d6.jpeg
[AI-SCREENSHOT-DEBUG] File size: 287.45KB
[AI-SCREENSHOT-DEBUG] Building geographical context...
[AI-SCREENSHOT-DEBUG] Calculated coverage area: 2.34 miles at zoom 15.5, lat 37.7749
[AI-SCREENSHOT-DEBUG] Geographical context: The user is viewing a map centered at 37.774900°N, -122.419400°E at zoom level 15.5. The visible area covers approximately 2.34 miles.
[AI-SCREENSHOT-DEBUG] Screenshot processed and added to request
[AI-SCREENSHOT-DEBUG] Dumping full prompt to filesystem for debugging...
[AI-SCREENSHOT-DEBUG] Full prompt dumped to: ./debug_screenshots/prompt_20251017_143052_a3b4c5d6.txt
```

## How to Use

### Step 1: Enable Debugging

Add to your `.env` file:
```bash
AI_DEBUG_SCREENSHOT=true
```

### Step 2: Restart Server

Restart your FastAPI server so it picks up the environment variable:
```bash
# Stop the server (Ctrl+C)
# Then restart it
python main.py
# or
uvicorn main:app --reload
```

### Step 3: Make Requests with Screenshots

Send AI chat requests that include screenshots. The debugging utilities will automatically:
1. Save each screenshot to `./debug_screenshots/`
2. Save the full prompt to `./debug_screenshots/`
3. Log details to the console

### Step 4: Review Debug Output

**Check the images**:
```bash
ls -lh ./debug_screenshots/*.jpeg
ls -lh ./debug_screenshots/*.png
```

Open the images in your image viewer to verify they look correct.

**Check the prompts**:
```bash
cat ./debug_screenshots/prompt_<timestamp>_<request_id>.txt
```

Review the prompt to ensure:
- The geographical context is correct
- The image metadata is included
- The user message is properly formatted

### Step 5: Clean Up

**IMPORTANT**: Debug files are NOT automatically cleaned up. You must manually delete them.

```bash
# Delete all debug files
rm -rf ./debug_screenshots/*

# Or delete old files (older than 7 days)
find ./debug_screenshots -type f -mtime +7 -delete
```

## Troubleshooting

### Issue: No debug files are created

**Possible Causes**:
1. `AI_DEBUG_SCREENSHOT` is not set to `true`
2. Server wasn't restarted after setting the environment variable
3. No screenshots are being sent in the requests

**Solution**:
```bash
# Check environment variable
echo $AI_DEBUG_SCREENSHOT

# Verify it's set in your process
# Add this temporarily to your code:
import os
print(f"DEBUG_SCREENSHOT: {os.getenv('AI_DEBUG_SCREENSHOT')}")

# Restart the server
```

### Issue: Screenshot files are corrupted or won't open

**Possible Causes**:
1. Base64 data is malformed
2. Format mismatch (claimed to be JPEG but is actually PNG)
3. Data was truncated during transmission

**Solution**:
- Check the console logs for validation errors
- Try a different image quality setting on the frontend
- Verify the base64 encoding on the frontend

### Issue: Prompt files are empty or incomplete

**Possible Causes**:
1. Exception occurred during prompt dumping
2. File permissions issue

**Solution**:
- Check console for error messages
- Verify write permissions on `./debug_screenshots/` directory
- Check disk space

### Issue: Too many debug files accumulating

**Solution**:
Set up a cron job or manual cleanup script:

```bash
#!/bin/bash
# cleanup_debug_screenshots.sh
# Delete debug files older than 7 days

find ./debug_screenshots -type f -mtime +7 -delete
echo "Cleaned up old debug files"
```

Add to crontab:
```bash
# Run daily at 2am
0 2 * * * /path/to/cleanup_debug_screenshots.sh
```

## Security Considerations

### Do NOT Enable in Production

The debugging utilities should **ONLY** be enabled in development environments because:

1. **Disk Space**: Debug files accumulate and are not auto-cleaned
2. **Sensitive Data**: Screenshots may contain sensitive user data
3. **Performance**: Writing files to disk adds overhead
4. **Security**: Debug files may expose system information

### Recommended Approach

Only enable debugging when actively troubleshooting:

```bash
# Enable debugging temporarily
AI_DEBUG_SCREENSHOT=true python main.py

# Disable after debugging
AI_DEBUG_SCREENSHOT=false python main.py
```

## Understanding the Debug Output

### Screenshot Files

The dumped screenshot files show exactly what the OpenAI API receives. Verify:
- ✅ Image is clear and readable
- ✅ Map is visible
- ✅ Image size is reasonable (< 500KB ideally)
- ❌ Image is too large (> 1MB) - consider reducing quality on frontend
- ❌ Image is blurry - increase quality on frontend
- ❌ Image is corrupted - check base64 encoding

### Prompt Files

The prompt files show the full context sent to OpenAI. Key sections:

```
=== Message 1 ===
role: system
content: <System prompt with instructions>

=== Message 2 ===
role: system
content: Canvas state information

=== Message 3 ===
role: user
content:
  Part 1: image
    media_type: image/jpeg
    data_length: 384562 chars (~287.45KB)
  Part 2: text
    text: The user is viewing a map centered at 37.774900°N, -122.419400°E at zoom level 15.5...

    User message: What restaurants are in this area?
```

Verify:
- ✅ Geographical context has correct coordinates
- ✅ Coverage area is reasonable for the zoom level
- ✅ User message is included
- ✅ Image size is reasonable
- ❌ Coordinates are wrong - check frontend mapCenter extraction
- ❌ Zoom level is wrong - check frontend mapZoom extraction
- ❌ Coverage area seems way off - check formula or latitude

## Code Location

The debugging utilities are implemented in:

**File**: `services/screenshot_utils.py`

**Functions**:
- `ai_screenshot_debug_print()` - Debug logging
- `dump_screenshot_to_filesystem()` - Dumps decoded images
- `dump_full_prompt()` - Dumps prompt text files
- `validate_screenshot()` - Validates screenshot data
- `build_geographical_context()` - Builds context string
- `calculate_coverage_area_miles()` - Calculates coverage

## Module Flag

The debugging is controlled by a module-level flag:

```python
# In screenshot_utils.py
DEBUG_SCREENSHOT = os.getenv("AI_DEBUG_SCREENSHOT", "false").lower() == "true"
```

This flag is checked by the utility functions to determine if debugging is enabled.

## Example End-to-End Debug Session

```bash
# 1. Enable debugging
echo "AI_DEBUG_SCREENSHOT=true" >> .env

# 2. Start server
python main.py

# 3. Send a request with screenshot
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @test_request_with_screenshot.json

# 4. Check console output
# You should see [AI-SCREENSHOT-DEBUG] logs

# 5. Check debug files
ls -lh ./debug_screenshots/

# 6. View the screenshot
open ./debug_screenshots/screenshot_*.jpeg

# 7. View the prompt
cat ./debug_screenshots/prompt_*.txt

# 8. Clean up when done
rm -rf ./debug_screenshots/*

# 9. Disable debugging
sed -i '/AI_DEBUG_SCREENSHOT/d' .env
```

## Limitations & Future Work

Current limitations documented in code comments:

1. **No Auto-Cleanup**: Debug files must be manually deleted
2. **Repo Root Directory**: Files are dumped to `./debug_screenshots/` (relative to working directory)
3. **No Rotation**: Unlimited number of debug files can accumulate
4. **No Size Limits**: Could fill up disk if many large screenshots are processed
5. **Synchronous I/O**: File writes block the request (minimal impact for PoC)

Future improvements:
- [ ] Add automatic cleanup of old debug files
- [ ] Add configurable debug directory location
- [ ] Add max file count with rotation
- [ ] Add max total debug directory size
- [ ] Use async I/O for file writes
- [ ] Add debug file compression
- [ ] Add selective debugging (only log failures, only log large images, etc.)
