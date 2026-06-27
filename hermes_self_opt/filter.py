"""
filter.py — 预过滤：在调用 LLM 之前，判断一个 session 是否值得 Mine。

节约 token 消耗：普通对话 session（非排障）直接跳过，不调 LLM。
"""

from __future__ import annotations

# 排障关键词——纯正向匹配，不用非排障词反向排除
TROUBLESHOOTING_KEYWORDS = [
    # 故障现象
    "故障", "报错", "error", "失败", "超时", "timeout",
    "不通", "掉线", "离线", "down", "offline", "disconnect",
    "丢包", "延迟", "slow", "unreachable",
    "拒绝", "denied", "reject",
    # 排查动作
    "排查", "检查", "查看", "确认", "验证",
    "登录", "ssh", "telnet", "ping", "traceroute",
    "debug", "troubleshoot", "diagnose",
    # 设备/网络
    "交换机", "switch", "路由器", "router", "AP", "WAC",
    "端口", "port", "VLAN", "DHCP", "ARP", "MAC",
    "PoE", "SFP", "光模块", "配置",
    # 认证
    "认证", "dot1x", "MAB", "RADIUS", "802.1x",
    # 排障工具  
    "Wireshark", "抓包", "pcap", "日志", "log",
    "Kibana", "NetBox", "SSH",
    "display inter", "show ap",
    # 用户求助
    "怎么解决", "为什么", "帮我看", "帮我查", "帮我",
]


def looks_like_troubleshooting(dialog: str) -> bool:
    """纯正向匹配：命中 ≥3 个排障关键词就通过。不反向排除。"""
    if len(dialog) < 300:
        return False
    lower = dialog.lower()
    return sum(1 for kw in TROUBLESHOOTING_KEYWORDS if kw.lower() in lower) >= 3
