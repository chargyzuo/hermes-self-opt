"""hermes-self-opt — Agent Self-Optimization for Hermes."""

from pathlib import Path

# Skills 统一根目录（Hermes 的 ~/.hermes/skills 已弃用，改为软链接指向此处）
SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"
