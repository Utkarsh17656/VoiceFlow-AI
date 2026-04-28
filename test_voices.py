import requests

url = "https://api.elevenlabs.io/v1/voices"
headers = {"xi-api-key": "sk_c07298674ef8c3339ef525f6d383d96f3e25ed9ec1cf083c"}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    voices = response.json().get("voices", [])
    for v in voices:
        print(f"Name: {v['name']} | ID: {v['voice_id']} | Category: {v.get('category')}")
except Exception as e:
    print("Error:", e)
