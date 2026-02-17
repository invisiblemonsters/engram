"""Test ENGRAM LLM backend with auto-detection."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.llm import EngramLLM

llm = EngramLLM()
print(f"URL: {llm.url}")
print(f"Model: {llm.model}")
print(f"Has key: {bool(llm.api_key)}")
print(f"Available: {llm.is_available()}")

if llm.is_available():
    result = llm.call('Output a JSON object with key "status" and value "engram_alive"')
    print(f"JSON call: {result}")

    text = llm.call_text("Say exactly: ENGRAM LLM BACKEND OPERATIONAL")
    print(f"Text call: {text}")
else:
    print("No LLM backend reachable")
