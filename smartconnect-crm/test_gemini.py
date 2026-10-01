import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-flash-latest")
response = model.generate_content("Say hello in one short sentence.")
print("Response from Gemini:", response.text)