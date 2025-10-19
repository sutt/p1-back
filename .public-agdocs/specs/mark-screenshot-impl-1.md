Perform a basic implementation of the mark-screenshot plan. The goal is to get a result of a the modified and marked image with debugging into review.

The first goal for this implementation is to accomplish "place a circle over the boston common" where the map in the screenshot will have the boston common visible in it with label. Don't overfit to this but let it help guide you on understanding an example task.

- Provide basic coord translation methods.

- provide some modification to the system/meta prompt that goes out to llm api.

- add comments in your implementation indicating limitations and 
- use "# LIMITATION [MARK-SCREENSHOT]: ...", "# MANUAL-INTERVENTION [MARK-SCREENSHOT]: ..." prefix to these comments


- When looking to add packages, update the pyproject.toml / requirements.txt and allow me to perform the commands. Otherwise don't hesitate to ask to use tools. 

- update the mark-screenshot plan with a new section detailing the choices you made and future updates that could altered or improved.