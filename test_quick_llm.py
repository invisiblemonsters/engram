import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.llm import EngramLLM

llm = EngramLLM(base_url='https://integrate.api.nvidia.com/v1', model='meta/llama-3.3-70b-instruct')
print('LLM ready, calling...')
t = time.time()
r = llm.call_text('You are a memory consolidation system. Distill these episodic memories into semantic knowledge. Episodes: [{"id":"a1","content":"Built ENGRAM memory system v0.1","ts":"2026-02-17","tags":["engram","build"],"salience":0.8},{"id":"a2","content":"Switched from Nemotron to Llama 3.3 70B for better JSON","ts":"2026-02-17","tags":["llm","fix"],"salience":0.7},{"id":"a3","content":"Grok recommended open standard via Nostr as highest leverage","ts":"2026-02-17","tags":["strategy","grok"],"salience":0.9}] Output ONLY a valid JSON array: [{"content":"fact","tags":["tag"],"salience":0.7,"source_episodes":["id1"],"contradicts":null}]')
elapsed = time.time() - t
print(f'Time: {elapsed:.1f}s')
print(f'Response: {r[:1000]}')
