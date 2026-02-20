"""ENGRAM with Ollama for embeddings and LLM."""
from engram import Engram

e = Engram(
    data_dir="./example_data",
    embedding_provider="ollama",
    embedding_model="nomic-embed-text",
    llm_provider="ollama",
    llm_model="llama3.2",
)

e.remember("Testing Ollama integration", type="episodic", salience=0.8)
results = e.recall("Ollama", top_k=3)
print(f"Found {len(results)} memories")

# With LLM: consolidation and dreams work
report = e.sleep()
print(f"Sleep report: {report}")
