# Backend plan

TODO - insert your plan here

# Frontend plan

## Executive Summary

This document outlines the architecture for implementing an AI-powered chat widget that allows users to manipulate the collaborative canvas through natural language commands. The feature will use OpenAI's function calling capabilities to interpret user commands and execute canvas operations while respecting the existing multi-user collaboration constraints.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Frontend Components](#frontend-components)
4. [Backend Components](#backend-components)
5. [AI Function Calling Schema](#ai-function-calling-schema)
6. [Implementation Plan](#implementation-plan)
7. [Security & Concerns](#security--concerns)
8. [Testing Strategy](#testing-strategy)

---

## Feature Overview

### User Experience Flow

1. User clicks an "AI Assistant" button to open a chat widget
2. User types a natural language command (e.g., "Create a blue rectangle in the center")
3. The system sends the command to the backend along with current canvas state
4. Backend uses OpenAI's function calling to parse the command and determine actions
5. Backend returns structured commands to frontend
6. Frontend executes the commands (create shapes, move shapes, etc.)
7. Changes are synced through existing collaboration system
8. User sees the result on canvas immediately (optimistic update)

### Required Command Categories (6+ commands)

**Creation Commands:**
- Create rectangle/circle/text with specific properties
- Create multiple shapes (e.g., "grid of 3x3 squares")
- Create complex layouts (e.g., "login form")

**Manipulation Commands:**
- Move shape to position or by delta
- Resize shape by dimensions or factor
- Rotate shape (future - not in current schema)

**Layout Commands:**
- Arrange shapes horizontally/vertically
- Space shapes evenly
- Align shapes (left, center, right, top, middle, bottom)

**Selection Commands:**
- Select shape by description (e.g., "select the blue rectangle")
- Select all shapes of a type
- Clear selection

**Query Commands:**
- Get canvas state
- Count shapes
- Find shapes by property

**Complex Commands:**
- Multi-step operations combining creation and layout

---

## Architecture Decisions

### Key Decision: Backend-Driven AI Processing

**Decision:** AI processing happens on the backend, not frontend.

**Rationale:**
1. **Security:** Keep OpenAI API keys server-side
2. **Consistency:** Ensure all users receive the same interpretation of commands
3. **State Management:** Backend has authoritative canvas state
4. **Cost Control:** Server can implement rate limiting and usage tracking
5. **Complexity:** LLM reasoning about canvas state is easier server-side

### Frontend vs Backend Responsibilities

| Responsibility | Location | Rationale |
|---------------|----------|-----------|
| **Chat UI Rendering** | Frontend | User interface, React components |
| **User Input Capture** | Frontend | Text input, send button |
| **Chat History Display** | Frontend | Message bubbles, scrolling |
| **OpenAI API Call** | Backend | Security, API key protection |
| **Function Calling Interpretation** | Backend | Stateful, requires canvas context |
| **Command Validation** | Backend | Check shape IDs exist, user has permission |
| **Canvas Manipulation** | Frontend | Execute commands via existing React state |
| **Collision Detection** | Backend | Verify shapes aren't selected by others |
| **Rate Limiting** | Backend | Prevent abuse |
| **Logging/Analytics** | Backend | Track AI usage, costs |

---

## Frontend Components

### 1. AI Chat Widget Component

**Location:** `my-react-app/src/components/AIChatWidget.tsx` (new file)

**Component Structure:**
```typescript
interface AIChatWidgetProps {
  currentUser: string;
  shapes: Shape[];
  onExecuteCommands: (commands: AICommand[]) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  commands?: AICommand[]; // For assistant messages
  status?: 'pending' | 'success' | 'error'; // Command execution status
}

interface AICommand {
  action: string; // 'createShape', 'moveShape', 'resizeShape', etc.
  params: Record<string, any>;
}
```

**State Management:**
- `messages: ChatMessage[]` - Chat history
- `inputText: string` - Current user input
- `isLoading: boolean` - Waiting for AI response
- `isOpen: boolean` - Widget visibility
- `error: string | null` - Error message display

**Features:**
- Collapsible floating panel (bottom-right corner)
- Scrollable message history
- Text input with send button
- Loading indicator while processing
- Error handling display
- Success/failure feedback for commands

### 2. Integration with DemoFigma Component

**Location:** `my-react-app/src/DemoFigma.tsx` (modifications)

**Required Changes:**

1. **Add AI Chat State:**
```typescript
const [aiChatOpen, setAiChatOpen] = useState(false);
```

2. **Add AI Button to Top Bar:**
```tsx
<button
  onClick={() => setAiChatOpen(!aiChatOpen)}
  className={aiChatOpen ? 'active' : ''}
>
  AI Assistant
</button>
```

3. **Implement Command Executor:**
```typescript
const executeAICommands = useCallback(async (commands: AICommand[]) => {
  for (const cmd of commands) {
    switch (cmd.action) {
      case 'createShape':
        // Create shape with specific properties
        break;
      case 'moveShape':
        // Move shape by ID
        break;
      case 'resizeShape':
        // Resize shape by ID
        break;
      case 'selectShape':
        // Select shape by ID
        break;
      case 'arrangeShapes':
        // Layout algorithm
        break;
      // ... more commands
    }
  }
  // Update server after all commands
  await updateShapesOnServer(shapes);
}, [shapes, currentUser, updateShapesOnServer]);
```

4. **Render Widget:**
```tsx
{aiChatOpen && (
  <AIChatWidget
    currentUser={currentUser}
    shapes={shapes}
    onExecuteCommands={executeAICommands}
  />
)}
```

### 3. AI Service Layer

**Location:** `my-react-app/src/services/aiService.ts` (new file)

**Purpose:** Handle API communication with backend

```typescript
export interface AIRequest {
  user: string;
  message: string;
  canvasState: {
    shapes: Shape[];
    viewport: { zoom: number; pan: { x: number; y: number } };
  };
}

export interface AIResponse {
  message: string; // AI's text response
  commands: AICommand[]; // Structured commands to execute
  reasoning?: string; // Optional explanation
}

export const sendAIMessage = async (request: AIRequest): Promise<AIResponse> => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const response = await fetch(`${apiUrl}/ai/chat`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`AI request failed: ${response.status}`);
  }

  return await response.json();
};
```

### 4. Command Execution Utilities

**Location:** `my-react-app/src/utils/aiCommands.ts` (new file)

**Purpose:** Helper functions for executing AI commands

```typescript
export const createShapeFromAI = (
  type: ShapeType,
  x: number,
  y: number,
  properties: Record<string, any>
): Shape => {
  // Similar to existing createShape but with custom properties
};

export const findShapeCenter = (viewport: { width: number; height: number }) => {
  // Calculate center coordinates
};

export const arrangeHorizontally = (shapes: Shape[], spacing: number) => {
  // Layout algorithm
};

export const arrangeGrid = (shapes: Shape[], rows: number, cols: number) => {
  // Grid layout algorithm
};
```

---

## Backend Components

### 1. New API Endpoint: `/api/ai/chat`

**Location:** Backend API (FastAPI)

**Method:** POST

**Request Body:**
```json
{
  "user": "username",
  "message": "Create a blue rectangle in the center",
  "canvasState": {
    "shapes": [...],
    "viewport": {
      "zoom": 1.0,
      "pan": { "x": 0, "y": 0 }
    }
  }
}
```

**Response Body:**
```json
{
  "message": "I've created a blue rectangle in the center of the canvas.",
  "commands": [
    {
      "action": "createShape",
      "params": {
        "type": "rectangle",
        "x": 400,
        "y": 300,
        "width": 200,
        "height": 150,
        "color": "blue"
      }
    }
  ],
  "reasoning": "Calculated center based on typical viewport size."
}
```

**Error Response:**
```json
{
  "error": "Shape with ID 'shape_123' is currently selected by another user",
  "message": "I couldn't move that shape because it's being edited by Alice."
}
```

### 2. OpenAI Integration Service

**Purpose:** Handle OpenAI API calls with function calling

**Key Components:**

1. **Function Definitions (Tool Schema):**
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "createShape",
            "description": "Create a new shape on the canvas",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["rectangle", "circle", "text"],
                        "description": "The type of shape to create"
                    },
                    "x": {
                        "type": "number",
                        "description": "X coordinate"
                    },
                    "y": {
                        "type": "number",
                        "description": "Y coordinate"
                    },
                    "width": {
                        "type": "number",
                        "description": "Width for rectangle/text"
                    },
                    "height": {
                        "type": "number",
                        "description": "Height for rectangle/text"
                    },
                    "radius": {
                        "type": "number",
                        "description": "Radius for circle"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text content for text shapes"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color of the shape (for future styling)"
                    }
                },
                "required": ["type", "x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "moveShape",
            "description": "Move an existing shape to a new position",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to move. If not known, use description to find shape first."
                    },
                    "x": {
                        "type": "number",
                        "description": "New X coordinate"
                    },
                    "y": {
                        "type": "number",
                        "description": "New Y coordinate"
                    }
                },
                "required": ["shapeId", "x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resizeShape",
            "description": "Resize an existing shape",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to resize"
                    },
                    "width": {
                        "type": "number",
                        "description": "New width (for rectangles/text)"
                    },
                    "height": {
                        "type": "number",
                        "description": "New height (for rectangles/text)"
                    },
                    "radius": {
                        "type": "number",
                        "description": "New radius (for circles)"
                    },
                    "scaleFactor": {
                        "type": "number",
                        "description": "Scale factor (e.g., 2.0 for twice as big)"
                    }
                },
                "required": ["shapeId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "selectShape",
            "description": "Select a shape on behalf of the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeId": {
                        "type": "string",
                        "description": "ID of the shape to select"
                    }
                },
                "required": ["shapeId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "findShapes",
            "description": "Find shapes by description or properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["rectangle", "circle", "text", "all"],
                        "description": "Filter by shape type"
                    },
                    "description": {
                        "type": "string",
                        "description": "Natural language description (e.g., 'the blue rectangle')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "arrangeShapes",
            "description": "Arrange multiple shapes in a layout",
            "parameters": {
                "type": "object",
                "properties": {
                    "shapeIds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IDs of shapes to arrange"
                    },
                    "layout": {
                        "type": "string",
                        "enum": ["horizontal", "vertical", "grid"],
                        "description": "Layout pattern"
                    },
                    "spacing": {
                        "type": "number",
                        "description": "Space between shapes in pixels"
                    },
                    "gridRows": {
                        "type": "number",
                        "description": "Number of rows for grid layout"
                    },
                    "gridCols": {
                        "type": "number",
                        "description": "Number of columns for grid layout"
                    }
                },
                "required": ["shapeIds", "layout"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "createComplexLayout",
            "description": "Create a multi-shape layout like a form, navbar, or card",
            "parameters": {
                "type": "object",
                "properties": {
                    "layoutType": {
                        "type": "string",
                        "enum": ["loginForm", "navbar", "card", "custom"],
                        "description": "Type of layout to create"
                    },
                    "position": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "description": "Top-left position of the layout"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Layout-specific properties (e.g., number of navbar items)"
                    }
                },
                "required": ["layoutType", "position"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "getCanvasState",
            "description": "Get information about the current canvas state",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
```

2. **System Prompt:**
```text
You are an AI assistant helping users manipulate a collaborative canvas.
The canvas contains shapes (rectangles, circles, text) that can be created, moved, and resized.

Current canvas dimensions: 800x600 (typical viewport)
Coordinate system: Top-left is (0,0), X increases right, Y increases down

IMPORTANT CONSTRAINTS:
- Only one user can select a shape at a time
- Do NOT manipulate shapes that are selectedBy another user
- Always check canvasState.shapes[].selectedBy before moving/resizing
- If a shape is unavailable, explain why and suggest alternatives

Canvas state information will be provided with each request.
Use the available functions to execute user commands.
For complex operations, call multiple functions in sequence.
Always provide a friendly response explaining what you did.
```

3. **Request Processing Flow:**
```
1. Receive user message + canvas state
2. Build OpenAI messages array:
   - System prompt
   - Canvas state summary
   - User message
3. Call OpenAI with tools/function calling
4. Parse function calls from response
5. Validate each function call:
   - Check shape exists
   - Check not selected by another user
   - Validate coordinates in bounds
6. If validation fails, call OpenAI again with error context
7. Return commands + AI message to frontend
```

### 3. Validation & Security Layer

**Purpose:** Ensure AI commands are safe and respect collaboration rules

**Validations:**
1. **Shape Ownership:** Verify shape isn't selected by another user
2. **Shape Existence:** Verify shapeId exists in current state
3. **Coordinate Bounds:** Prevent creating shapes at extreme coordinates
4. **Rate Limiting:** Max N requests per user per minute
5. **Command Limits:** Max N commands per AI response
6. **User Authentication:** Only authenticated users can use AI (optional)

**Example Validation Function:**
```python
def validate_move_shape(shape_id: str, user: str, canvas_state: dict) -> tuple[bool, str]:
    shape = next((s for s in canvas_state['shapes'] if s['id'] == shape_id), None)

    if not shape:
        return False, f"Shape {shape_id} does not exist"

    if shape['selectedBy'] and shape['selectedBy'][0] != user:
        return False, f"Shape is currently selected by {shape['selectedBy'][0]}"

    return True, ""
```

### 4. Configuration & Environment

**New Environment Variables:**
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview  # Or gpt-3.5-turbo for cost savings
AI_RATE_LIMIT_PER_USER=10  # Requests per minute
AI_MAX_COMMANDS_PER_RESPONSE=20  # Prevent abuse
AI_ENABLE=true  # Feature flag
```

---

## AI Function Calling Schema

### Complete Tool Definitions

See Backend Components section for full schema.

### Example Function Call Sequences

**Simple Command:**
```
User: "Create a red circle at 100, 200"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "createShape",
        "arguments": {
          "type": "circle",
          "x": 100,
          "y": 200,
          "radius": 50,
          "color": "red"
        }
      }
    }
  ]
}
```

**Complex Command:**
```
User: "Create a login form"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "createComplexLayout",
        "arguments": {
          "layoutType": "loginForm",
          "position": {"x": 300, "y": 200},
          "properties": {
            "includeRememberMe": false
          }
        }
      }
    }
  ]
}

Backend expands to:
[
  createShape(type="text", x=300, y=200, text="Username:", width=200, height=30),
  createShape(type="rectangle", x=300, y=240, width=200, height=40),
  createShape(type="text", x=300, y=290, text="Password:", width=200, height=30),
  createShape(type="rectangle", x=300, y=330, width=200, height=40),
  createShape(type="rectangle", x=300, y=380, width=200, height=40, text="Login")
]
```

**Multi-Step Command:**
```
User: "Find all circles and arrange them horizontally"

AI Response:
{
  "tool_calls": [
    {
      "function": {
        "name": "findShapes",
        "arguments": {"type": "circle"}
      }
    }
  ]
}

(After receiving shape IDs)

{
  "tool_calls": [
    {
      "function": {
        "name": "arrangeShapes",
        "arguments": {
          "shapeIds": ["shape_1", "shape_2", "shape_3"],
          "layout": "horizontal",
          "spacing": 20
        }
      }
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Backend Foundation (Week 1)

**Tasks:**
1. Add OpenAI SDK to backend dependencies
2. Create `/api/ai/chat` endpoint skeleton
3. Implement OpenAI function calling integration
4. Define all tool schemas
5. Implement validation layer
6. Add rate limiting
7. Unit tests for validation logic
8. Environment variable configuration

**Deliverables:**
- Backend can receive AI requests
- Backend can call OpenAI with function calling
- Backend returns structured commands
- Backend validates commands against collaboration rules

### Phase 2: Frontend UI (Week 1-2)

**Tasks:**
1. Create `AIChatWidget` component
2. Implement chat UI (messages, input, loading states)
3. Create `aiService.ts` for API communication
4. Add AI button to DemoFigma top bar
5. Wire up state management
6. Add error handling and feedback
7. Style the widget to match existing design

**Deliverables:**
- Functional chat widget UI
- Can send messages to backend
- Displays AI responses
- Shows loading and error states

### Phase 3: Command Execution (Week 2)

**Tasks:**
1. Implement `executeAICommands` function in DemoFigma
2. Handle `createShape` commands
3. Handle `moveShape` commands
4. Handle `resizeShape` commands
5. Handle `selectShape` commands
6. Handle `arrangeShapes` commands
7. Implement layout algorithms (horizontal, vertical, grid)
8. Test with existing collaboration system
9. Ensure proper sync via `updateShapesOnServer`

**Deliverables:**
- All AI commands execute correctly
- Changes sync to other users
- Respects selection constraints
- Optimistic updates work

### Phase 4: Complex Commands (Week 3)

**Tasks:**
1. Implement `createComplexLayout` on backend
2. Define templates for loginForm, navbar, card
3. Handle multi-shape creation
4. Implement intelligent positioning
5. Test complex commands end-to-end
6. Refine AI prompts for better interpretation

**Deliverables:**
- Can create login forms
- Can create navigation bars
- Can create card layouts
- AI understands context

### Phase 5: Polish & Testing (Week 3-4)

**Tasks:**
1. Comprehensive testing of all 6+ required commands
2. Edge case testing (offline users, shape collisions)
3. Performance optimization
4. Error message improvements
5. User experience refinements
6. Documentation
7. Demo video creation

**Deliverables:**
- Feature complete and tested
- Documentation for PM review
- Demo showing all required commands
- Ready for submission

---

## Security & Concerns

### Security Considerations

1. **API Key Protection**
   - **Concern:** OpenAI API key must not be exposed to frontend
   - **Solution:** All AI calls go through backend proxy
   - **Implementation:** Store key in environment variables, never in code

2. **Rate Limiting**
   - **Concern:** Users could abuse AI API causing high costs
   - **Solution:** Per-user rate limits (10 requests/minute)
   - **Implementation:** Redis-based rate limiting or in-memory tracking

3. **Input Validation**
   - **Concern:** Malicious prompts could try to manipulate AI behavior
   - **Solution:** Sanitize user input, length limits (500 chars)
   - **Implementation:** Backend validates input before sending to OpenAI

4. **Command Validation**
   - **Concern:** AI might generate invalid or malicious commands
   - **Solution:** Strict validation layer checks all commands
   - **Implementation:** Validate against schema, check bounds, verify permissions

5. **Cost Control**
   - **Concern:** AI API usage could be expensive
   - **Solution:** Monitor costs, set budget alerts, use cheaper models
   - **Implementation:** CloudWatch/logging, GPT-3.5-turbo vs GPT-4

### Collaboration Concerns

1. **Shape Selection Conflicts**
   - **Issue:** AI might try to manipulate shapes selected by others
   - **Solution:** Validation layer checks `selectedBy` before allowing operations
   - **Implementation:** Backend validates, AI gets error feedback, suggests alternatives

2. **Race Conditions**
   - **Issue:** AI command execution happens while other users are editing
   - **Solution:** Use existing polling-based sync mechanism
   - **Implementation:** Commands go through `updateShapesOnServer` which does merge logic

3. **Concurrent AI Requests**
   - **Issue:** User sends multiple AI requests while first is processing
   - **Solution:** Disable send button while loading, queue requests
   - **Implementation:** Frontend `isLoading` state prevents concurrent sends

4. **Stale Canvas State**
   - **Issue:** Canvas state changes between request and execution
   - **Solution:** Include timestamp, backend re-validates before execution
   - **Implementation:** Backend checks shape still exists and available

### User Experience Concerns

1. **AI Interpretation Errors**
   - **Issue:** AI might misunderstand user intent
   - **Solution:** Provide clear feedback, allow undo, show reasoning
   - **Implementation:** Display AI's text response, add undo button

2. **Performance**
   - **Issue:** OpenAI API calls take 2-5 seconds
   - **Solution:** Show loading indicators, optimize prompts for speed
   - **Implementation:** Skeleton loaders, use streaming if available

3. **Learning Curve**
   - **Issue:** Users might not know what commands are possible
   - **Solution:** Provide examples, autocomplete suggestions
   - **Implementation:** Placeholder text with examples, help button

4. **Error Communication**
   - **Issue:** Users need to understand why commands fail
   - **Solution:** Clear error messages in natural language
   - **Implementation:** Backend returns user-friendly error messages

### Technical Concerns

1. **Backend API Schema Extension**
   - **Issue:** Need to add new endpoint to existing FastAPI backend
   - **Solution:** Follow existing patterns, add to OpenAPI schema
   - **Implementation:** Standard FastAPI route with proper models

2. **Frontend State Management**
   - **Issue:** DemoFigma is already 1,182 lines, adding more complexity
   - **Solution:** Extract AI logic to separate components/services
   - **Implementation:** Create `AIChatWidget`, `aiService.ts`, `aiCommands.ts`

3. **Testing Complexity**
   - **Issue:** AI responses are non-deterministic
   - **Solution:** Mock OpenAI in tests, test validation logic separately
   - **Implementation:** Unit tests for validation, integration tests with mocked AI

4. **Backward Compatibility**
   - **Issue:** Must not break existing functionality
   - **Solution:** Feature flag, isolated code, optional feature
   - **Implementation:** `AI_ENABLE` env var, widget only shows if enabled

### Mitigation Strategies Summary

| Concern | Risk Level | Mitigation | Status |
|---------|-----------|------------|--------|
| API Key Exposure | High | Backend proxy only | Planned |
| High Costs | Medium | Rate limiting + monitoring | Planned |
| Selection Conflicts | High | Validation layer | Planned |
| Race Conditions | Medium | Existing merge logic | Leverages existing |
| AI Misinterpretation | Medium | Clear feedback + undo | Planned |
| Performance | Low | Loading indicators | Planned |
| Backward Compatibility | Low | Feature flag | Planned |

---

## Testing Strategy

### Unit Tests

**Backend:**
- Validation functions (shape ownership, existence, bounds)
- Command parsing and generation
- Rate limiting logic
- Error handling

**Frontend:**
- Command execution functions
- Layout algorithms (arrangeHorizontally, arrangeGrid)
- Component rendering (AIChatWidget)
- Service layer (aiService.ts)

### Integration Tests

**Backend:**
- `/api/ai/chat` endpoint with mocked OpenAI
- Full request/response cycle
- Validation with actual canvas state
- Error scenarios

**Frontend:**
- Chat widget interaction flow
- Command execution with actual shapes
- Sync with backend via API
- Multi-step command sequences

### End-to-End Tests

**Required Command Testing (6+ commands):**

1. **Creation Commands:**
   - "Create a red rectangle at 100, 200"
   - "Add a text that says 'Hello World' at 300, 300"
   - "Make a circle with radius 50 at 400, 200"

2. **Manipulation Commands:**
   - "Move the rectangle to 200, 200"
   - "Resize the circle to be twice as big"
   - "Make the text box 300 pixels wide"

3. **Layout Commands:**
   - "Arrange these three shapes horizontally"
   - "Create a grid of 3x3 squares"
   - "Space the circles evenly"

4. **Complex Commands:**
   - "Create a login form with username and password fields"
   - "Build a navigation bar with 4 menu items"
   - "Make a card layout with title and description"

**Collaboration Scenarios:**
- User A selects shape, User B tries to move it via AI (should fail gracefully)
- AI creates shape while another user is panning/zooming (should work)
- Multiple users use AI simultaneously (should handle correctly)

**Error Scenarios:**
- Invalid shape ID
- Shape selected by another user
- Malformed command
- OpenAI API timeout
- Rate limit exceeded

### Manual Testing Checklist

- [ ] Chat widget opens and closes smoothly
- [ ] Messages display correctly (user vs assistant)
- [ ] Loading state shows during AI processing
- [ ] Error messages display clearly
- [ ] All 6 required command types work
- [ ] Complex commands create proper layouts
- [ ] Commands respect selection constraints
- [ ] Changes sync to other users
- [ ] Widget is responsive on different screen sizes
- [ ] Works with authenticated and anonymous users
- [ ] Works after page refresh (state restoration)
- [ ] Handles network errors gracefully

---

## Appendix A: File Structure

```
my-react-app/
├── src/
│   ├── components/
│   │   └── AIChatWidget.tsx          [NEW] Chat UI component
│   │   └── AIChatWidget.css          [NEW] Widget styles
│   ├── services/
│   │   └── aiService.ts              [NEW] API communication
│   ├── utils/
│   │   └── aiCommands.ts             [NEW] Command execution helpers
│   ├── DemoFigma.tsx                 [MODIFIED] Add AI integration
│   ├── DemoFigma.css                 [MODIFIED] Add AI button styles
│   └── main.tsx                      [NO CHANGE]

backend/
├── routes/
│   └── ai.py                         [NEW] AI chat endpoint
├── services/
│   └── openai_service.py             [NEW] OpenAI integration
│   └── ai_validator.py               [NEW] Command validation
├── models/
│   └── ai_models.py                  [NEW] Request/response models
├── main.py                           [MODIFIED] Register AI routes
└── requirements.txt                  [MODIFIED] Add openai package

docs/
└── aitool-plan.md                    [THIS FILE]
```

## Appendix B: Environment Configuration

**.env (Frontend):**
```
VITE_API_URL=http://127.0.0.1:8000/api
VITE_POLLING_INTERVAL_MS=2000
VITE_USER_POLLING_INTERVAL_MS=5000
VITE_HIDE_DEBUG_MENU=false
VITE_AI_ENABLED=true                  [NEW]
```

**.env (Backend):**
```
OPENAI_API_KEY=sk-...                 [NEW]
OPENAI_MODEL=gpt-3.5-turbo           [NEW]
AI_RATE_LIMIT_PER_USER=10            [NEW]
AI_MAX_COMMANDS_PER_RESPONSE=20      [NEW]
AI_ENABLE=true                        [NEW]
```

## Appendix C: API Endpoint Specification

**POST `/api/ai/chat`**

Request:
```typescript
{
  user: string;              // Current username
  message: string;           // User's natural language command
  canvasState: {
    shapes: Shape[];         // Current shapes array
    viewport: {
      zoom: number;
      pan: { x: number; y: number };
    };
  };
}
```

Response (Success):
```typescript
{
  message: string;           // AI's text response
  commands: AICommand[];     // Structured commands to execute
  reasoning?: string;        // Optional explanation of AI's logic
}
```

Response (Error):
```typescript
{
  error: string;             // Error code/type
  message: string;           // User-friendly error message
  details?: any;             // Additional debug info
}
```

---

## Conclusion

This architecture plan provides a comprehensive blueprint for implementing the AI Canvas Agent feature. The design prioritizes:

1. **Security:** API keys protected, validation at every step
2. **Collaboration:** Respects existing multi-user constraints
3. **User Experience:** Clear feedback, natural language understanding
4. **Maintainability:** Modular code, clear separation of concerns
5. **Scalability:** Rate limiting, cost controls, feature flags

The implementation will be phased over 3-4 weeks, with clear milestones and deliverables at each stage. The feature will enable users to manipulate the canvas through natural language while maintaining the integrity of the collaborative system.

Next steps: Review this plan with the team, get approval, and begin Phase 1 implementation.
