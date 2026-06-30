#!/usr/bin/env python3
"""Show Core Memory stats after self-opt pipeline."""
import sys
from pathlib import Path

SELF_OPT_ROOT = Path(__file__).resolve().parent.parent
if str(SELF_OPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SELF_OPT_ROOT))

from hermes_self_opt.core_memory import stats, load_all
s = stats()
print(f"Core Memory ({sum(s.values())} 条):")
for cat, count in s.items():
    print(f"  {cat}: {count} 条")
