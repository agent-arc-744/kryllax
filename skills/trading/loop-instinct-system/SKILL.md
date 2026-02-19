---
name: loop-instinct-system
version: 1.0.0
description: Continuous learning instinct engine for trading bots. Manages named instincts with confidence scoring (0.0-1.0) that evolve based on trade outcomes. Integrates with LLM-based trading agents via tag injection.
tags: [trading, machine-learning, instincts, confidence-scoring, loop-bot]
author: arc
platforms: [agent-zero, claude-code]
---

# Loop Instinct System

A lightweight continuous learning engine that gives trading AIs persistent, evolving instincts based on real trade outcomes.

## Concept

Instincts are named behavioral tendencies with confidence scores:
- Score 0.0-0.3: Weak / suppressed
- Score 0.3-0.7: Active / normal
- Score 0.7-1.0: Strong / dominant

The AI uses `[INSTINCT:name]` tags in responses to activate instincts. The engine reinforces or decays scores based on trade P&L outcomes.

## Core Engine

Save as `instinct_engine.py`:

```python
import json, os
from datetime import datetime

INSTINCT_FILE = "/app/data/instincts.json"

DEFAULT_INSTINCTS = {
    "range_adjustment": {"confidence": 0.6, "description": "Widen range in high volatility", "activations": 0, "wins": 0},
    "accumulation_aggression": {"confidence": 0.5, "description": "Increase DCA in fear markets", "activations": 0, "wins": 0},
    "patience_mode": {"confidence": 0.7, "description": "Hold positions in sideways markets", "activations": 0, "wins": 0},
    "profit_lock": {"confidence": 0.6, "description": "Take profits at resistance levels", "activations": 0, "wins": 0}
}

def load_instincts() -> dict:
    if os.path.exists(INSTINCT_FILE):
        with open(INSTINCT_FILE) as f:
            return json.load(f)
    save_instincts(DEFAULT_INSTINCTS)
    return DEFAULT_INSTINCTS

def save_instincts(instincts: dict):
    os.makedirs(os.path.dirname(INSTINCT_FILE), exist_ok=True)
    with open(INSTINCT_FILE, "w") as f:
        json.dump(instincts, f, indent=2)

def get_context_injection() -> str:
    instincts = load_instincts()
    active = {k: v for k, v in instincts.items() if v["confidence"] >= 0.5}
    if not active:
        return ""
    lines = ["
[INSTINCT CONTEXT]"]
    for name, data in active.items():
        lines.append(f"- {name} (confidence: {data["confidence"]:.2f}): {data["description"]}")
    lines.append("Use [INSTINCT:name] tag to activate an instinct in your response.")
    return "
".join(lines)

def reinforce(instinct_name: str, success: bool, magnitude: float = 0.05):
    instincts = load_instincts()
    if instinct_name not in instincts:
        return
    instincts[instinct_name]["activations"] += 1
    if success:
        instincts[instinct_name]["wins"] += 1
        instincts[instinct_name]["confidence"] = min(1.0, instincts[instinct_name]["confidence"] + magnitude)
    else:
        instincts[instinct_name]["confidence"] = max(0.0, instincts[instinct_name]["confidence"] - magnitude)
    save_instincts(instincts)

def parse_instinct_tags(text: str) -> list:
    import re
    return re.findall(r"\[INSTINCT:(\w+)\]", text)
```

## Integration

In your LLM chat handler:
```python
from instinct_engine import get_context_injection, parse_instinct_tags, reinforce

# 1. Inject instinct context into system prompt
system_prompt += get_context_injection()

# 2. After response, parse activated instincts
activated = parse_instinct_tags(response)

# 3. After trade outcome, reinforce
for instinct in activated:
    reinforce(instinct, success=(profit > 0))
```

## Notes
- Instinct file persists across container restarts (stored in /app/data/)
- Default decay rate: 0.05 per activation
- Confidence floor: 0.0, ceiling: 1.0
