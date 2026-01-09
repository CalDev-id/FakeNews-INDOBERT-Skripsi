import os
from groq import Groq
from dotenv import load_dotenv

class GroqRunTime():
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GROQ_KEY")

        self.client = Groq(
            api_key=self.api_key,
        )

    def generate_response(self, system_prompt, user_prompt):
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            # model="llama-3.1-8b-instant"
            model="llama-3.3-70b-versatile",
            # temperature=0.0,
        )
        return response.choices[0].message.content.strip()
