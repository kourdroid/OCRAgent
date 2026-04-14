#!/usr/bin/env python3
"""
Code Review Checklist Generator

Generates a markdown checklist for backend code reviews.
Can be customized for different aspects (security, performance, etc.)

Usage:
    python code_review_checklist.py [type] [output_file]
    python code_review_checklist.py                    # Full checklist to stdout
    python code_review_checklist.py security           # Security-focused checklist
    python code_review_checklist.py pr-review.md       # Full checklist to file
"""

import sys
from datetime import datetime


CHECKLISTS = {
    "naming": """
## Naming Conventions

- [ ] Function names are verb + noun (e.g., `getUserById`, `createOrder`)
- [ ] Boolean variables use is/has/can/should prefix
- [ ] Constants are SCREAMING_SNAKE_CASE
- [ ] No abbreviations (except common: id, url, api)
- [ ] Names describe WHAT, not HOW
""",
    
    "functions": """
## Function Design

- [ ] Single responsibility (does one thing well)
- [ ] No more than 3-4 parameters
- [ ] No boolean parameters (use options object or enums)
- [ ] Pure functions where possible (no hidden side effects)
- [ ] Side effects are explicit and documented
- [ ] All paths return consistent types
""",
    
    "error_handling": """
## Error Handling

- [ ] No swallowed errors (catch without handling)
- [ ] Specific error types used (not generic Error)
- [ ] Error messages are helpful (include context)
- [ ] Errors are logged with stack trace
- [ ] User-facing errors are sanitized (no internal details)
- [ ] Retries have exponential backoff
""",
    
    "validation": """
## Input Validation

- [ ] All external inputs validated at boundaries
- [ ] Using schema validation (Zod, Yup, Pydantic)
- [ ] No trust of internal calls (validate anyway)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
""",
    
    "security": """
## Security

- [ ] No hardcoded secrets or credentials
- [ ] Secrets from environment variables
- [ ] Auth tokens are short-lived
- [ ] Rate limiting on sensitive endpoints
- [ ] CORS properly configured
- [ ] Input sanitization for file uploads
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection on mutations
""",
    
    "database": """
## Database

- [ ] Queries are parameterized (no string concatenation)
- [ ] Indexes exist for frequently queried columns
- [ ] N+1 query patterns avoided
- [ ] Connection pooling configured
- [ ] Transactions used for multi-step operations
- [ ] Migrations are reversible
""",
    
    "testing": """
## Testing

- [ ] Unit tests cover happy path
- [ ] Unit tests cover error cases
- [ ] Edge cases tested
- [ ] Assertions are specific (not just "no error")
- [ ] Tests are independent (no shared state)
- [ ] Mocks used appropriately (not too many)
""",
    
    "logging": """
## Logging & Observability

- [ ] Structured logging (JSON format)
- [ ] Request IDs propagated
- [ ] Sensitive data not logged
- [ ] Appropriate log levels used
- [ ] External calls logged with duration
""",
    
    "performance": """
## Performance

- [ ] No blocking I/O in hot paths
- [ ] Caching for expensive operations
- [ ] Pagination for list endpoints
- [ ] Database queries optimized
- [ ] Memory leaks prevented (listeners removed)
"""
}


def generate_full_checklist() -> str:
    """Generate the complete checklist."""
    output = f"""# Backend Code Review Checklist

**Date:** {datetime.now().strftime('%Y-%m-%d')}

**PR Link:** [Insert PR URL]

**Reviewer:** [Your name]

---

"""
    for section in CHECKLISTS.values():
        output += section + "\n"
    
    output += """
---

## Summary

**Approved:** [ ] Yes  [ ] No  [ ] Needs changes

**Comments:**

[Add review comments here]
"""
    return output


def generate_focused_checklist(focus: str) -> str:
    """Generate a focused checklist."""
    if focus not in CHECKLISTS:
        available = ", ".join(CHECKLISTS.keys())
        return f"Unknown checklist type: {focus}\nAvailable: {available}"
    
    return f"""# {focus.title()} Code Review Checklist

**Date:** {datetime.now().strftime('%Y-%m-%d')}

---

{CHECKLISTS[focus]}

---

**Notes:**

[Add review notes here]
"""


def main():
    args = sys.argv[1:]
    
    # Determine what to generate
    if not args:
        print(generate_full_checklist())
    elif args[0] in CHECKLISTS:
        # Focused checklist
        output = generate_focused_checklist(args[0])
        if len(args) > 1:
            with open(args[1], 'w') as f:
                f.write(output)
            print(f"Checklist written to: {args[1]}")
        else:
            print(output)
    elif args[0].endswith('.md'):
        # Output to file
        with open(args[0], 'w') as f:
            f.write(generate_full_checklist())
        print(f"Full checklist written to: {args[0]}")
    else:
        print(f"Unknown argument: {args[0]}")
        print(f"Available types: {', '.join(CHECKLISTS.keys())}")
        print("Or specify a .md filename for output")


if __name__ == "__main__":
    main()
