#!/usr/bin/env python3
"""
Throwaway script to get available models for function calling from OpenAI's API.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Initialize OpenAI client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Get all available models
    models = client.models.list()

    # Filter models that support function calling
    # Function calling is generally supported by gpt-4 and gpt-3.5-turbo variants
    function_calling_models = []

    print("Available models from OpenAI API:\n")
    print("-" * 80)

    for model in models.data:
        model_id = model.id

        # Check if it's a GPT model that likely supports function calling
        # Function calling is supported by gpt-4*, gpt-3.5-turbo*, and newer models
        if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5-turbo']):
            function_calling_models.append(model_id)
            print(f"✓ {model_id}")

    print("-" * 80)
    print(f"\nTotal models supporting function calling: {len(function_calling_models)}")

    # Print them sorted for easier reading
    print("\nSorted list:")
    for model_id in sorted(function_calling_models):
        print(f"  - {model_id}")

if __name__ == "__main__":
    main()
