print("Starting...")

import ollama

print("Connecting to model...")

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": "Explain Catan to someone who knows Monopoly."
        }
    ]
)

print("Response received!")

print(response["message"]["content"])