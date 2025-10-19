Create a plan docuemnt for implementing the this feature:

We're going to add another feature to this screenshot to prompt pipeline: we're going to add markings to the screenshot to provide visual context to the image corresponding to map-viewport of mapCenter, mapBounds. 
- add the the modified marked image to the debug_screenshots when debugging mode is on.

We'll also need to supply coord translation between canvas based coords and map based coords of lat/long.
- remember that shapes use integer coords and these are the tool calls we want the ai api to construct for us.

Provide flags to switch a lat/long based way and a canvas-based way to provide context about the markings for the ai system (default canvas coords) the way you deliver the prompt instruction, prompt context, and markings on the image.