"""ENGRAM with OpenAI for embeddings and LLM."""
import os
from engram import Engram

e = Engram(
    data_dir="./example_data",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    llm_api_key=os.environ.get("OPENAI_API_KEY", ""),
)

e.remember("Testing OpenAI integration", type="episodic", salience=0.8)
results = e.recall("OpenAI", top_k=3)
print(f"Found {len(results)} memories")
print(e.status())
