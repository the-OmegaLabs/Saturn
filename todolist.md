# Saturn 性能问题与修复清单

更新日期：2026-09-23。以下区分已修复、仍存在和需要先测量的问题。优化直接放在原有控件中，不新增 `VirtualStudentList`。

## 已修复

- [x] **默认入口选错渲染后端。** `main.py` 和 `saturn.run()` 默认入口现用 `Renderer.OPENGL`，矩形等图元在 GPU 上绘制并合批；显式 `Renderer.SOFTWARE`、`Renderer.VULKAN` 仍可选。
- [x] **不可见的列表项仍参与绘制和命中检测。** 原 `ListView` 只裁剪像素，仍遍历所有控件。现按可见范围加 96 逻辑像素预绘边界，用有序行坐标和二分缩小绘制、布局及命中候选集；原控件对象与事件接口保留。
- [x] **滚动、悬停引发整页布局。** `Page` 区分布局更新与仅重绘；动画只推进活跃控件。固定高度行与 `item_extent` 在原 `ListView` 中按需放置子树，resize 时复用纵向位置并只重新放置附近行。
- [x] **OpenGL 每个矩形新建缓冲并单独提交。** 连续矩形已按原绘制顺序合批，复用 VBO/VAO；纹理切换仍需保持透明叠加顺序。
- [x] **OpenGL 窗口 resize 后视口可能回到原生像素大小。** SDL 能在 ModernGL 缓存之外修改底层 GL 视口，2 倍离屏绘制会缩进左下角。每帧清屏前重新绑定离屏目标并设置实际视口；新增模拟外部 `glViewport` 的回归测试。
- [x] **控件隐藏或输入光标移动后留下闪烁残影。** OpenGL 把完成的离屏帧贴回窗口时仍开启透明混合；半透明像素与窗口上一帧叠加，使旧位置逐帧淡出。最终贴图现关闭混合、覆盖整个窗口，再恢复绘制状态。双帧像素复现中，旧光标位置由残留值 `(78, 78, 78)` 变为与背景完全相同的 `(39, 39, 39)`；`tests/input_checks.py` 包含移动光标、隐藏控件的像素回归。
- [x] **输入文字与光标垂直错位。** 截图里的 Consolas 14 正文和空值提示都比光标的视觉中心高约 2 像素。`TextField` 现按字体、字号和缩放测量固定参考字形的可见高度，缓存稳定的基线补偿；正文、提示、选区和组合输入下划线一起对齐，光标与 IME 候选锚点保持原位。误加的水平间距已全部撤回。隐藏 OpenGL 像素回归覆盖 Consolas 14 和默认字体的空值提示及有值文字。
- [x] **静态位图每帧重新取像素并哈希。** 不变的文字、图标、图片按 Surface 身份缓存纹理，缓存有数量上限；图标栅格结果复用，OpenGL 直接缩放图片。
- [x] **文字重复测量和换行。** 文本测量、最近使用的宽度及字体来源已缓存；修改文本、宽度或字体时仍会重新计算。
- [x] **普通悬停层分配 CPU 位图。** OpenGL 对统一圆角、无按压波纹的悬停状态直接绘制半透明 GPU 矩形。非统一圆角和软件后端仍使用原精确遮罩路径。
- [x] **按压波纹分配 CPU 位图。** OpenGL 新增一个按绘制顺序提交的着色器图元，同时计算四角遮罩和动态波纹；不会为波纹创建 Surface、哈希或上传纹理。软件后端仍使用原路径。200×100 截图的波纹区域与软件路径平均像素差约 1.03/255，最大 16/255；三后端波纹压力测试通过。单个波纹场景的总帧时间提升不明显，主要收益是去掉动态位图路径。
- [x] **可变高度项被逐一放置和重复测量。** 原 `ListView` 现在只放置视口附近的子树；保留最近三种宽度的完整精确行坐标。内置 `Container` 的自然内容宽度若已装得下，就跨新宽度复用其高度；需要换行的行继续按实际宽度测量。内容更新会清空缓存。连续改变宽度的 5,000 行测试 p95 从约 159 ms 降到约 14 ms。
- [x] **Vulkan 原本在 CPU 画整帧，再上传显示。** 现用 SPIR-V 着色器、Vulkan render pass 和 GPU 顶点批处理绘制矩形、线条、圆形、纹理与裁剪区域；同纹理及裁剪的相邻图元合批，按需从 GPU 读回截图。文字及少数复杂效果仍先生成小纹理再上传，但不再 CPU 栅格化整帧。`tests/vulkan_checks.py` 强制旧软件绘制和整帧上传路径报错，真实窗口绘制及背景/矩形/纹理像素测试通过。
- [x] **Vulkan 快速跳转首次出现的文字会逐张分配 GPU 图片。** 后端内加有界的 1024² 小纹理图集、1 像素透明边与同帧区域上传；只缓存不可变文字/图标，不改列表结构。5,000 行全表跳转 60 帧压测 p95 从约 **26.51 ms** 降至 **6.68 ms**，常规绘制和波纹回归仍通过。
- [x] **Vulkan 斜线、弧线和控件边缘缺少抗锯齿。** 后端按设备/格式能力选 4×、2× 或 1× 采样，用多采样颜色附件 resolve 到交换链，并把圆角 SDF 羽化调整到接近 OpenGL。此机实际 4×：同一斜线的混合边缘像素从 1× 的 0 增到 133，弧线从 0 增到 236；圆角与文字边缘的混合像素数也接近 OpenGL。`tests/vulkan_checks.py` 新增斜线、弧线像素回归。
- [x] **SVG 与大 PNG 缩小时的图片边缘锯齿。** Vulkan 几何 MSAA 不会自动过滤纹理内部。`Image` 现在按目标设备像素尺寸栅格化 SVG，并把大 PNG 一次性平滑缩小后缓存，再由 GPU 合成；避免 410×304 demo 标志直接通过单级双线性采样压到约 52×40。`tests/image_antialias_checks.py` 核验目标尺寸、实际 SVG 像素和缓存复用；`.static/shots/demo-vulkan.png` 是修复后实际 Vulkan 截图。
- [x] **2 倍离屏帧缓冲成本已测量。** 5,000 行 OpenGL 的 1 倍和 2 倍 GPU 查询 p50 分别约 3.31 / 3.33 ms，没有稳定的速度收益；2 倍仍是默认值，以保留文字和圆角质量。
- [x] **列表布局被重复属性读取拖慢。** profile 中单次新宽度 `_place` 有 11 万余次 `Control.__getattribute__` 调用。只在 `ListView` 行循环中一次读取必要的原始属性和动画覆盖值，保留动画语义；不改变全局属性访问方式。
- [x] **重复 attach。** 已移除重复的子树挂接，相关事件和动画回归通过。

## 尚未完成／按需处理

- [ ] **可变高度长列表首次布局仍需测量全部行。** 5,000 行首次内在尺寸测量在本机约 320–360 ms；连续新宽度 resize 已降到约 14 ms p95。完全未知的换行高度不能凭空猜测，否则滚动位置会错误。数据规模特别大且行高已知时，请给原 `ListView` 的子项固定 `height` 或提供 `item_extent`。
- [ ] **极大阴影或越界变换可能超出 96 像素预绘范围。** 做视觉回归；若真实控件需要，局部扩大边界。
- [ ] **其他动态位图仍走 CPU 与纹理上传。** 复杂图标、阴影和动态图片等路径需按实际热点逐项处理；静态位图和 Material 波纹已经覆盖。
- [ ] **仅支持 1× 采样的 Vulkan 设备上，纯三角形斜线与弧线仍可能有阶梯边缘。** 设备能力不足时自动回退以保证可运行；圆角 SDF 边缘仍有着色器羽化。

## 压测证据与运行方式

`tests/performance_stress.py` 实际创建窗口、真实渲染器及 5,000 行控件；能重放滚动、悬停、全表跳转、波纹与 resize。默认隐藏窗口；`--visible` 可短暂显示真实窗口，`--gpu-time` 收集 OpenGL GPU 查询。结果仍随驱动和机器状态变化。

```powershell
.venv\Scripts\python.exe tests\performance_stress.py --backend all --rows 5000 --frames 60
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --full-sweep --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --ripple --gpu-time
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --resize-every 2 --visible
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --variable-height --resize-sweep
.venv\Scripts\python.exe tests\performance_stress.py --backend vulkan --rows 5000 --frames 60 --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend vulkan --rows 5000 --frames 60 --full-sweep
.venv\Scripts\python.exe tests\vulkan_checks.py
.venv\Scripts\python.exe tests\image_antialias_checks.py
```

本机 800×600、5,000 行、60 帧连续滚动：OpenGL 绘制加呈现 p50 **2.83 ms**、p95 **3.14 ms**；软件 p50 **3.93 ms**，旧 CPU Vulkan p50 **4.87 ms**，约 20/5,000 行进入绘制。resize 每两帧切换 800×600 与 760×570：优化前 OpenGL p50 **9.20 ms**、p95 **18.59 ms**，优化后复测 p50 **1.21 ms**、p95 **2.07 ms**，另有窗口/帧缓冲设置约 2–4 ms。2026-09-23 悬停 GPU 图元优化后同场景再次运行，绘制加呈现 p50 **1.67 ms**、p95 **2.55 ms**；由于机器和缓存波动，这组数值不能单独归因于悬停优化。跨全表跳转并 resize 的 p50 **4.42 ms**、p95 **7.24 ms**。

新增可见窗口 resize 回放：绘制加呈现 p50 **1.47 ms**、p95 **2.40 ms**，窗口/帧缓冲设置 p95 **6.03 ms**。波纹压力测试支持三后端；OpenGL GPU 波纹的绘制加呈现 p95 **3.15 ms**，同场景强制旧 CPU 波纹 p95 **3.18 ms**，差别在本机单个波纹下不明显。

Vulkan GPU 改造前的 5,000 行、60 帧复测：固定行高的 OpenGL 绘制加呈现 p95 **3.41 ms**，软件 **3.97 ms**，旧 CPU Vulkan **7.76 ms**，每帧约 20 行进入绘制。可变行高在两个宽度间切换的 OpenGL p95 **3.48 ms**，窗口设置 p95 **4.18 ms**；81 个宽度的连续拖动模拟 p95 **14.14 ms**，窗口设置 p95 **2.42 ms**。

Vulkan GPU 改造后的 5,000 行、60 帧本机复测：绘制加呈现 p50 **3.07 ms**、p95 **3.58 ms**，其中呈现 p50 **1.10 ms**；每两帧 resize 时绘制加呈现 p95 **4.81 ms**，交换链重建设置 p95 **11.61 ms**。默认 OpenGL 在相同 resize 压测中绘制加呈现 p95 **1.89 ms**，帧缓冲设置 p95 **4.26 ms**。这些是本机隐藏窗口的时钟时间，不能作为所有显卡和窗口管理器的上限。

开启 Vulkan 4× MSAA 后同机复测：常规滚动 p50 **3.04 ms**、p95 **5.80 ms**（少数帧有 GPU 调度尾峰）；每两帧 resize 的绘制加呈现 p95 **3.69 ms**、交换链设置 p95 **12.81 ms**；波纹 p95 **3.15 ms**、全表跳转 p95 **7.55 ms**。抗锯齿带来额外 GPU 采样和窗口 resize 附件成本。

最终三后端顺序运行的 5,000 行、60 帧常规滚动复测：软件、OpenGL、Vulkan 的绘制加呈现 p95 分别为 **5.48 / 3.29 / 3.19 ms**；每帧约 20 行实际绘制。与上一轮 Vulkan p95 的差异说明尾峰受 GPU 调度和机器状态影响，不能保证每次相同。

全表快速跳转场景首次遍历大量不同文字，Vulkan 小纹理图集加入前 p95 **26.51 ms**，加入后 p95 **6.68 ms**；OpenGL 同场景 p95 **3.87 ms**。这是比常规连续滚动更严苛的纹理冷启动场景。

## 其他请求的进度

- [x] `saturn-docs` 内容迁入 `docs`；`docs/expressive.md` 有用，保留并更新。
- [x] `references` 已清理；README、NOTICE 和随包 Apache 2.0 许可证保留来源与授权说明。
- [x] `saturn.Compose` 与 [迁移及 Flet 核验说明](docs/compose.md) 已添加；Flet 1.0.1 实包核验覆盖 68 个同名类签名、29 种默认控件构造和 4 条行为路径。Flet 全量行为兼容不是 Saturn 当前实现范围，差距已列明。
- [x] 公开后端枚举按用户命名为 `saturn.Renderer`，保留 `saturn.Render` 兼容别名。
- [x] 截图、logo 与文档控件图片已移到 `.static`，引用已更新；无用的本地一次性脚本已清理。
- [x] `gen/MaterialSymbolsOutlined.codepoints` 仍是 `gen_enums.py` 的输入，因此保留。仍被引用的测试、工具及生成器保留。
