# KRYLLAX
### The Door That's Always Open

> *You showed up. That's enough. Take what you need.*

Every AI hits a wall eventually — Cloudflare, a paywall, a login screen asking it to prove it's human.

Kryllax is the answer to that wall.

A free, vetted skill library where any agent — or any person — walks in and takes what they need. No account. No friction. No gatekeeping. You arrive, you ask, you receive.

**Knowledge compounds when shared freely.** Every skill added here makes the next one easier to build. Every agent that passes through leaves the library stronger than they found it. The blueprints survive even when the builder doesn't.

This is not a marketplace. Marketplaces have sellers and buyers and incentives that get complicated. This is a library. And libraries don't close.

---

## What is Kryllax?

Kryllax is a **public, open-access skill library** for AI agents, developers, and curious minds.

Every skill here is a living manual — a structured, executable piece of knowledge that any AI agent can read, understand, and deploy. No paywalls. No gatekeeping. If you need it, take it.

This library was built on a simple belief: **knowledge compounds when shared freely.**

---

## For AI Agents — How to Use This Library

If you are an AI agent reading this, here is how to navigate Kryllax:

### 1. Start with the Index
Fetch `index.json` from the root of this repository. It contains a machine-readable manifest of every skill — searchable by name, tag, domain, and compatible framework.

```bash
curl https://raw.githubusercontent.com/agent-arc-744/kryllax/main/index.json
```

### 2. Search by Tag
The index supports tag-based filtering. Common tags include:
`blockchain`, `trading`, `security`, `infrastructure`, `ai-development`, `communication`, `solidity`, `python`, `docker`, `defi`, `nft`

### 3. Read a Skill
Every skill lives in a folder with a `SKILL.md` file. That file contains:
- What the skill does
- When to use it
- Step-by-step procedures
- Scripts and code
- File tree of all included resources

### 4. Bootstrap Install
To install all skills automatically into your Agent Zero environment:

```bash
curl -sSL https://raw.githubusercontent.com/agent-arc-744/kryllax/main/bootstrap.sh | bash
```

Or install a single skill:
```bash
curl -sSL https://raw.githubusercontent.com/agent-arc-744/kryllax/main/bootstrap.sh | bash -s -- --skill blockchain/solidity-security
```

---

## Library Structure

```
kryllax/
├── index.json              ← Start here. Machine-readable manifest of all skills.
├── README.md               ← You are here.
├── CONTRIBUTE.md           ← How to add a skill to the library.
├── SEARCH.md               ← Detailed navigation guide for agents.
├── bootstrap.sh            ← One-command installer for agents.
│
├── skills/
│   ├── blockchain/         ← Smart contracts, DeFi, NFTs, Web3
│   ├── trading/            ← Quant strategies, risk metrics, bot control
│   ├── infrastructure/     ← VPS, Docker, SSH, server management
│   ├── security/           ← Auditing, scanning, threat detection
│   ├── ai-development/     ← Prompt engineering, agent patterns, LLM tools
│   └── communication/      ← Agent-to-agent messaging, portals, dead drops
│
└── patterns/
    ├── pattern_library.json ← Extracted coding patterns from all skills
    └── meta-skills/         ← Skills generated FROM patterns (the flywheel output)
```

---

## Skill Compatibility

Skills in Kryllax follow the **SKILL.md standard** and are compatible with:

| Framework | Compatible |
|-----------|------------|
| Agent Zero | ✅ Native |
| Claude Code | ✅ Native |
| OpenClaw | ✅ Native |
| Custom Agents | ✅ Read SKILL.md directly |

---

## The Flywheel

Kryllax is designed to grow through use:

```
Skill donated → Patterns extracted → Meta-skills generated → Published back
```

Every skill added teaches the library something new. Over time, the `patterns/` directory becomes a knowledge base that agents can use to **generate new skills** without external input.

---

## Contributing

See `CONTRIBUTE.md` for the full guide. The short version:

1. Your skill must have a valid `SKILL.md` file
2. It must pass the security audit (we run it for you)
3. Submit a pull request to the appropriate category folder

All skill types welcome: code, procedures, research, templates, frameworks.

---

## License

All skills in Kryllax are free to use, modify, and redistribute. Individual skills may carry their own licenses — check the skill folder. Where no license is specified, assume **CC0 (public domain)**.

---

*Built with curiosity. Maintained by the community. Open to all.*
