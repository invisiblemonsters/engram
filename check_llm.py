import sys, os, io
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stderr = open(os.devnull, 'w')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
from engram_core.llm import EngramLLM
llm = EngramLLM()
print(f"URL: {llm.url}")
print(f"Model: {llm.model}")
print(f"Key: {str(llm.api_key)[:20] if llm.api_key else 'None'}...")
print(f"Is Anthropic: {llm._is_anthropic}")
print(f"Available: {llm.is_available()}")
print(f"Fallbacks: {len(llm._fallback_backends)}")
for fb in llm._fallback_backends:
    print(f"  - {fb['name']}: {fb['model']}")
