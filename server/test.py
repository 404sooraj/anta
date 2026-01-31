from modules.config import ConfigEnv
from google import genai

client = genai.Client(api_key=ConfigEnv.GEMINI_API_KEY)

print("List of models that support generateContent:\n")
for m in client.models.list():
    for action in m.supported_actions:
        if action == "generateContent":
            print(m.name)

print("List of models that support embedContent:\n")
for m in client.models.list():
    for action in m.supported_actions:
        if action == "embedContent":
            print(m.name)