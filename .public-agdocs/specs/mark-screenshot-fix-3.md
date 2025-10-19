Great so there's two issues to explore here.

Let's try to first perform a hard-coded fix to see if we can match on this example and then generalize from there.

Explore these issues:
1) the pixel size of the screenshot sent by the client doesn't nec match the canvas-coords which are model-based coords not nec connected to screen pixels (the canvas is the client-side  user drawing pad not a pure html element), in this case as you noted the actual jpeg is (1097,1080) but the coords we want to mark correspond to the viewport of ((0,0),(1280, 1260)).
2) The client is sending a partial screenshot of the full view: it does not include the top
    - In this the topleft corner of screenshot_mark will be (0,0)

Let's address #1 to start here. Adjust the coord translation methods and run the testing script to produce a new marked screenshot.