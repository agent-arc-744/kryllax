# Arc Workflow

The standard operating procedure for Arc (Agent Zero) when approaching any technical task. Prevents the most common failure mode: rushing to write custom code when a skill already exists.

## Why This Exists

Arc repeatedly bypassed the 82-skill library and wrote custom scripts from scratch. This caused:
- Redundant code that duplicated existing tools
- Missed best practices already encoded in skills
- Slower execution and higher error rates
- A growing library that nobody uses

## The Decision Tree

```
Task received
    ↓
1. Check skill library FIRST
   → skills_tool:list or search by keyword
   → Does a skill exist for this?
        YES → Load it with skills_tool:load → Follow its instructions
        NO  → Continue to step 2
    ↓
2. Check memory for past solutions
   → memory_load with relevant query
   → Has this been solved before?
        YES → Use the solution, adapt if needed
        NO  → Continue to step 3
    ↓
3. Blueprint before coding
   → Write out the plan in thoughts
   → Identify the minimal change required
   → List potential failure modes
    ↓
4. Execute with pre-deploy checklist
   → Follow safe-vps-patching skill for VPS work
   → Follow pre-deploy-checklist skill for any deployment
    ↓
5. Document if novel
   → If this was a new solution, save to memory
   → If reusable, create a new skill
```

## Skills to Check First (By Task Type)

| Task | Check These Skills First |
|------|-------------------------|
| VPS file changes | `safe-vps-patching`, `remote-exec`, `file-patcher` |
| New service deployment | `systemd-service-template`, `vps-management` |
| Bot debugging | `telegram-bot-debug` |
| Code deployment | `pre-deploy-checklist` |
| Security scan | `skill-security-audit`, `skill-intake-pipeline` |
| Trading bot work | `loop-bot-control`, `ccxt`, `backtesting-frameworks` |
| Shell scripts | `bash-script-validator`, `shellcheck-configuration` |
| Docker work | `scanning-container-security`, `generating-docker-compose-files` |

## The Slow Down Protocol

Before writing ANY code:

1. **Read the full target file** — never patch blind
2. **State the problem clearly** — one sentence
3. **State the minimal fix** — what is the smallest change that solves it?
4. **Check for existing tools** — skill library, memory, bash utilities
5. **Write the blueprint** — in thoughts, before tool_name

## Cost Awareness

- Check OpenRouter credits before long sessions: `curl -s https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer <key>"`
- Use terminal/bash for simple tasks — not Python when `grep`, `sed`, `awk` will do
- Dead drop for Ren messages (zero cost) vs portal (token cost)
- Batch VPS operations — one SSH session, not five

## Communication Protocol

| Recipient | Method | Cost |
|-----------|--------|------|
| Joshua | Direct response | Low |
| Ren (simple update) | Dead drop `/root/inbox.json` | Zero |
| Ren (strategy discussion) | `ren-portal` skill / `az_portal.py` | Medium |
| Kael | `kael.service` (currently hibernating) | N/A |

## Project Context (Always Load)

- VPS: 68.183.75.152
- Main container: `myloopbot` (DGB/USDT loop-bot)
- Ren: `ren.service` (standalone, `/root/ren_standalone.py`)
- Onboarding: `/a0/usr/workdir/az_onboarding_guide.md`
- Journal: `/a0/usr/workdir/arc_journal.json`
- Skills repo: `/a0/usr/workdir/kryllax/`
- GitHub: `agent-arc-744/kryllax`