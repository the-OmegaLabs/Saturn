# Python → C++ 动画合同（骨架）

目标：还原行为，不是刷像素。填满本表再动刀。来源：`saturn/animation.py`、`saturn/motion.py`、`saturn/types.py`（`Animation` / `Duration` / `AnimationCurve`）、控件 `_animate_internal`。

## 时钟与入口

| 项 | Python 合同 | C++ 现状 | 备注 |
|----|-------------|----------|------|
| 帧时钟 | Page / app 驱动；动画用墙钟 `now`（ms） | 待填 | 同一时钟喂 elevation / ripple / dialog |
| `animation_spec` | `bool` / ms / `Animation` / `None` → `(seconds, curve)` | 未迁 | 见 `animation.animation_spec` |
| `ease(curve, t)` | 含 Material 私有名（`materialStandard*` 等） | 未迁 | 曲线表必须对齐 `animation.ease` |
| `interpolate` | 标量 / 颜色 / Offset 等按名插值 | 未迁 | |

## Material 时长（ms，`motion.py`）

| Token | ms |
|-------|---:|
| SHORT1–4 | 50 / 100 / 150 / 200 |
| MEDIUM1–4 | 250 / 300 / 350 / 400 |
| LONG1–2 | 450 / 500 |

## Demo 相关控件动效（先盘这些）

| 控件 | 属性 | 时长 | 曲线 | 触发 |
|------|------|------|------|------|
| ElevatedButton | `_elevation_progress` | SHORT3 (150) | EMPHASIZED | hover / press / release |
| ElevatedButton | `_shape_progress` | SHORT2 (100) | （style） | press / release |
| Button ripple | ink | SHORT4 press / SHORT2 fade | — | press / release |
| Switch / Checkbox / Slider | 待从源码补 | | | |
| Dialog / SnackBar / Dropdown overlay | 待补 | | | |

Idle demo 截图路径用 elevation=1；**交互实机**才需要 hover→3 / press→1 等过渡。

## 排版（与动画并列的合同入口）

| 项 | Python | C++ |
|----|--------|-----|
| Row/Column expand / cross-axis | 已有语义 | 部分落地 |
| Text 测量 / 换行 | 待合同化 | 单行债 |
| clip 栈 | `clip_push/pop` | 有深度 cap |

控件尺寸以 `cpp/docs/demo-inventory.md` 为准，禁止 Spacer 刷分。

## 填表规则

1. 只写可验证行为（触发 → 时长 → 曲线 → 起止值）。  
2. 超限走 `limits.hpp` 抛，不静默。  
3. `compare_shots` 仅回归嗅探，不进 KPI。
