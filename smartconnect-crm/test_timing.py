import os, time, requests
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")
print("Key found:", bool(key))

for model in ["gemini-flash-latest", "gemini-flash-lite-latest"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    start = time.time()
    try:
        r = requests.post(
            url,
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": "Reply with the single word OK."}]}]},
            timeout=60,
        )
        print(model, "| status:", r.status_code, "| seconds:", round(time.time() - start, 1))
        print(r.text[:200].replace("\n", " "))
    except Exception as e:
        print(model, "| failed after", round(time.time() - start, 1), "seconds:", type(e).__name__)