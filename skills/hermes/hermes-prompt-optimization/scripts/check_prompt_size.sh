#!/bin/bash
# check_prompt_size.sh — measure Hermes agent system prompt size and breakdown
# Usage: bash check_prompt_size.sh [--brief]

python3 << 'PYEOF'
import sys, os

hermes_dir = os.path.expanduser('~/.hermes/hermes-agent')
sys.path.insert(0, hermes_dir)

# CRITICAL: set platform so disabled skills are applied correctly
os.environ['HERMES_PLATFORM'] = 'cli'
os.environ.setdefault('HERMES_HOME', os.path.expanduser('~/.hermes'))
os.environ.setdefault('TERMINAL_ENV', 'local')

from agent.system_prompt import build_system_prompt_parts

class ProbeAgent:
    def __init__(self):
        self.model = 'deepseek-v4-flash'
        self.provider = 'deepseek'
        self.platform = 'cli'
        self.session_id = None
        self.pass_session_id = False
        self.valid_tool_names = {
            'memory', 'session_search', 'skill_manage',
            'skills_list', 'skill_view',
            'terminal', 'file', 'web', 'todo',
            'clarify', 'delegate_task',
        }
        self.skip_context_files = True
        self.load_soul_identity = True
        self._tool_use_enforcement = False
        self._task_completion_guidance = False
        self._parallel_tool_call_guidance = False
        self._environment_probe = False
        self._kanban_worker_guidance = None
        self._memory_store = None
        self._memory_enabled = False
        self._user_profile_enabled = False
        self._memory_manager = None
        self.context_compressor = None
        self._platform_hint_overrides = {}
    def _emit_status(self, msg):
        pass

agent = ProbeAgent()
parts = build_system_prompt_parts(agent)
full = "\n\n".join(p for p in (parts['stable'], parts['context'], parts['volatile']) if p)
brief = '--brief' in sys.argv

print("=" * 50)
print("  System Prompt Size Analysis")
print("=" * 50)
print(f"  stable  tier:   {len(parts['stable']):>7,} chars")
print(f"  context tier:   {len(parts['context']):>7,} chars")
print(f"  volatile tier:  {len(parts['volatile']):>7,} chars")
print(f"  {'─'*40}")
print(f"  TOTAL:          {len(full):>7,} chars  (~{len(full)//4:,} tokens)")
if brief:
    sys.exit(0)

print()
sections = parts['stable'].split('\n## ')
total = len(parts['stable'])
for s in sections:
    if not s.strip():
        continue
    lines = s.strip().split('\n')
    title = lines[0].strip('# ')
    size = len(s)
    pct = size / total * 100
    bar = '█' * int(pct / 3)
    print(f"  {bar:<33} {size:>5,} chars ({pct:4.1f}%)  {title[:50]}")

# Skills section detail
if 'available_skills>' in parts['stable']:
    inner = parts['stable'].split('available_skills>')[1].split('</')[0]
    skill_lines = [l.strip() for l in inner.split('\n') if l.strip().startswith('- ')]
    print(f"\n  Skills in index: {len(skill_lines)}")
    for l in skill_lines:
        print(f"    {l[:80]}")

print()
print("  Tip: /reset or new session for config changes to take effect.")
PYEOF
