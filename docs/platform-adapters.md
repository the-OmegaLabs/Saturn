# 平台适配层与 Win32 拆分

Saturn 目前以 Windows 为主要开发环境，但 Linux 改造需要先固定边界：控件、
布局、主题、事件和渲染接口保持平台无关；窗口系统、DPI、原生拖拽、任务栏、
模块监控和 GPU 绑定由平台适配器实现。

## 已完成的第一步

- `saturn/platform/base.py` 定义 `PlatformAdapter` 和
  `PlatformCapabilities`。
- `saturn/platform/windows.py` 集中 Windows DPI、窗口矩形、深色标题栏、
  modal owner、实时 resize watch 和模块枚举。
- `saturn/platform/windows_native.py` 集中 Win32 窗口样式、透明度、拖拽、
  resize、任务栏进度/徽章和 COM 资源。
- `saturn/platform/windows_gl.py` 集中 WGL GPU affinity/association。
- `saturn/platform/linux.py` 和 `saturn/platform/other.py` 提供可扩展的空适配器；
  Linux 已有 `/proc/self/maps` 模块快照。
- `saturn/_native_window.py` 保留为旧私有导入的兼容转发，不再承载实现。
- `App`、`Window`、`Page`、`Subpage`、`WindowDragArea`、颜色偏好和模块监控
  已通过适配器访问平台能力。

## 代码约束

公共核心代码不应直接出现 `ctypes.windll`、`ctypes.WinDLL`、`winreg`、
`WGL` 或 `sys.platform == "win32"`。平台判断只放在
`saturn/platform/__init__.py`；平台原生库只在对应适配器中延迟加载。

能力的正确调用方式是：

```python
platform = app.platform
if platform.supports("native_window_dragging"):
    await page.window.start_dragging()
```

Wayland 不允许模拟窗口定位、全局输入或 layer-shell 的能力。适配器应返回
明确的不支持状态，或让公开 API 抛出可理解的 `NotImplementedError`。

## 下一步 Linux 工作

1. 先验证 SDL Software/OpenGL 在 Ubuntu、Fedora 的 X11 和 Wayland 上创建、
   resize、输入、字体和多显示器窗口。
2. 在 `linux.py` 中实现通用能力，再按需要增加 `linux_x11.py` 与
   `linux_wayland.py`，不要把两套协议混进核心窗口类。
3. 把剪贴板、文件选择、通知、托盘和桌面入口放到 services 层，优先使用
   xdg-desktop-portal、D-Bus 和标准桌面协议。
4. 面板、启动器、设置中心和通知中心放到 shell 层；完整 compositor、锁屏、
   会话和权限边界保持独立进程。

完整的可行性评估、路线图、测试矩阵和桌面环境范围见
[Linux 桌面路线图](./linux-desktop-roadmap.md)。
