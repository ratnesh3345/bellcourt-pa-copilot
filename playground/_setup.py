"""Lets the playground scripts import the project (config.py, copilot/...)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def title(text: str):
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)
