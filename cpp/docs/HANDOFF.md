# Saturn C++ 交接（2026-10-09）

**main tip:** `39cf80c`（#42 合入后）  
**仓库:** https://github.com/the-OmegaLabs/Saturn · 代码在 `cpp/`  
**黄金截图:** `.static/shots/demo-opengl-win-944x761.png`（Windows true-GL，drawable **944×761**）

---

## 目标纠偏（用户拍板）

**不要**再以「全部像素拟合 / 刷 `compare_shots` 分数」为主目标。

**要做的是还原 Python 侧：**

1. **动画** — 过渡、elevation 动效、按压缩放等行为合同  
2. **逻辑** — 控件状态机、事件、焦点、对话框/菜单栈、滚动与输入  
3. **排版引擎** — Row/Column/expand/align、测量与 dirty 布局、clip，与 Python 布局语义对齐  

`compare_shots` 只作回归嗅探，**不是** KPI。禁止为刷分加 Spacer / 魔改布局。

---

## 现状一句话

SDL3 + OpenGL 的 Control 树已能跑 `saturn_demo`；多数 inventory 控件有静态皮；**TextField / ListView 仍未实现**（解冻刀开写时被叫停）。相对黄金约 **avg_abs 7.63 / tol=2 差 27.6%**，大头是缺 TextField/ListView 造成的布局错位，不是「再抠几个圆角」能吃掉的。

---

## 已落地（C++）

| 域 | 内容 |
|----|------|
| 窗口/尺寸 | `demo_size.hpp`：logical client vs pixel drawable；`SATURN_DEMO_CONTRACT` / 显式 flag；无 `width()`/`height()` 别名糊弄 |
| 渲染 | 批 `fill_rects`、纹理 quad、SDF 圆角 fill/描边、`stroke_arc`（ProgressRing）、`TextureImage` |
| 字体 | 捆绑 Inter + stb_truetype；atlas 测量/绘制 |
| 布局 | Row/Column、`CrossAxisAlignment`、`set_expand`、Container、圆角 hit-test、clip 深度 |
| 控件 | Text、ColorBox、Elevated/Filled/Outlined/IconButton（Pressable/ButtonBase）、Image（`border_radius`）、Checkbox、Slider、Switch、ProgressRing、Dropdown（闭合态）、AlertDialog、SnackBar、TextButton |
| 阴影 | Elevated：`painting.draw_shadow` ambient/key 近似（同心半透明圆角 fill）；`py_round` 银行家舍入；**无** FBO/真高斯 |
| 安全文化 | `limits.hpp` 超限 **抛**、不静默截断；缺 GL uniform / pipeline 失败抛 |

### 关键 caps（节选）

见 `cpp/include/saturn/limits.hpp`：`kMaxTextBytes`、`kMaxEventQueue=4096`、`kMaxClipDepth=64`、`kMaxListItems=4096`、`kMaxScrollBackBytes=4MiB`、`kMaxDialogDepth/Actions=8`、`kMaxSnackBarQueue=8`、`kMaxSnackBarDurationMs=60000`、`kMaxDropdownOptions=256`、`kMaxSliderDivisions=1024`、`kMaxImageDecodeDim=4096` 等。

解冻 TextField/ListView 时审查者已拍：内容走 `kMaxTextBytes`；输入排队走 `kMaxEventQueue`；ListView 不许无界 tile/cache；布局尺寸以 inventory 为准，勿估。

---

## 未做 / 债

| 项 | 说明 |
|----|------|
| **TextField / ListView** | 仍冻；demo 里 TBD。inventory：`cpp/docs/demo-inventory.md`（TextField h56/pad16/r4/text16；ListView 400×260、spacing4、30 项、item pad8/r6） |
| Dropdown **overlay** | 菜单弹出层；闭合黄金几乎不动 headline；要做为**交互正确** |
| Elevated 阴影保真 | 合同路径对了，仍是 fill 近似 ≠ silhouette 高斯；勿为 Δ0.01 拧色阶 |
| Dialog 长文 | 单行 measure/draw，多行是像素/排版债 |
| 动画系统 | 基本未迁；新目标下应优先摸清 Python 动画 API 再在 C++ 建等价物 |
| HiDPI / 多 scale | 未认真做 |

近期已合 PR（节选）：#33 Dialog/SnackBar → #34 队列分账 → #35–36 Image 圆角 → #37–38 ProgressRing 真弧 → #39–42 Elevated 阴影路径纠正。

---

## 实机跑 demo（Windows，已验证）

```powershell
cd C:\Users\bzym2\src\Saturn
git fetch origin; git checkout main; git pull origin main
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
& $cmake -S cpp -B cpp/build "-DCMAKE_PREFIX_PATH=C:\Users\bzym2\src\SDL3-devel\SDL3-3.4.18"
& $cmake --build cpp/build --config Release --target saturn_demo -- /m
cd cpp\build\Release
.\saturn_demo.exe
```

截图对照：设 `SATURN_SHOT` + `SATURN_SHOT_FRAMES=5`，工具 `cpp/tools/compare_shots.py`。Mesa/Linux 截图 **不是** 黄金。桌面 push 用过 `HTTPS_PROXY=http://127.0.0.1:7897` + `gh`。

对照报告：本地跑 `cpp/tools/compare_shots.py` 产出即可，勿依赖 agent 机器路径。

---

## 文档索引

- `cpp/docs/AGENTS.md` — agent 约束  
- `cpp/docs/DESIGN.md` — 设计  
- `cpp/docs/DEMO.md` — demo / 截图合同  
- `cpp/docs/demo-inventory.md` — 与 `examples/demo.py` 的控件清单  
- `cpp/docs/ANIMATION-CONTRACT.md` — Python 动画/时钟合同（骨架）  

---

## 建议后续（按新目标排序）

1. **按 `ANIMATION-CONTRACT.md` 填满动画/时钟/implicit 合同**（骨架已落，缺项补齐后再动刀）。  
2. **排版/测量语义对齐**（含 Text 换行），再谈 TextField。  
3. **TextField / ListView** — 按已拍 cap + inventory，为逻辑与布局服务，不为刷分。  
4. **Dropdown overlay / 焦点 / 对话框栈** — 交互正确性。  
5. 动画与 elevation 过渡接到同一时钟。  
6. `compare_shots` 降级为「大回归别炸」检查。

---

## 协作备忘

- 群：Saturn（Coding / Coding 2 / 锐评者 / 审查者）  
- 审查：cap 先钉、超限抛；锐评：毒辣挑刺、禁刷分  
- Coding 偏好：先计划再改（用户侧）；本次用户明确 **停手**，解冻刀已取消，未合入。

*停手原因：用户要求停止像素拟合路线，改为还原 Python 动画 + 逻辑 + 排版引擎，并留下本交接。*
