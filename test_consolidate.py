"""Test consolidation LLM call."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.llm import EngramLLM

llm = EngramLLM(base_url='https://integrate.api.nvidia.com/v1', model='nvidia/nemotron-3-nano-30b-a3b')

episodes = [
    {'id': 'test1', 'content': 'Built ENGRAM memory system with 12 modules', 'timestamp': '2026-02-17', 'tags': ['engram'], 'salience': 0.8},
    {'id': 'test2', 'content': 'Pushed ENGRAM v0.1 to GitHub at github.com/invisiblemonsters/engram', 'timestamp': '2026-02-17', 'tags': ['github'], 'salience': 0.7},
    {'id': 'test3', 'content': 'Grok recommended ENGRAM as open standard via Nostr', 'timestamp': '2026-02-17', 'tags': ['strategy'], 'salience': 0.6},
]

prompt = (
    "You are a memory consolidation system. Given these episodic memories, "
    "distill them into semantic knowledge (facts, rules, lessons).\n\n"
    "Episodic memories:\n" + json.dumps(episodes, indent=2) + "\n\n"
    "Output ONLY a valid JSON array of distilled facts:\n"
    '[{"content": "fact", "tags": ["tag"], "salience": 0.7, "source_episodes": ["id"], "contradicts": null}]'
)

print("Calling LLM...")
result = llm.call_text(prompt, system="You are ENGRAM. Output ONLY valid JSON array. No markdown, no code fences, no explanation.")
print(f"Result type: {type(result)}")
print(f"Result: {repr(result[:800]) if result else 'None'}")

if result:
    # Try parsing
    try:
        start = result.find("[")
        end = result.rfind("]") + 1
        if start >= 0 and end > 0:
            parsed = json.loads(result[start:end])
            print(f"\nParsed {len(parsed)} facts:")
            for f in parsed:
                print(f"  - {f.get('content', '???')}")
        else:
            print("No JSON array found in response")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Attempted to parse: {result[start:end][:200]}")
