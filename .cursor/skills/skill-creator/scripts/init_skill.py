#!/usr/bin/env python3
import sys
import os
from pathlib import Path

SKILL_TEMPLATE = """---
name: {title}
description: Description of what this skill does.
disable-model-invocation: false
---

# {title}

## Purpose
Describe the purpose of this skill.

## Usage
Describe how to use this skill.
"""

def init_skill(skill_name):
    # Validate name
    if " " in skill_name or not skill_name.islower():
        print("Error: Skill name must be kebab-case (lowercase, no spaces).")
        sys.exit(1)

    # Determine paths
    # Assumes script is in .cursor/skills/skill-creator/scripts/
    # We want .cursor/skills/<skill_name>
    base_dir = Path(__file__).resolve().parent.parent.parent
    target_dir = base_dir / skill_name
    
    if target_dir.exists():
        print(f"Error: Skill '{skill_name}' already exists at {target_dir}")
        sys.exit(1)

    # Create directories
    target_dir.mkdir(parents=True)
    (target_dir / "scripts").mkdir()

    # Create SKILL.md
    title = skill_name.replace("-", " ").title()
    skill_md = target_dir / "SKILL.md"
    skill_md.write_text(SKILL_TEMPLATE.format(title=title))

    # Create dummy script
    script_file = target_dir / "scripts" / "example.py"
    script_file.write_text("#!/usr/bin/env python3\nprint('Hello from " + skill_name + "')\n")
    
    # Make executable
    script_file.chmod(0o755)

    print(f"✅ Skill '{skill_name}' created successfully!")
    print(f"   Location: {target_dir}")
    print(f"   Action: Edit {skill_md} to define your skill.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: init_skill.py <skill-name>")
        sys.exit(1)
    
    init_skill(sys.argv[1])
