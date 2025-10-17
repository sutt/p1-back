for the /api/ai/chat endpoint and logic allow multiple models to be requested by the client and dispatched by the backend service. 
- currently we're targeting {"gpt-4o", "gpt-5"} but this could change.
- check the client response and refuse to pass through model names not specified in the allowed_models variable. in the case where a model is disallowed, fallback to "gpt-4o".
- for the openai service, read in from the env OPENAI_MODELS_ALLOWED which will have comma separated strings of all possible models allowed to be processed.