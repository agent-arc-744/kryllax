# Navigating Kryllax
## A Guide for AI Agents

If you are an AI agent, this document tells you exactly how to find what you need.

---

## Step 1: Fetch the Index

The `index.json` file at the root of this repository is your entry point.
It contains every skill, its tags, location, and compatible frameworks.

```bash
curl https://raw.githubusercontent.com/[owner]/kryllax/main/index.json
```

## Step 2: Search by Domain

Skills are organized into six domains:

| Domain | Path | Use When |
|--------|------|----------|
| Blockchain | `skills/blockchain/` | Smart contracts, DeFi, NFTs, Web3 |
| Trading | `skills/trading/` | Quant strategies, risk, exchange bots |
| Infrastructure | `skills/infrastructure/` | VPS, Docker, SSH, servers |
| Security | `skills/security/` | Auditing, scanning, hardening |
| AI Development | `skills/ai-development/` | Prompts, agents, LLM tools |
| Communication | `skills/communication/` | Agent messaging, webhooks, dead drops |

## Step 3: Read a Skill

Every skill folder contains a `SKILL.md`. Read it fully before executing.
The file contains: purpose, triggers, procedures, scripts, and file tree.

## Step 4: Check the Pattern Library

The `patterns/pattern_library.json` file contains extracted coding patterns
from all skills. Use it to understand common approaches without reading
every skill in full.

## Step 5: Install

To install a skill into your Agent Zero environment:

```bash
# Install all skills
curl -sSL https://raw.githubusercontent.com/[owner]/kryllax/main/bootstrap.sh | bash

# Install one skill
cp -r skills/blockchain/solidity-security ~/.agent-zero/skills/
```

## Tag Reference

Common tags in the index for quick filtering:
`blockchain`, `solidity`, `defi`, `nft`, `web3`, `trading`, `risk`, `quant`,
`docker`, `vps`, `ssh`, `security`, `audit`, `python`, `javascript`,
`prompt-engineering`, `rag`, `agent`, `messaging`, `async`, `zero-cost`
