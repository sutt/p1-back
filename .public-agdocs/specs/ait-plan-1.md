### Task
We want to implement a new feature to allow an ai-powered chat widget in the frontend which will allow the user to type a command which will manipulate the canvas, e.g. adding shapes, moving shapes or resizing shapes. This likely should utilize a function-calling request to openai's api.

Sketch out the architecture nec for backend and add it to docs/aitool-plan.md. 
- identify what should be handled on frontend vs backend
- identify any frontend code thats needs to be updated or added
- identify any concerns


Extra info provided:
- the plan doc (docs/aitool-plan.md) already has information on 
- information about manipulating objects on canvas given the collab syncing architecture.
- features guidelines for PM, some examples of what should be done.

IMPORTANT: just update the plan file  in docs/aitool-plan.md, don't write the code yet.

Guidelines:
- We're looking for a proof-of-concept implementation, not a full production use. Sketch out the minimalist implementation they can be extended in the future, not the full production-grade implementation yet.


### Collab Arch, corner cases
Note: this multi-user collab architecture allows only 1 user to , so don't manipulate objects which are currently selected 



### Feature guidlelines from PM

AI Canvas Agent
The AI Feature
Build an AI agent that manipulates your canvas through natural language using function calling.

When a user types “Create a blue rectangle in the center,” the AI agent calls your canvas API functions, and the rectangle appears on everyone’s canvas via real-time sync.
Required Capabilities
Your AI agent must support at least 6 distinct commands showing a range of creation, manipulation, and layout actions.
Creation Commands:

“Create a red circle at position 100, 200”
“Add a text layer that says ‘Hello World’”
“Make a 200x300 rectangle”
Manipulation Commands:

“Move the blue rectangle to the center”
“Resize the circle to be twice as big”
“Rotate the text 45 degrees”
Layout Commands:

“Arrange these shapes in a horizontal row”
“Create a grid of 3x3 squares”
“Space these elements evenly”
Complex Commands:

“Create a login form with username and password fields”
“Build a navigation bar with 4 menu items”
“Make a card layout with title, image, and description”
Example Evaluation Criteria
When you say:

“Create a login form,” …We expect the AI to create at least three inputs (username, password, submit), arranged neatly, not just a text box.
Technical Implementation
Define a tool schema that your AI can call, such as:

createShape(type, x, y, width, height, color)
moveShape(shapeId, x, y)
resizeShape(shapeId, width, height)
rotateShape(shapeId, degrees)
createText(text, x, y, fontSize, color)
getCanvasState() // returns current canvas objects for context

We recommend OpenAI’s function calling or LangChain tools for interpretation.
For complex operations (e.g. “create a login form”), your AI should plan steps upfront (create fields, align, group) and execute sequentially.
Shared AI State
