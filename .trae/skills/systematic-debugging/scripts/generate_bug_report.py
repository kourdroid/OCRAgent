#!/usr/bin/env python3
"""
Bug Report Template Generator

Generates a markdown bug report template with:
- Environment info (OS, Node, Python, etc.)
- Git state (branch, last commit)
- Reproduction steps template

Usage:
    python generate_bug_report.py [output_file]
    python generate_bug_report.py  # Prints to stdout
"""

import os
import sys
import platform
import subprocess
from datetime import datetime


def run_command(cmd: str) -> str:
    """Run a shell command and return output, or empty string if fails."""
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_environment_info() -> dict:
    """Gather environment information."""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "node": run_command("node --version"),
        "npm": run_command("npm --version"),
        "git_branch": run_command("git branch --show-current"),
        "git_commit": run_command("git rev-parse --short HEAD"),
        "git_status": "clean" if not run_command("git status --porcelain") else "dirty",
        "cwd": os.getcwd(),
        "timestamp": datetime.now().isoformat(),
    }


def generate_template(env: dict) -> str:
    """Generate the bug report markdown template."""
    return f"""# Bug Report

**Date:** {env['timestamp']}

## Environment

| Property | Value |
|----------|-------|
| OS | {env['os']} |
| Python | {env['python']} |
| Node | {env['node']} |
| npm | {env['npm']} |
| Git Branch | {env['git_branch']} |
| Git Commit | {env['git_commit']} |
| Git Status | {env['git_status']} |
| Working Directory | {env['cwd']} |

## Bug Description

**Summary:** [One sentence describing the bug]

**Severity:** [ ] Critical [ ] High [ ] Medium [ ] Low

## Steps to Reproduce

1. [First step]
2. [Second step]
3. [Third step]

## Expected Behavior

[What should happen]

## Actual Behavior

[What actually happens]

## Error Message / Stack Trace

```
[Paste error here]
```

## Screenshots / Recordings

[Attach if applicable]

## Minimal Reproduction

- [ ] Created minimal reproduction case
- [ ] Link: [URL or file path]

## Investigation Notes

### Hypothesis

[What you think is causing this]

### Evidence

- [Observation 1]
- [Observation 2]

### Attempted Fixes

| Attempt | Result |
|---------|--------|
| [What you tried] | [What happened] |

## Root Cause (to be filled after investigation)

[Technical explanation of why this happened]

## Fix Applied

[What was changed and why]

## Regression Test

- [ ] Test added: `tests/path/to/test.py::test_name`

## Prevention

[What was added to prevent recurrence]
"""


def main():
    env = get_environment_info()
    template = generate_template(env)
    
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
        with open(output_file, 'w') as f:
            f.write(template)
        print(f"Bug report template written to: {output_file}")
    else:
        print(template)


if __name__ == "__main__":
    main()
