---
name: ap-yellow-led-troubleshoot
version: 1.0
description: 排查Aruba AP黄灯闪烁（Radio Status LED黄色闪烁）的标准化流程
inputs:
  - ap_name: 用户提供的AP名称（如CNPEK144-F02-AP11-640D）
  - ap_ip: 可选，AP管理IP
  - ap_mac: 可选，AP MAC地址
steps:
  - name: check_ap_status
    command: ssh wac 'show ap database | include {AP_NAME}'
    expected: status=Up 或 status=Down
  - name: check_led_panel
    note: 根据型号物理丝印标签确认LED类型（PWR=System, WiFi=Radio）。AP-555黄灯闪烁=Radio LED=一个射频在监控模式
  - name: check_log
    command: ssh wac 'show log all | include {AP_NAME} | include down'
    fallback: 使用Kibana KQL过滤："stm" AND "down" AND "{AP_NAME}"
  - name: locate_switch_port
    steps:
      - check_neighbor: ssh wac 'show ap debug lldp neighbors {AP_NAME}'
      - search_mac: ssh switch 'display mac-address | include {AP_MAC}'
      - fallback: 通过同交换机其他AP端口编号规律推断，结合PoE状态和掉线时间
  - name: check_switch_port
    commands:
      - ssh switch 'display interface {PORT}'
      - ssh switch 'display poe power-state interface {PORT}'
    decisions:
      - port_down_and_poe_ok: 物理链路故障，需现场验证网线/光模块
      - port_up: 检查AP软件配置或认证
      - poe_abnormal: 供电不足或PoE硬件故障
  - name: create_obsidian_note
    note: 将排查结果写入Obsidian Vault/Kibana日志过滤语法.md或Aruba AP 指示灯状态与故障排查.md
outputs:
  - 根因分析
  - 交换机IP和端口
  - 建议操作
