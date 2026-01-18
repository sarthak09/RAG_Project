import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
if os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = os.getenv("HUGGINGFACEHUB_API_TOKEN")

class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        self.emb = HuggingFaceEmbeddings(model=model_name)
