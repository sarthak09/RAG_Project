import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
if os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

class LLM:
    def __init__(self, model_name: str):
        self.llm = init_chat_model(model=model_name)