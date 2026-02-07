---
name: Skill Creator
description: Create new Cursor Skills following the standard directory structure.
disable-model-invocation: false
---

# Skill Creator

Use this skill to create new skills for the ASAP Protocol agents.

## Usage

To create a new skill, run the initialization script:

```bash
python3 .cursor/skills/skill-creator/scripts/init_skill.py <skill-name>
```

**Example:**
```bash
python3 .cursor/skills/skill-creator/scripts/init_skill.py my-new-feature
```

## What it does
1.  Creates `.cursor/skills/<skill-name>/`
2.  Generates `SKILL.md` template
3.  Creates `scripts/` directory with a sample script

## Standards
-   **Naming**: Kebab-case (`my-skill-name`)
-   **Structure**: Always use the directory structure.
-   **Scripts**: Python scripts should use `uv` or standard lib.
