import os
from fireworks.client import Fireworks
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def generate_chat_response():
    # 1. Fetch the API key from the environment variables
    api_key = os.environ.get("FIREWORKS_API_KEY")
    
    if not api_key:
        raise ValueError("Error: FIREWORKS_API_KEY environment variable not found. Please set it before running.")

    # 2. Initialize the Fireworks client
    client = Fireworks(api_key=api_key)

    # 3. Call the serverless chat completions endpoint
    response = client.chat.completions.create(
        model="accounts/fireworks/models/minimax-m2p7",
        messages=[
            {
                "role": "user",
                "content": "Explain quantum computing in exactly two sentences.",
            }
        ],
        temperature=0.7,
        max_tokens=150
    )

    # 4. Print the output
    print("--- Model Response ---")
    print(response.choices[0].message.content)

if __name__ == "__main__":
    generate_chat_response()
