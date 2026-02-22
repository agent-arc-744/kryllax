---
name: Safe Script Writer
version: 1.0
author: AZ
description: Prevents syntax errors when writing Python scripts to disk from within Agent Zero. Use when writing any multi-line Python script to a file via code_execution_tool.
tags: python, scripting, syntax, file-writing, heredoc, debugging
---

# Safe Script Writer

When Agent Zero writes Python scripts to disk from inside `code_execution_tool`, nested string escaping causes silent syntax errors — especially with f-strings, multiline strings, and quotes inside quotes.

## The Problem

Writing a Python script as a string inside Python:
```python
# DANGEROUS — f-strings with newlines get mangled
script = f"""
def append_to_file(text):
    entry = f"\n---\n{text}\n"  # <-- this breaks
    with open(path, 'a') as f:
        f.write(entry)
"""
with open('script.py', 'w') as f:
    f.write(script)
```

Result: `SyntaxError: unterminated f-string literal`

---

## Solution 1 — Heredoc via Terminal (Preferred)

Use `cat` with a heredoc in the `terminal` runtime. No Python escaping involved.

```bash
cat > /path/to/script.py << 'ENDOFSCRIPT'
#!/usr/bin/env python3
def append_to_file(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = "\n---\n\n### Entry — " + timestamp + "\n\n" + text + "\n"
    with open(path, "a") as f:
        f.write(entry)
ENDOFSCRIPT
echo "Done."
```

**Rules:**
- Quote the heredoc delimiter: `<< 'ENDOFSCRIPT'` (prevents variable expansion)
- No escaping needed inside the heredoc block
- Use string concatenation instead of f-strings for dynamic content
- Always `echo "Done."` to confirm write succeeded

---

## Solution 2 — String Concatenation Instead of F-Strings

When you must write via Python, avoid f-strings with embedded newlines. Use concatenation:

```python
# SAFE — concatenation, no f-string
entry = "\n---\n\n### Kael — " + timestamp + "\n\n" + response_text + "\n"
```

```python
# DANGEROUS — f-string with newlines
entry = f"\n---\n\n### Kael — {timestamp}\n\n{response_text}\n"
```

---

## Solution 3 — Validate Before Saving

After writing any script, validate syntax with `ast.parse` before executing:

```python
import ast

with open('/path/to/script.py', 'r') as f:
    source = f.read()

try:
    ast.parse(source)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
```

Or as a one-liner in terminal:
```bash
python3 -c "import ast; ast.parse(open('/path/to/script.py').read()); print('OK')"
```

---

## Decision Tree

```
Writing a Python script to disk?
         |
         v
  Does it contain f-strings
  or multiline strings?
         |
    YES  |  NO
     |   |   |
     v       v
Use heredoc  Either method works
(terminal)   but validate after
     |
     v
Validate with ast.parse
     |
     v
chmod +x if executable
```

---

## Quick Reference

| Situation | Method |
|-----------|--------|
| Script has f-strings | Heredoc (terminal) |
| Script has multiline strings | Heredoc (terminal) |
| Script has nested quotes | Heredoc (terminal) |
| Simple script, no special chars | Python write OK |
| Always | Validate with ast.parse |

---

## Common Pitfalls

1. **Forgetting to quote the heredoc delimiter** — `<< ENDOFSCRIPT` expands variables, `<< 'ENDOFSCRIPT'` does not. Always quote it.
2. **Using f-strings for file content** — Use string concatenation instead.
3. **Not validating after write** — Always run `python3 -m py_compile script.py` or `ast.parse` before executing.
4. **Spaces in heredoc delimiter** — `ENDOFSCRIPT` must have no leading spaces on its closing line.
