# Screenshot Capture Feature for AI Chat Context (Frontend plan)

## Overview
This feature captures a visual screenshot of the current application view and attaches it to AI chat tool requests as context. This allows the AI to see what the user is currently viewing and provide more contextual responses.

## Implementation Approach: html2canvas

### Why html2canvas?
- Pure JavaScript implementation (no native dependencies)
- Works across all modern browsers
- Can capture specific DOM elements or entire views
- Converts directly to base64 for easy transmission
- Handles complex CSS and layouts well

## Frontend Implementation

### 1. Installation
```bash
npm install html2canvas
```

### 2. Screenshot Capture Service
Create a new service to handle screenshot capture:

**Location**: `src/services/screenshotCapture.ts`

**Responsibilities**:
- Capture specific elements or full app view
- Handle canvas rendering and conversion
- **Extract map viewport information from Mapbox instance**
- Compress/resize images if needed
- Return base64 encoded image string + viewport metadata

**Capturing Map Viewport Data:**
```typescript
// Get data from Mapbox GL instance
const mapCenter = map.getCenter(); // {lng, lat}
const mapZoom = map.getZoom(); // number
const mapBounds = map.getBounds(); // LngLatBounds object

const viewportInfo = {
  width: window.innerWidth,
  height: window.innerHeight,
  mapCenter: [mapCenter.lat, mapCenter.lng],
  mapZoom: mapZoom,
  mapBounds: {
    north: mapBounds.getNorth(),
    south: mapBounds.getSouth(),
    east: mapBounds.getEast(),
    west: mapBounds.getWest()
  }
};
```

### 3. Integration Points

#### AI Chat Tool Integration
- Add screenshot capture trigger before sending chat messages
- Attach screenshot as part of the request payload
- Provide user option to enable/disable screenshot capture

#### UI Considerations
- Add toggle in chat interface to enable/disable screenshots
- Show visual indicator when screenshot is being captured
- Display loading state during capture
- Show preview of captured screenshot (optional)

### 4. Configuration Options
```typescript
interface ScreenshotConfig {
  enabled: boolean;
  captureFullApp: boolean; // vs just map view
  quality: number; // 0-1 for compression
  maxWidth: number; // resize large screenshots
  maxHeight: number;
  includeInEveryMessage: boolean; // vs user-triggered only
}
```

### 5. Performance Considerations
- Capture timing (before vs after render)
- Image compression to reduce payload size
- Caching to avoid re-capture of unchanged views
- Debouncing for rapid successive captures
- Loading states to prevent UI blocking

### 6. Error Handling
- Handle canvas rendering failures
- Fallback when html2canvas fails
- Timeout for long captures
- User notification of capture failures

## Backend Implementation Requirements

### 0. Quick Start Guide for Backend Developers

This section provides a step-by-step guide for backend developers to implement screenshot support.

#### Step 1: Update API Request Handler

**Accept the new screenshot field in your request:**
```typescript
// Before
interface AIChatRequest {
  message: string;
  conversationId?: string;
}

// After
interface AIChatRequest {
  message: string;
  conversationId?: string;
  screenshot?: ScreenshotData; // New field
}

interface ScreenshotData {
  data: string; // base64 encoded PNG or JPEG
  format: 'png' | 'jpeg';
  capturedAt: string; // ISO timestamp
  viewportInfo: ViewportInfo;
}

interface ViewportInfo {
  width: number;
  height: number;
  mapCenter: [number, number]; // [lat, lng]
  mapZoom: number;
  mapBounds?: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
}
```

#### Step 2: Validate Screenshot Data

```typescript
function validateScreenshot(screenshot?: ScreenshotData): boolean {
  if (!screenshot) return true; // Optional field

  // Validate required fields
  if (!screenshot.data || !screenshot.format || !screenshot.viewportInfo) {
    throw new Error('Invalid screenshot data: missing required fields');
  }

  // Validate base64 format
  if (!screenshot.data.match(/^[A-Za-z0-9+/]+=*$/)) {
    throw new Error('Invalid screenshot data: not valid base64');
  }

  // Validate image size (e.g., max 10MB base64)
  const sizeInBytes = (screenshot.data.length * 3) / 4;
  if (sizeInBytes > 10 * 1024 * 1024) {
    throw new Error('Screenshot too large: max 10MB');
  }

  // Validate viewport info
  const { mapCenter, mapZoom } = screenshot.viewportInfo;
  if (!Array.isArray(mapCenter) || mapCenter.length !== 2) {
    throw new Error('Invalid mapCenter: must be [lat, lng]');
  }
  if (mapCenter[0] < -90 || mapCenter[0] > 90) {
    throw new Error('Invalid latitude: must be between -90 and 90');
  }
  if (mapCenter[1] < -180 || mapCenter[1] > 180) {
    throw new Error('Invalid longitude: must be between -180 and 180');
  }
  if (mapZoom < 0 || mapZoom > 22) {
    throw new Error('Invalid zoom level: must be between 0 and 22');
  }

  return true;
}
```

#### Step 3: Calculate Coverage Area

```typescript
/**
 * Calculate approximate coverage area in miles based on zoom level
 * Formula based on Web Mercator projection at equator
 */
function calculateCoverageAreaMiles(zoom: number, latitude: number): number {
  // Earth's circumference at equator in miles
  const earthCircumference = 24901;

  // At zoom level 0, one tile covers entire earth
  // Each zoom level doubles the number of tiles (halves the coverage)
  const tilesAtZoom = Math.pow(2, zoom);
  const milesPerTile = earthCircumference / tilesAtZoom;

  // Adjust for latitude (map is wider at equator, narrower at poles)
  const latitudeAdjustment = Math.cos(latitude * Math.PI / 180);

  return milesPerTile * latitudeAdjustment;
}
```

#### Step 4: Format Context for AI

```typescript
function buildAIContextFromScreenshot(screenshot: ScreenshotData): string {
  const { mapCenter, mapZoom, mapBounds } = screenshot.viewportInfo;
  const [lat, lng] = mapCenter;

  const coverageArea = calculateCoverageAreaMiles(mapZoom, lat);

  let context = `The user is viewing a map centered at ${lat.toFixed(6)}°N, ${lng.toFixed(6)}°E`;
  context += ` at zoom level ${mapZoom.toFixed(1)}.`;
  context += ` The visible area covers approximately ${coverageArea.toFixed(2)} miles.`;

  if (mapBounds) {
    context += `\nGeographical bounds: ${mapBounds.north.toFixed(4)}°N to ${mapBounds.south.toFixed(4)}°S, `;
    context += `${mapBounds.west.toFixed(4)}°W to ${mapBounds.east.toFixed(4)}°E.`;
  }

  return context;
}
```

#### Step 5: Send to AI Model (Claude Example)

```typescript
async function sendToAI(request: AIChatRequest): Promise<string> {
  const messages: any[] = [];

  // Build the content array
  const content: any[] = [];

  // If screenshot exists, add image first
  if (request.screenshot) {
    // Validate first
    validateScreenshot(request.screenshot);

    // Add image
    content.push({
      type: "image",
      source: {
        type: "base64",
        media_type: `image/${request.screenshot.format}`,
        data: request.screenshot.data
      }
    });

    // Add geographical context
    const geoContext = buildAIContextFromScreenshot(request.screenshot);
    const textContent = `${geoContext}\n\nUser message: ${request.message}`;
    content.push({
      type: "text",
      text: textContent
    });
  } else {
    // No screenshot, just text
    content.push({
      type: "text",
      text: request.message
    });
  }

  // Make API request to Claude
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: content
      }]
    })
  });

  const data = await response.json();
  return data.content[0].text;
}
```

#### Step 6: Error Handling

```typescript
try {
  validateScreenshot(request.screenshot);
  const aiResponse = await sendToAI(request);
  return { success: true, message: aiResponse };
} catch (error) {
  console.error('Screenshot processing error:', error);

  // Return user-friendly error
  if (error.message.includes('Screenshot too large')) {
    return {
      success: false,
      error: 'Screenshot is too large. Please try again with a smaller viewport.'
    };
  }

  // For other errors, try without screenshot
  console.log('Retrying without screenshot...');
  const fallbackRequest = { ...request, screenshot: undefined };
  const aiResponse = await sendToAI(fallbackRequest);
  return {
    success: true,
    message: aiResponse,
    warning: 'Screenshot could not be processed, but your message was sent.'
  };
}
```

#### Key Backend Implementation Notes:

1. **Screenshot is Optional**: Always handle the case where `screenshot` is undefined
2. **Validate Before Processing**: Check base64 format, size limits, and geographical bounds
3. **Include Geographical Context**: Use the viewport info to build meaningful context text for the AI
4. **Error Handling**: If screenshot processing fails, fall back to text-only mode
5. **Cost Monitoring**: Vision API calls are more expensive - track usage and costs
6. **Rate Limiting**: Consider limiting screenshot-enabled requests per user/hour
7. **Logging**: Log screenshot usage for monitoring and debugging

### 1. API Endpoint Updates

#### Current Endpoint
```
POST /api/ai/chat
```

#### Updated Request Payload
```typescript
interface AIChatRequest {
  message: string;
  conversationId?: string;
  // NEW: Screenshot data
  screenshot?: {
    data: string; // base64 encoded image
    format: 'png' | 'jpeg';
    capturedAt: string; // ISO timestamp
    viewportInfo: {
      width: number; // viewport width in pixels
      height: number; // viewport height in pixels
      mapCenter: [number, number]; // [latitude, longitude] of map center
      mapZoom: number; // current zoom level (0-22, where higher = more zoomed in)
      mapBounds?: {
        // Geographical bounds of visible map area
        north: number; // northern latitude
        south: number; // southern latitude
        east: number; // eastern longitude
        west: number; // western longitude
      };
    };
  };
}
```

### 2. Backend Processing

#### Geographical Context (Critical for Map Applications)

**Why viewport info is essential:**
The screenshot alone doesn't tell the AI *where* on Earth the user is looking. The geographical context provides:

1. **Spatial Understanding**: AI knows the exact location and scale of what's shown
2. **Range Calculation**: From zoom level, calculate approximate coverage area (usually 1-10 miles for typical usage)
3. **Context Enhancement**: AI can reference specific locations, neighborhoods, or geographical features
4. **Better Responses**: AI can suggest location-specific information or actions

**Example Context Calculation:**
- Zoom level 15 ≈ covers ~2-3 miles
- Zoom level 13 ≈ covers ~8-10 miles
- Zoom level 18 ≈ covers ~0.3 miles (neighborhood level)

**Using the Data:**
The backend should extract this information and include it in the AI prompt:
```typescript
const systemPrompt = `The user is viewing a map centered at
${screenshot.viewportInfo.mapCenter[0]}, ${screenshot.viewportInfo.mapCenter[1]}
(lat, lng) at zoom level ${screenshot.viewportInfo.mapZoom}, covering approximately
${calculateCoverageArea(screenshot.viewportInfo.mapZoom)} miles.
The visible area extends from ${bounds.north}N to ${bounds.south}S and
${bounds.west}W to ${bounds.east}E.`;
```

#### Image Handling
- Decode base64 image data
- Validate image size/format
- Extract and validate geographical viewport information
- Optional: Store screenshot temporarily or permanently
- Optional: Compress/resize on server side

#### AI Model Integration
- Pass image to vision-capable AI model (e.g., Claude with vision, GPT-4V)
- Include image in system context
- Handle multimodal request formatting

#### Example AI Request Format (Claude)
```typescript
{
  model: "claude-3-sonnet",
  messages: [
    {
      role: "user",
      content: [
        {
          type: "image",
          source: {
            type: "base64",
            media_type: "image/png",
            data: screenshot.data
          }
        },
        {
          type: "text",
          text: `Context: User is viewing a map centered at ${lat}, ${lng} (latitude, longitude)
at zoom level ${zoom}, covering approximately ${coverageAreaMiles} miles.
The visible area shows locations between ${bounds.north}°N to ${bounds.south}°S
and ${bounds.west}°W to ${bounds.east}°E.

User message: ${userMessage}`
        }
      ]
    }
  ]
}
```

### 3. Storage Considerations

#### Option A: Ephemeral (Recommended for MVP)
- Don't persist screenshots
- Include in request only
- Reduces storage costs

#### Option B: Persistent Storage
- Store screenshots in blob storage (S3, etc.)
- Link screenshots to conversation history
- Enable review/debugging of user context
- Implement cleanup/retention policy

### 4. Rate Limiting & Cost Control
- Screenshots significantly increase payload size
- May increase AI API costs (vision models cost more)
- Consider:
  - Rate limiting screenshot-enabled requests
  - User quotas for screenshot usage
  - Optional feature for premium users

### 5. Security & Privacy

#### Backend Validation
- Validate image format and size
- Scan for malicious content
- Strip EXIF data if present

#### Privacy Considerations
- User consent for screenshot capture
- Clear indication when screenshots are being sent
- Option to review before sending
- Data retention policy
- Compliance with privacy regulations (GDPR, etc.)

### 6. API Response
No changes needed to response format, but consider:
```typescript
interface AIChatResponse {
  message: string;
  conversationId: string;
  // Optional: Confirm screenshot was processed
  metadata?: {
    screenshotProcessed: boolean;
    screenshotId?: string; // if stored
  };
}
```

## Implementation Plan

### Phase 1: Basic Implementation
1. Install html2canvas dependency
2. Create screenshot capture service
3. Add capture trigger to AI chat interface
4. Update frontend to include screenshot in payload
5. Backend: Accept screenshot in request
6. Backend: Pass screenshot to AI model

### Phase 2: UI/UX Enhancement
1. Add toggle for screenshot feature
2. Visual indicator during capture
3. Preview captured screenshot
4. User preferences for screenshot settings

### Phase 3: Optimization
1. Image compression
2. Caching mechanism
3. Performance monitoring
4. Error handling refinement

### Phase 4: Advanced Features
1. Selective capture (map only vs full app)
2. Annotation tools before sending
3. Screenshot history in conversation
4. Admin dashboard for monitoring usage

## Technical Risks & Mitigations

### Risk 1: Large Payload Sizes
- **Impact**: Slow requests, increased bandwidth costs
- **Mitigation**: Aggressive compression, image resizing, quality settings

### Risk 2: Canvas Rendering Failures
- **Impact**: Feature doesn't work for some views
- **Mitigation**: Comprehensive error handling, fallback mechanisms, user notification

### Risk 3: Cross-Origin Issues
- **Impact**: html2canvas fails with external resources
- **Mitigation**: Proxy external images, use CORS-enabled resources, handle gracefully

### Risk 4: Increased AI API Costs
- **Impact**: Higher operating costs
- **Mitigation**: User quotas, optional feature, cost monitoring

### Risk 5: Privacy Concerns
- **Impact**: User hesitation to use feature
- **Mitigation**: Clear privacy policy, user consent, transparency

## Testing Strategy

### Frontend Tests
- Unit tests for screenshot capture service
- Integration tests for AI chat flow with screenshots
- Performance tests for capture timing
- Cross-browser compatibility tests

### Backend Tests
- Unit tests for image processing
- Integration tests for AI model requests
- Load tests with large images
- Security tests for malicious content

### E2E Tests
- Full flow from capture to AI response
- Error scenarios (capture failure, network issues)
- Different viewport sizes and content types

## Metrics & Monitoring

### Frontend Metrics
- Screenshot capture success rate
- Capture timing (performance)
- Feature adoption rate
- User preferences (enabled/disabled)

### Backend Metrics
- Average image size
- Processing time
- AI API cost per request (with/without screenshots)
- Error rates

## Future Enhancements
- Video/GIF capture for animation context
- Selective element capture (user highlights area)
- OCR preprocessing to extract text
- Screenshot diff comparison for change detection
- Multi-screenshot support (before/after views)

## References
- [html2canvas Documentation](https://html2canvas.hertzen.com/)
- [Claude Vision API](https://docs.anthropic.com/claude/docs/vision)
- [Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
