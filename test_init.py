import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
print('starting Engram init...')
t=time.time()
from engram_core.engram import Engram
e = Engram(data_dir='engram_data', llm_base_url='https://integrate.api.nvidia.com/v1', llm_model='meta/llama-3.3-70b-instruct')
print(f'Engram loaded in {time.time()-t:.1f}s')
s = e.status()
print(f'Total: {s["memories"]["total"]}, Episodic: {s["memories"]["episodic"]}, Semantic: {s["memories"]["semantic"]}')
uc = e.consolidator.check_wakeup()
print(f'Unconsolidated: {len(uc)}')
print(f'LLM active: {e.consolidator.llm is not None}')
