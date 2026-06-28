# 交换机诊断命令速查

## 关键原则：先识别设备类型

**永远不要假设设备厂商。** 第一条命令必须是识别设备类型：
- 华为：`dis version`
- Cisco：`show version`
- Arista：`show version`

主机名通常包含型号线索：`C9200` = Cisco Catalyst 9200, `CE68` = Huawei CE6800, `DCS` = Arista。

## Cisco IOS-XE

### 电源
```
show environment power       # 电源模块状态（最关键）
show environment all         # 温度+风扇+电源全貌
show inventory | include PWR # 电源模块硬件详情
show power inline            # PoE 供电状态
```

### 告警/日志
```
show logging | include FAULTY|SIGNAL|FRU_PS   # 搜索电源相关告警
show logging last 200                          # 最近日志全貌
show logging | include last 24                 # 最近24小时（部分版本支持）
```

### 系统
```
show version                  # 软件版本+uptime
show module                   # 堆叠成员状态
show platform software status control-processor brief  # 控制平面健康
```

## Huawei VRP

### 电源
```
dis power                          # 电源模块状态
dis device                         # 设备组件（含电源）
dis environment                    # 温度+风扇+电源
display device power system        # 部分型号
```

### 告警/日志
```
dis alarm all                      # 当前告警
dis alarm active                   # 活跃告警
dis logbuffer | include Power|power   # 日志搜索
dis trapbuffer                     # 告警缓冲区
```

### 系统
```
dis version                        # 软件版本+uptime
dis device                         # 板卡/电源/风扇状态
dis health                         # 健康检查
```

## Arista EOS

### 电源
```
show environment power             # 电源模块状态
show environment all               # 温度+风扇+电源全貌
show platform power                # 部分型号
```

### 告警/日志
```
show logging | grep -i power|fault   # 日志搜索
show logging last 30 minutes         # 最近日志
```

### 系统
```
show version                        # 软件版本+uptime
show module                         # 模块状态
```
