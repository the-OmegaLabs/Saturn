# Saturn 平台适配层

这里是 Saturn 与操作系统原生 API 之间的边界。核心 UI、窗口公开 API
和渲染器只调用 `PlatformAdapter`，不应直接导入 Win32、X11、Wayland、D-Bus
或平台动态库。

## 目录

| 文件 | 职责 |
| --- | --- |
| `base.py` | 跨平台接口、能力表和无操作默认实现 |
| `__init__.py` | 按运行时平台选择适配器并缓存实例 |
| `windows.py` | DPI、窗口矩形、标题栏、模态 owner、模块监控和 Win32 resize hook |
| `windows_native.py` | Win32 窗口样式、透明度、任务栏、拖拽、缩放和子类回调 |
| `windows_gl.py` | WGL GPU affinity/association 和跨上下文呈现 |
| `linux.py` | Linux 适配器占位，以及 `/proc` 模块快照 |
| `other.py` | macOS、BSD、无显示器测试环境的安全回退 |

## 使用方式

```python
from saturn.platform import get_platform

platform = get_platform()
if platform.supports("window_frame_metrics"):
    # 使用平台提供的原生窗口边框测量
    ...
```

功能要通过能力表查询，而不是在公共模块中判断 `sys.platform`。不支持的
功能应返回空结果、使用 SDL 回退，或抛出带有平台说明的
`NotImplementedError`；不能伪造原生成功。

## Linux 接入顺序

Linux 的第一阶段只需要普通顶层窗口：SDL 窗口、输入、Software/OpenGL
和基础 DPI/resize。之后再按显示协议拆成：

```text
saturn/platform/linux.py       通用 Linux 能力
saturn/platform/linux_x11.py   X11/EWMH/ICCCM
saturn/platform/linux_wayland.py  Wayland/XDG
```

面板、桌面背景和通知中心等 Shell 能力不应塞进普通窗口适配器，应在独立
的 services/shell 层使用 layer-shell、D-Bus 和 xdg-desktop-portal。

## 新增平台能力的规则

1. 在 `PlatformCapabilities` 增加能力标志，并在 `PlatformAdapter` 提供默认行为。
2. 在对应平台文件实现行为；不要把原生库导入放到核心模块的顶层。
3. 在 `Window`、`App` 或渲染器中只调用适配器方法。
4. 为不支持该能力的平台保留软件/SDL 回退和明确错误。
5. 至少运行 Software smoke test、`compileall` 和目标平台窗口生命周期测试。
