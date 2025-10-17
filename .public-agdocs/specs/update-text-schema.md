Update the models and any other nec fields to handle the added text element on the frontend. The diff on the frontend is provided below.
- update the seed data to include the new fields, also add one text elem to seed data


### Diff on client side

diff --git a/my-react-app/src/DemoFigma.tsx b/my-react-app/src/DemoFigma.tsx
index b56495a..1b7354a 100644
--- a/my-react-app/src/DemoFigma.tsx
+++ b/my-react-app/src/DemoFigma.tsx
@@ -6,7 +6,7 @@ import './DemoFigma.css';
 // Module-wide debug flag
 const DEBUG = false;
 
-type ShapeType = 'rectangle' | 'circle';
+type ShapeType = 'rectangle' | 'circle' | 'text';
 
 interface BaseShape {
   id: string;
@@ -27,7 +27,14 @@ interface CircleShape extends BaseShape {
   radius: number;
 }
 
-type Shape = RectangleShape | CircleShape;
+interface TextShape extends BaseShape {
+  type: 'text';
+  text: string;
+  width: number;
+  height: number;
+}
+
+type Shape = RectangleShape | CircleShape | TextShape;
 
 interface UserOnlineResponse {
   userName: string;
@@ -48,7 +55,7 @@ const createShape = (type: ShapeType, x: number, y: number): Shape => {
       height: getRandomSize(),
       selectedBy: [],
     };
-  } else { // circle
+  } else if (type === 'circle') {
     return {
       id,
       type: 'circle',
@@ -57,6 +64,17 @@ const createShape = (type: ShapeType, x: number, y: number): Shape => {
       radius: getRandomSize(),
       selectedBy: [],
     };
+  } else { // text
+    return {
+      id,
+      type: 'text',
+      x: Math.round(x),
+      y: Math.round(y),
+      text: 'this is text',
+      width: 200,
+      height: 50,
+      selectedBy: [],
+    };
   }
 };
 
@@ -69,6 +87,10 @@ const isPointInCircle = (px: number, py: number, circle: CircleShape) => {
   return distance <= circle.radius;
 };
 
+const isPointInText = (px: number, py: number, text: TextShape) => {
+  return px >= text.x && px <= text.x + text.width && py >= text.y && py <= text.y + text.height;
+};
+
 const formatDuration = (createdAt: string) => {
   const now = new Date();
   const createdDate = new Date(createdAt);
@@ -90,7 +112,7 @@ function DemoFigma() {
   const [zoom, setZoom] = useState(1);
   const [pan, setPan] = useState({ x: 0, y: 0 });
   const [isPanning, setIsPanning] = useState(false);
-  const [activeTool, setActiveTool] = useState<'rectangle' | 'circle' | 'select' | null>(null);
+  const [activeTool, setActiveTool] = useState<'rectangle' | 'circle' | 'text' | 'select' | null>(null);
   const [isMoveMode, setIsMoveMode] = useState(false);
   const lastMousePosition = useRef({ x: 0, y: 0 });
   const canvasRef = useRef<HTMLDivElement>(null);
@@ -102,6 +124,7 @@ function DemoFigma() {
   const [authUsername, setAuthUsername] = useState('');
   const [authPassword, setAuthPassword] = useState('');
   const [authError, setAuthError] = useState('');
+  const [editingShapeId, setEditingShapeId] = useState<string | null>(null);
 
   const hideDebugMenu = import.meta.env.VITE_HIDE_DEBUG_MENU === 'true';
 
@@ -246,6 +269,14 @@ function DemoFigma() {
     }
   }, [currentUser]);
 
+  const finishEditing = useCallback(() => {
+    setEditingShapeId(null);
+    setShapes(currentShapes => {
+      updateShapesOnServer(currentShapes);
+      return currentShapes;
+    });
+  }, [updateShapesOnServer]);
+
   const handleSignup = async () => {
     const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
     try {
@@ -453,6 +484,7 @@ function DemoFigma() {
   };
 
   const handleCanvasClick = (e: MouseEvent<HTMLDivElement>) => {
+    if (editingShapeId) return;
     if (!canvasRef.current) return;
 
     const rect = canvasRef.current.getBoundingClientRect();
@@ -462,7 +494,7 @@ function DemoFigma() {
     const canvasX = (mouseX - pan.x) / zoom;
     const canvasY = (mouseY - pan.y) / zoom;
 
-    if (activeTool === 'rectangle' || activeTool === 'circle') {
+    if (activeTool === 'rectangle' || activeTool === 'circle' || activeTool === 'text') {
       const newShape = createShape(activeTool, canvasX, canvasY);
       setShapes(prevShapes => {
         const newShapes = [...prevShapes, newShape];
@@ -496,8 +528,10 @@ function DemoFigma() {
         let hit = false;
         if (shape.type === 'rectangle') {
           hit = isPointInRectangle(canvasX, canvasY, shape);
-        } else {
+        } else if (shape.type === 'circle') {
           hit = isPointInCircle(canvasX, canvasY, shape);
+        } else if (shape.type === 'text') {
+          hit = isPointInText(canvasX, canvasY, shape);
         }
         if (hit) {
           clickedShape = shape;
@@ -549,7 +583,7 @@ function DemoFigma() {
     if (hintMessage) {
       return hintMessage;
     }
-    if (activeTool === 'rectangle' || activeTool === 'circle') {
+    if (activeTool === 'rectangle' || activeTool === 'circle' || activeTool === 'text') {
       return `Click on the canvas to place a ${activeTool}`;
     }
     if (isMoveMode) {
@@ -570,7 +604,7 @@ function DemoFigma() {
     return message;
   };
 
-  const handleToolClick = (tool: 'rectangle' | 'circle' | 'select') => {
+  const handleToolClick = (tool: 'rectangle' | 'circle' | 'text' | 'select') => {
     setActiveTool(prev => {
       const newTool = prev === tool ? null : tool;
       if (newTool) {
@@ -696,6 +730,12 @@ function DemoFigma() {
             >
               Circle
             </button>
+            <button
+              onClick={() => handleToolClick('text')}
+              className={activeTool === 'text' ? 'active' : ''}
+            >
+              Text
+            </button>
             <span>{getHintText()}</span>
           </div>
         </div>
@@ -778,6 +818,72 @@ function DemoFigma() {
                 </Fragment>
               );
             }
+            if (shape.type === 'text') {
+              const isEditing = editingShapeId === shape.id;
+              return (
+                <Fragment key={shape.id}>
+                  {isSelected && !isEditing && (
+                    <div
+                      className="shape-tooltip"
+                      style={{
+                        left: `${shape.x}px`,
+                        top: `${shape.y}px`,
+                      }}
+                    >
+                      {shape.selectedBy.join(', ')}
+                    </div>
+                  )}
+                  {isEditing ? (
+                    <textarea
+                      value={shape.text}
+                      onChange={(e) => {
+                        const newText = e.target.value;
+                        setShapes(prevShapes => prevShapes.map(s =>
+                          s.id === shape.id ? { ...s, text: newText } : s
+                        ));
+                      }}
+                      onKeyDown={(e) => {
+                        if (e.key === 'Enter' && !e.shiftKey) {
+                          e.preventDefault();
+                          finishEditing();
+                        }
+                      }}
+                      onBlur={finishEditing}
+                      autoFocus
+                      style={{
+                        position: 'absolute',
+                        left: `${shape.x}px`,
+                        top: `${shape.y}px`,
+                        width: `${shape.width}px`,
+                        height: `${shape.height}px`,
+                        border: '1px solid #007bff',
+                        zIndex: 1000,
+                        font: 'inherit',
+                        padding: '5px',
+                        boxSizing: 'border-box',
+                      }}
+                    />
+                  ) : (
+                    <div
+                      className={`text ${isSelected ? 'selected' : ''}`}
+                      style={{
+                        position: 'absolute',
+                        left: `${shape.x}px`,
+                        top: `${shape.y}px`,
+                        width: `${shape.width}px`,
+                        height: `${shape.height}px`,
+                        display: 'flex',
+                        alignItems: 'center',
+                        justifyContent: 'center',
+                      }}
+                      onDoubleClick={() => setEditingShapeId(shape.id)}
+                    >
+                      {shape.text}
+                    </div>
+                  )}
+                </Fragment>
+              );
+            }
             return null;
           })}
         </div>
