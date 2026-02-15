#!/usr/bin/env python3
"""
Keyword Manager for YouTube News Notifier
Add, remove, and list monitoring keywords.

Conceived by Romuald Czlonkowski - www.aiadvisors.pl/en
"""

import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def list_keywords():
    config = load_config()
    keywords = config.get("keywords", [])
    if not keywords:
        print("No keywords configured.")
        return
    print(f"Monitoring {len(keywords)} keyword(s):\n")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")


def add_keyword(keyword):
    config = load_config()
    if keyword in config["keywords"]:
        print(f"'{keyword}' is already in the list.")
        return
    config["keywords"].append(keyword)
    save_config(config)
    print(f"Added '{keyword}'. Now monitoring {len(config['keywords'])} keyword(s).")


def remove_keyword(keyword):
    config = load_config()
    if keyword not in config["keywords"]:
        print(f"'{keyword}' not found in the list.")
        return
    config["keywords"].remove(keyword)
    save_config(config)
    print(f"Removed '{keyword}'. Now monitoring {len(config['keywords'])} keyword(s).")


def show_help():
    print("""YouTube News Notifier - Keyword Manager

Usage:
  python manage.py list                  List all keywords
  python manage.py add <keyword>         Add a keyword
  python manage.py add "ai news"         Add a multi-word keyword
  python manage.py remove <keyword>      Remove a keyword
  python manage.py help                  Show this help

Examples:
  python manage.py add openai
  python manage.py add "artificial intelligence"
  python manage.py remove claude
  python manage.py list
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "list":
        list_keywords()
    elif command == "add":
        if len(sys.argv) < 3:
            print("Error: specify a keyword. Example: python manage.py add openai")
            sys.exit(1)
        add_keyword(" ".join(sys.argv[2:]))
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Error: specify a keyword. Example: python manage.py remove openai")
            sys.exit(1)
        remove_keyword(" ".join(sys.argv[2:]))
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
