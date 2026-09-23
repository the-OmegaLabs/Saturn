# Compose Material 3 / Expressive 绘制对照

本次依据官方 `androidx.compose.material3:material3:1.5.0-alpha28` 源码。
源码包、校验值和许可证见 `references/androidx-compose-material3/`。
[官方发布记录](https://developer.android.com/jetpack/androidx/releases/compose-material3)说明 Expressive 的演进在 1.5 分支中。

## 已实现的对齐

- `MaterialExpressiveTheme`：对应 `ColorScheme.kt` 的 `expressiveLightColorScheme()`，浅色主题的四个 on-container 角色改为 tone 30；深色沿用 `darkColorScheme()` 基线。自定义 seed 配色保留原行为。
- `Card`：依据 `Card.kt` 和三种 Card tokens，统一 12dp 圆角；filled 使用 surfaceContainerHighest，outlined 使用 surface 和 1dp outlineVariant，elevated 使用 surfaceContainerLow 并绘制阴影。
- 按钮禁用态：依据 `FilledButtonTokens.kt` 等，容器为 onSurface 的 10%，文字为 onSurfaceVariant 的 38%；描边保留。文字透明度在 blit 时处理，因为 pygame 字体渲染会忽略颜色中的 alpha。
- `ExpressiveButton`：依据 `Button.kt`，支持 xsmall/small/medium/large/xlarge，分别为 32/40/56/96/136dp；图标为 20/20/24/32/40dp；按下圆角为 8/8/12/16/16dp。使用源码实际覆盖后的 XS padding 12、间距 4，而非生成 token 中的旧值。现有按钮也可传 `expressive=True` 或 `size=`。
- `ToggleButton` 及 elevated/tonal/outlined 变体：依据 `ToggleButton.kt`，有未选、选中、按下三种形状；选中状态支持事件与程序更新。
- `SplitButton`：依据 `SplitButton.kt`，小号 40dp 高、2dp 间距、外角 full、内角 4dp、按下内角 12dp；两段独立命中和事件。
- `ButtonGroup`：依据 `ButtonGroup.kt`，标准间距 12dp，按下项扩大 15%，相邻项等量缩小；动画中的绘制和命中使用同一布局。
- `FloatingActionButton` 家族：依据 `FloatingActionButton.kt`，小/标准/中/大尺寸 40/56/80/96dp，圆角 12/16/20/28dp；支持扩展文字形式。大号图标采用源码覆盖值 36dp。
- `ListItem`：依据 `ListItem.kt` 和 `ListItemDefaults.kt`，支持一/二/三行 56/72/88dp 最小高度、前后内容、选中配色及状态圆角。
- `Slider`：依据 `Slider.kt`，16dp 轨道、4×44dp 滑块（按下宽 2dp）、6dp 间隙、4dp 停止点和刻度。
- `ProgressBar` / `ProgressRing`：依据 `ProgressIndicator.kt`，轨道色为 secondaryContainer，活动色为 primary；确定态有轨道间隙，线性末端停止点，圆形使用同宽轨道和圆端帽。

## 用法

```python
import saturn as ft

def main(page):
    page.theme = ft.MaterialExpressiveTheme()
    page.add(
        ft.ExpressiveButton("Create", icon=ft.Icons.ADD, size="medium"),
        ft.ToggleButton("Selected", checked=True),
        ft.SplitButton("Run", on_click=lambda e: print("run"),
                       on_trailing_click=lambda e: print("options")),
        ft.ExtendedFloatingActionButton("Save", icon=ft.Icons.ADD),
        ft.ListItem("Title", supporting="Supporting text", selected=True),
    )

ft.run(main)
```

## 当前精度边界

这不是完整的 Compose 运行时移植。Saturn 保持 Python/Flet 风格 API。
阴影、状态层和形状动画仍使用现有渲染器及定时插值，尚未逐像素复现 Android 的阴影、圆角 ripple 裁剪和弹簧动画。
默认字体仍为项目选定的 Inter，因此文字宽度不保证与 Android Roboto 相同。
ButtonGroup 的 `connected=True` 当前设置连接式间距，未实现非对称连接角和溢出菜单。
LoadingIndicator 的七形态 RoundedPolygon morph、WavyProgressIndicator、FloatingToolbar、FAB Menu 等仍未引入。
本次没有扩展通用 HCT 动态配色；已有 `color_scheme_seed` 仍只带靛蓝参考配色。
