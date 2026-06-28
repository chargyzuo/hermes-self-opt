#!/usr/bin/env python3
"""
sync-memory-from-core.py
从 core/*.yaml 编译 pre-MEMORY.md 并同步到 Hermes MEMORY.md。

过滤规则: duplicate_count >= 5 或 duplicate_count == 0（人工静态 entry）才写入。
按 duplicate_count 降序排列，再按段落模板分组压缩。

用法:
  python3 sync-memory-from-core.py              # 生成 pre-MEMORY.md + 同步 MEMORY.md
  python3 sync-memory-from-core.py --dry-run    # 只生成 pre-MEMORY.md，不同步
  python3 sync-memory-from-core.py --check      # 仅检查是否需要更新（退出码 0=需更新, 1=不需）
  python3 sync-memory-from-core.py --verbose    # 打印过滤详情

由 self-opt-distill cron 或 core memory 变动时触发。
"""

import os
import re
import sys
import hashlib
import yaml
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
CORE_DIR = HERMES_HOME / "memories" / "core"
MEMORY_MD = HERMES_HOME / "memories" / "MEMORY.md"
PRE_MEMORY_MD = CORE_DIR / "pre-MEMORY.md"

CORE_FILES = ["facts.yaml", "preferences.yaml", "environment.yaml", "patterns.yaml"]

# 过滤阈值
MIN_DUPLICATE_COUNT = 5  # duplicate_count >= 此值才自动纳入
# duplicate_count == 0 始终纳入（人工静态 entry）

# 段落分组模板 — 按 topic 将相关 entries 合并为一个 § 段落
# 顺序很重要：越靠前的段落越优先保留（超过 2200 字符时从尾部截断）
PARAGRAPH_TEMPLATES = [
    # (段落标题, 匹配关键词列表)
    # 段落1: 排障规范
    ("排障", ["configure", "aaa online-fail-record", "Docker IP", "Arista", "Address Locking",
               "Leasequery", "Bluecat", "Cisco", "MAB Fallback", "dot1x超时", "交换机", "认证",
               "MAC", "802.1X", "switch_execute"]),
    # 段落2: 个人信息
    ("身份", ["班型", "飞书sheet", "Hermes v0.17", "CLI模式", "brew", "cron 268",
               "launchd", "网络运维工程师", "zuojiajie"]),
    # 段落3: Credentials
    ("安全", ["Credentials", "audit", "mask", "xxd", "subprocess", "code-security-audit",
               "parallel-agy", "密码"]),
    # 段落4: OPS 只读
    ("规则", ["READ-ONLY", "只读", "禁止写入", "数据来源", "静默使用缓存", "OPS"]),
    # 段落5: 网络工具
    ("工具", ["NetBox", "itelk", "ELK", "Kibana", "fortinet", "elk-query", "netbox"]),
    # 段落6: Provider
    ("模型", ["Volcano", "fangzhou", "Mira", "uid=", "api.qnaigc", "deepseek-v4",
               "Gemini", "Flash", "Claude", "auxiliary", "provider", "模型"]),
    # 段落7: 英语
    ("英语", ["English_learning", "edge-tts", "limit=30", "词汇"]),
    # 段落8: self-opt 管线
    ("管线", ["Phase1-4", "core Knowledge变更", "git commit", "已蒸馏文档", "token去重",
               "开发日记", "self-opt"]),
    # 段落9: 蒸馏
    ("蒸馏", ["蒸馏排障", "关键路径", "lark-doc-distill", "飞书→normal", "normal→core",
               "结构化 Markdown"]),
    # 段落10: 反馈层
    ("反馈", ["反馈层", "Gate-Lite", "Gate-Full", "target_type=skill", "target_type=knowledge",
               "correction"]),
    # 段落11: 全链路
    ("日志", ["全链路", "change.log", "logs/*.json", "eventlog", "实际产出文件",
               "benchmark"]),
    # 段落12: lark-cli + skills
    ("工具链", ["lark-cli", "self-opt/skills", "用户身份", "新增skill", "lark",
               "skill"]),
    # 段落13: Obsidian
    ("笔记", ["Obsidian", "Vault", "Mobile Documents", "已蒸馏"]),
]


def load_entries():
    """从 core/*.yaml 提取所有 entry（含 duplicate_count、content）"""
    entries = []
    for fname in CORE_FILES:
        fpath = CORE_DIR / fname
        if not fpath.exists():
            continue
        try:
            data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"WARNING: Failed to parse {fpath}: {e}", file=sys.stderr)
            continue
        if not data:
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            content = entry.get("content", "")
            if not content:
                continue
            dc = entry.get("duplicate_count", 0)
            # 规范化 dc：有些条目可能缺失或为 None
            try:
                dc = int(dc)
            except (TypeError, ValueError):
                dc = 0
            entries.append({
                "content": content.strip(),
                "duplicate_count": dc,
                "id": entry.get("id", ""),
                "source": fname,
            })
    return entries


def filter_entries(entries, verbose=False):
    """过滤：duplicate_count >= MIN_DUPLICATE_COUNT 或 duplicate_count == 0"""
    included = []
    excluded = []
    for e in entries:
        dc = e["duplicate_count"]
        if dc >= MIN_DUPLICATE_COUNT or dc == 0:
            included.append(e)
            if verbose:
                reason = "static" if dc == 0 else f"dc={dc}>={MIN_DUPLICATE_COUNT}"
                print(f"  + [{e['source']}] dc={dc} ({reason}) {e['id']}: {e['content'][:60]}...")
        else:
            excluded.append(e)

    # 按 duplicate_count 降序，static (dc=0) 排最前
    included.sort(key=lambda e: (-e["duplicate_count"] if e["duplicate_count"] > 0 else float("-inf"), e["content"]))

    if verbose:
        print(f"\nFilter: {len(included)} included, {len(excluded)} excluded "
              f"(dc>={MIN_DUPLICATE_COUNT} or dc==0)")

    return included


def group_entries(entries):
    """将 entries 按预定义模板分组，未匹配的归入「其他」"""
    groups = {i: [] for i in range(len(PARAGRAPH_TEMPLATES))}
    unmatched = []

    for entry in entries:
        content = entry["content"]
        matched = False
        for idx, (_, keywords) in enumerate(PARAGRAPH_TEMPLATES):
            if any(kw.lower() in content.lower() for kw in keywords):
                groups[idx].append(entry)
                matched = True
                break
        if not matched:
            unmatched.append(entry)

    return groups, unmatched


def compress_group(entries):
    """将一组 entries 压缩为一个段落"""
    if not entries:
        return ""
    seen = set()
    parts = []
    for e in entries:
        short = e["content"].split("。")[0].split("；")[0][:80]
        if short not in seen:
            seen.add(short)
            parts.append(short)
    return "。".join(parts[:4])  # 每组最多4句


def compile_memory_text(verbose=False):
    """编译 core YAML → MEMORY.md 格式文本（动态，基于 dc 过滤）"""
    entries = load_entries()
    filtered = filter_entries(entries, verbose=verbose)
    groups, unmatched = group_entries(filtered)

    paragraphs = []

    # 按模板顺序生成段落
    for idx, (title, _) in enumerate(PARAGRAPH_TEMPLATES):
        group_entries_list = groups.get(idx, [])
        if group_entries_list:
            text = compress_group(group_entries_list)
            if text:
                paragraphs.append(text)

    # 未匹配的放最后
    if unmatched:
        text = compress_group(unmatched)
        if text:
            paragraphs.append(text)

    return "\n§\n".join(paragraphs)


def get_core_hash():
    """计算 core/*.yaml 的联合哈希"""
    h = hashlib.sha256()
    for fname in sorted(CORE_FILES):
        fpath = CORE_DIR / fname
        if fpath.exists():
            h.update(fpath.read_bytes())
    return h.hexdigest()


def needs_update():
    """检查 core YAML 是否比 pre-MEMORY.md 新"""
    if not PRE_MEMORY_MD.exists():
        return True
    hash_file = CORE_DIR / ".memory_hash"
    current_hash = get_core_hash()
    if hash_file.exists():
        stored_hash = hash_file.read_text().strip()
        return current_hash != stored_hash
    return True


def sync(dry_run=False, verbose=False):
    """主同步逻辑"""
    text = compile_memory_text(verbose=verbose)
    char_count = len(text)
    limit = 2200

    if char_count > limit:
        print(f"WARNING: {char_count} chars exceeds {limit} limit, truncating...",
              file=sys.stderr)
        text = text[:limit]

    # 写 pre-MEMORY.md
    PRE_MEMORY_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {PRE_MEMORY_MD} ({len(text)} chars)")

    if not dry_run:
        # 同步到 Hermes MEMORY.md
        MEMORY_MD.write_text(text, encoding="utf-8")
        print(f"Synced to {MEMORY_MD}")

    # 保存哈希
    hash_file = CORE_DIR / ".memory_hash"
    hash_file.write_text(get_core_hash())


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if needs_update() else 1)
    elif "--dry-run" in sys.argv:
        sync(dry_run=True, verbose="--verbose" in sys.argv)
    elif "--verbose" in sys.argv:
        sync(verbose=True)
    else:
        sync()
