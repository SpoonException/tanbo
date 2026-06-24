#!/usr/bin/env python3
# encoding: utf-8
"""
Artisan Roast Simulator — 自动循环 + 新连接触发重置版

行为：
  1. 自动循环：每炉 12 分钟，烤完后冷却 5 秒自动开始下一炉
  2. 连接触发：如果空闲超过 10 秒后有新请求到达，立即重置开始新一炉
  3. 命令行控制：
     --no-loop     禁止自动循环，只响应连接触发
     --idle-reset N 空闲 N 秒后新连接触发重置（默认 10）
"""

import argparse
import asyncio
import math
import struct
import random
import time

from pymodbus.simulator import SimData, SimDevice, DataType
from pymodbus.server import ModbusTcpServer

FC_WRITE_MULTI_REGS = 16
FC_READ_HOLDING = 3

# ── 烘焙参数 ──────────────────────────────────────────────
CHARGE_ET    = 210.0
ROOM_BT      = 25.0
TURNING_T    = 55.0
FC_TEMP      = 198.0
DROP_TEMP    = 218.0
TOTAL_TIME   = 720   # 12 分钟
COOLDOWN     = 5     # 炉间冷却间隔（秒）

# 阶段时间
T_DROP       = 60
T_DRY        = 180
T_MAILLARD   = 300
T_PRE_FC     = 120
T_FC         = 30
T_DEV        = 30


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def float_to_registers(value: float) -> list[int]:
    data = struct.pack(">f", value)
    return [
        struct.unpack(">H", data[2:4])[0],
        struct.unpack(">H", data[0:2])[0],
    ]


class RoastModel:
    """真实烘焙模型"""

    def __init__(self, start_time: float | None = None):
        self.reset(start_time)

    def reset(self, start_time: float | None = None):
        self.start = start_time or time.time()
        self.batch = getattr(self, "batch", 0) + 1

    @property
    def elapsed(self) -> float:
        return time.time() - self.start

    def bt(self, t: float) -> float:
        if t <= 0:
            return ROOM_BT
        tp_time = 60
        if t <= tp_time:
            frac = t / tp_time
            return ROOM_BT + (TURNING_T - ROOM_BT) * (frac ** 0.35)
        fc_time = T_DROP + T_DRY + T_MAILLARD + T_PRE_FC
        if t <= fc_time:
            elapsed = t - tp_time
            total = fc_time - tp_time
            x = (elapsed / total) * 10 - 5
            sigmoid = 1 / (1 + math.exp(-x))
            return TURNING_T + (FC_TEMP - TURNING_T) * sigmoid
        elapsed_fc = t - fc_time
        if elapsed_fc <= T_FC:
            return FC_TEMP + 6 * (elapsed_fc / T_FC)
        elapsed_dev = elapsed_fc - T_FC
        frac = clamp(elapsed_dev / T_DEV, 0, 1)
        return FC_TEMP + 6 + (DROP_TEMP - FC_TEMP - 6) * (frac ** 0.7)

    def et(self, t: float) -> float:
        if t <= 0:
            return CHARGE_ET
        tp_time = 60
        if t <= tp_time:
            frac = t / tp_time
            et_min = CHARGE_ET - 55
            return et_min + (CHARGE_ET - et_min) * (frac ** 0.5)
        bt_now = self.bt(t)
        elapsed = t - tp_time
        total = TOTAL_TIME - tp_time
        gap = 0.5 + (1 - elapsed / total) * 28
        return bt_now + gap + random.uniform(-0.5, 0.5)

    def met(self, t: float) -> float:
        bt_now = self.bt(t)
        et_now = self.et(t)
        fc_time = T_DROP + T_DRY + T_MAILLARD + T_PRE_FC
        blend = 0.35 if t >= fc_time else 0.60
        return bt_now + (et_now - bt_now) * blend + random.uniform(-0.3, 0.3)

    def ror(self, t: float) -> float:
        bt_now = self.bt(t)
        bt_prev = self.bt(max(0, t - 1))
        return (bt_now - bt_prev) * 60

    def get_temperatures(self, t: float):
        return (
            round(self.et(t), 1),
            round(self.bt(t), 1),
            round(self.met(t), 1),
        )


class SessionManager:
    """管理烘焙会话：追踪客户端连接状态，协调烘焙循环"""

    def __init__(self, auto_loop: bool = True, idle_timeout: float = 10.0):
        self.auto_loop = auto_loop
        self.idle_timeout = idle_timeout
        self.last_request = time.time()
        self.should_reset = False

    def on_request(self):
        """当收到 Modbus 请求时调用"""
        now = time.time()
        idle = now - self.last_request
        self.last_request = now
        # 空闲超过阈值 → 标记需要重置
        if idle > self.idle_timeout:
            self.should_reset = True

    def is_idle(self) -> bool:
        return (time.time() - self.last_request) > self.idle_timeout

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_request


# ── SimDevice action 回调 ─────────────────────────────────
# 注意：action 会被绑定到 SessionManager 实例上调用

async def on_device_request(
    manager: SessionManager,
    _fc: int, _sa: int, _addr: int, _count: int,
    _regs: list[int], _set_vals: list[int] | list[bool] | None,
) -> None:
    manager.on_request()


async def update_loop(server: ModbusTcpServer, roast: RoastModel, mgr: SessionManager):
    count = 0
    device_id = 1

    while True:
        t = roast.elapsed

        # ── 规则 1：新连接触发重置 ──
        if mgr.should_reset:
            roast.reset()
            mgr.should_reset = False
            print(f"\n{'='*60}")
            print(f"  🔄 检测到新连接，开始第 {roast.batch} 炉")
            print(f"{'='*60}")
            t = 0.0

        # ── 规则 2：自动循环 ──
        if mgr.auto_loop and t >= TOTAL_TIME + COOLDOWN:
            roast.reset()
            print(f"\n{'='*60}")
            print(f"  🫘 第 {roast.batch - 1} 炉完成，自动开始第 {roast.batch} 炉")
            print(f"{'='*60}")
            t = 0.0

        # ── 更新寄存器 ──
        et, bt, met = roast.get_temperatures(t)
        ror = roast.ror(t)

        await server.async_setValues(device_id, FC_WRITE_MULTI_REGS, 10, float_to_registers(et))
        await server.async_setValues(device_id, FC_WRITE_MULTI_REGS, 12, float_to_registers(bt))
        await server.async_setValues(device_id, FC_WRITE_MULTI_REGS, 14, float_to_registers(met))

        # ── 终端输出 ──
        phase = get_phase(t)
        idle_str = f" 空闲={mgr.idle_seconds:.0f}s" if mgr.idle_seconds > 1 else ""
        if count % 5 == 0:
            print(
                f"[{t:5.0f}s] {phase:12s}  "
                f"ET={et:6.1f}  BT={bt:6.1f}  MET={met:6.1f}  "
                f"RoR={ror:5.1f}  #{roast.batch}{idle_str}"
            )

        count += 1
        await asyncio.sleep(1)


def get_phase(t: float) -> str:
    if t <= T_DROP:
        return "入料/回温  "
    elif t <= T_DROP + T_DRY:
        return "干燥阶段  "
    elif t <= T_DROP + T_DRY + T_MAILLARD:
        return "梅纳反应  "
    elif t <= T_DROP + T_DRY + T_MAILLARD + T_PRE_FC:
        return "一爆前  "
    elif t <= T_DROP + T_DRY + T_MAILLARD + T_PRE_FC + T_FC:
        return "◆ 一爆 ◆ "
    else:
        return "发展期  "


def parse_args():
    p = argparse.ArgumentParser(description="Artisan Roast Simulator")
    p.add_argument("--no-loop", action="store_true",
                   help="禁止自动循环，仅响应连接触发重置")
    p.add_argument("--idle-reset", type=float, default=10.0,
                   help="空闲 N 秒后新请求触发重置（默认 10）")
    p.add_argument("--port", type=int, default=5020,
                   help="监听端口（默认 5020）")
    p.add_argument("--host", default="0.0.0.0",
                   help="监听地址（默认 0.0.0.0）")
    return p.parse_args()


async def main():
    args = parse_args()

    roast = RoastModel()
    mgr = SessionManager(
        auto_loop=not args.no_loop,
        idle_timeout=args.idle_reset,
    )

    # 创建绑定到 mgr 实例的 action 回调
    import functools
    bound_action = functools.partial(on_device_request, mgr)

    device = SimDevice(
        1,
        simdata=[
            SimData(10, count=2, values=0, datatype=DataType.REGISTERS),
            SimData(12, count=2, values=0, datatype=DataType.REGISTERS),
            SimData(14, count=2, values=0, datatype=DataType.REGISTERS),
        ],
        action=bound_action,
    )

    server = ModbusTcpServer(device, address=(args.host, args.port))
    asyncio.create_task(update_loop(server, roast, mgr))

    print("=" * 65)
    print("  Artisan Roast Simulator — 循环版")
    print("=" * 65)
    print(f"  入料 ET  : {CHARGE_ET}°C      回温点 BT : ~{TURNING_T}°C")
    print(f"  一爆温度  : {FC_TEMP}°C         出炉温度  : {DROP_TEMP}°C")
    print(f"  总时间    : {TOTAL_TIME}s ({TOTAL_TIME/60:.0f} min)")
    print(f"  自动循环  : {'✓' if mgr.auto_loop else '✗'}")
    print(f"  连接重置  : 空闲 {args.idle_reset:.0f}s 后新请求触发")
    print(f"  Host      : {args.host}")
    print(f"  Port      : {args.port}       Slave ID  : 1")
    print(f"  Registers : 10-11 (ET), 12-13 (BT), 14-15 (MET)")
    print(f"  Format    : Float32 (Big-Endian, Word Swap)")
    print("=" * 65)
    print("  按 Ctrl+C 停止")
    print("  💡 每次连接 Artisan 会自动重置开始新一炉")
    print()

    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
