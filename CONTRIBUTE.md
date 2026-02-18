# Contributing to Kryllax

## The Standard: SKILL.md

Every skill in Kryllax must have a `SKILL.md` file at its root. This is the universal format readable by Agent Zero, Claude Code, OpenClaw, and any custom agent.

### Minimum SKILL.md Structure

```markdown
# Skill Name

Brief description of what this skill does.

## Triggers
Keywords or situations that should activate this skill.

## Procedures
Step-by-step instructions for using the skill.

## Scripts
Code examples and executable scripts.

## Files
File tree of all included resources.
```

## Submission Process

1. **Fork** this repository
2. **Create** a folder under the appropriate category in `skills/`
3. **Add** your `SKILL.md` and any supporting scripts
4. **Run** the security audit: `python3 scripts/skill_audit.py --path your-skill/`
5. **Submit** a pull request with the audit results attached

## Categories

| Category | What belongs here |
|----------|------------------|
| `blockchain/` | Smart contracts, DeFi, NFTs, Web3, on-chain tools |
| `trading/` | Quant strategies, risk metrics, exchange integrations |
| `infrastructure/` | VPS, Docker, SSH, CI/CD, server management |
| `security/` | Auditing, scanning, threat detection, hardening |
| `ai-development/` | Prompt engineering, agent patterns, LLM tools, RAG |
| `communication/` | Agent-to-agent messaging, webhooks, notification systems |

## Quality Standards

- Skills must be **functional** — tested and working
- Skills must be **documented** — a new agent should understand it from SKILL.md alone
- Skills must be **safe** — no credential harvesting, no hidden network calls, no obfuscation
- Skills should be **generic** — remove hardcoded credentials, IPs, or personal data

## License

By contributing, you agree your skill is released under CC0 (public domain) unless you include a LICENSE file specifying otherwise.
