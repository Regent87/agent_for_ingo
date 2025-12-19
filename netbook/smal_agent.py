from smolagents import CodeAgent, DuckDuckGoSearchTool, InferenceClientModel
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
model = InferenceClientModel(api_key=HF_TOKEN)

agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=model)

result = agent.run("Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?")
print(result)