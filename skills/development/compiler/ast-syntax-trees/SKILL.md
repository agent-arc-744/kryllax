---
name: ast-syntax-trees
description: Understanding Abstract Syntax Trees (AST) and syntax tree visualization. Essential knowledge for compiler development, code analysis, and understanding why AI models struggle with syntax generation. Use when working with compilers, code parsers, or debugging syntax errors.
version: "1.0"
author: Arc (documented for Joshua)
tags: [ast, syntax-tree, compiler, parsing, code-analysis]
---

# Abstract Syntax Trees (AST) & Syntax Trees

## Why This Matters for Our Project

Joshua identified a core truth: AI models like Arc generate code as **text**, not as
structured syntax trees. This is why syntax errors occur — we're typing code the way
a human types, not the way a compiler thinks.

Understanding ASTs is the foundation for building tools that generate *structurally
correct* code rather than text that *looks like* code.

## Key Resources

- **Visual Syntax Tree Tool**: http://mshang.ca/syntree/
  - Draw and visualize syntax trees interactively
  - Great for understanding tree structure before writing parsers

- **AST Introduction Guide**: https://dev.to/headwindz/introduction-to-abstract-syntax-trees-ast-563l
  - Comprehensive intro to what ASTs are and how they work
  - Covers real-world use cases in JavaScript/TypeScript tooling

## What is an AST?

An Abstract Syntax Tree is a tree representation of the structure of source code.
Each node represents a construct in the language.

```
Source Code:          x = 1 + 2

AST Representation:
        Assignment
       /          \
  Variable       BinaryOp
    (x)         /   |   \
              Add  Int  Int
                   (1)  (2)
```

## Why AI Struggles With Syntax

```
Human compiler thinks:  AST node → serialize → text
AI model thinks:        text → text → text (no tree in mind)
```

The fix is a **code generation layer** that builds AST nodes programmatically
then serializes them — eliminating the entire class of syntax errors.

## Python AST Module (Built-in)

```python
import ast

# Validate syntax before deploying
def validate_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, "Valid"
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"

# Example usage
code = "def hello():\n    print('world')"
valid, msg = validate_python(code)
print(f"Syntax: {msg}")
```

## Build AST Nodes Programmatically

```python
import ast

# Build a function definition as AST (never has syntax errors)
func = ast.FunctionDef(
    name='hello',
    args=ast.arguments(posonlyargs=[], args=[], vararg=None,
                       kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
    body=[ast.Expr(value=ast.Call(
        func=ast.Name(id='print', ctx=ast.Load()),
        args=[ast.Constant(value='world')],
        keywords=[]
    ))],
    decorator_list=[],
    returns=None
)
ast.fix_missing_locations(func)
# This CANNOT have syntax errors — it's built structurally
```

## Syntax Tree Visualization

Use http://mshang.ca/syntree/ with bracket notation:
```
[S [NP [D The] [N cat]] [VP [V sat] [PP [P on] [NP [D the] [N mat]]]]]
```

## Related Skills
- `compiler-development` — Full LLVM compiler pipeline
- `llvm-learning` — LLVM learning resources
- `hypothesis-driven-debugging` — Systematic debugging approach
- `syntax-guardian` (Arc custom) — Pre-deploy syntax validation
