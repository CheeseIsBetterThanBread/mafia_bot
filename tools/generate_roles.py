from pathlib import Path
from collections import Counter
import subprocess

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "config" / "roles.yaml"
CONFIG_DIR = BASE_DIR / "config"

ROLES_FILE = CONFIG_DIR / "roles.py"
ROLE_ACTIONS_FILE = CONFIG_DIR / "role_actions.py"


def load_roles():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data["roles"]


def validate_roles(roles):
    names = [role["name"] for role in roles]

    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate role names found: {duplicates}")


def generate_roles_py(roles):
    role_lines = []
    for role in roles:
        role_lines.append(f'"{role["name"]}": "{role["description"]}",')

    mafia_lines = []
    for role in roles:
        if role.get("is_mafia", False):
            mafia_lines.append(f'"{role["name"]}",')

    content = f"ROLE_DESCRIPTIONS = {{{chr(10).join(role_lines)}}}\n\n"
    content += f"MAFIA_TEAM = [{chr(10).join(mafia_lines)}]"

    ROLES_FILE.write_text(content, encoding="utf-8")


def generate_role_actions_py(roles):
    all_actions = set()
    action_texts = {}
    role_action_lines = []

    for role in roles:
        role_name = role["name"]
        actions = role.get("night_actions", [])

        role_action_entries = []

        for action_data in actions:
            action_name = action_data["action"]
            if "text" in action_data:
                action_texts[action_name] = action_data["text"]

            if action_name not in action_texts:
                raise ValueError(
                    f"Action '{action_name}' " f"is missing text on first occurrence"
                )

            action_text = action_texts[action_name]
            all_actions.add(action_name)
            role_action_entries.append(
                f'(NightAction.{action_name.upper()},"{action_text}",)'
            )

        if role_action_entries:
            actions_block = ",".join(role_action_entries)
            role_action_lines.append(f'"{role_name}": [{actions_block}],')

    enum_lines = []
    for action in sorted(all_actions):
        enum_lines.append(f'    {action.upper()} = "{action}"')

    content = "from enum import Enum\n"
    content += f"class NightAction(str, Enum):\n{chr(10).join(enum_lines)}\n"
    content += f"ROLE_NIGHT_ACTIONS = {{{chr(10).join(role_action_lines)}}}"

    ROLE_ACTIONS_FILE.write_text(content, encoding="utf-8")


def main():
    roles = load_roles()
    validate_roles(roles)

    generate_roles_py(roles)
    generate_role_actions_py(roles)

    subprocess.run(["black", str(CONFIG_DIR)], check=True)

    print("Roles generated successfully")


if __name__ == "__main__":
    main()
