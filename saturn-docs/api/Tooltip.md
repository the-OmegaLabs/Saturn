# Tooltip

配置控件悬停或长按时显示的提示内容。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 364 行）。

## 构造参数

```python
saturn.Tooltip(message: 'str', decoration: 'object' = None, enable_feedback: 'bool | None' = None, vertical_offset: 'float | None' = None, margin: 'object' = None, padding: 'object' = None, bgcolor: 'object' = None, text_style: 'TextStyle | None' = None, text_align: 'TextAlign | None' = None, prefer_below: 'bool | None' = None, show_duration: 'object' = None, wait_duration: 'object' = None, exit_duration: 'object' = None, tap_to_dismiss: 'bool' = True, exclude_from_semantics: 'bool | None' = False, trigger_mode: 'TooltipTriggerMode | None' = None, mouse_cursor: 'object' = None, size_constraints: 'object' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `message` | `str` | `必填` | 事件或结果的文字消息。 |
| `decoration` | `object` | `None` | 文本装饰或边框装饰设置。 |
| `enable_feedback` | `bool | None` | `None` | 交互时是否提供反馈效果。 |
| `vertical_offset` | `float | None` | `None` | 垂直方向额外偏移的距离。 |
| `margin` | `object` | `None` | 控件外侧的留白。 |
| `padding` | `object` | `None` | 控件内容四周的内边距。 |
| `bgcolor` | `object` | `None` | 控件或容器的背景颜色。 |
| `text_style` | `TextStyle | None` | `None` | 输入或显示文字的样式。 |
| `text_align` | `TextAlign | None` | `None` | 文本在可用宽度内的对齐方式。 |
| `prefer_below` | `bool | None` | `None` | 空间允许时优先把提示显示在控件下方。 |
| `show_duration` | `object` | `None` | 显示过渡所需时间。 |
| `wait_duration` | `object` | `None` | 进入下一次显示前的等待时间。 |
| `exit_duration` | `object` | `None` | 消失过渡所需时间。 |
| `tap_to_dismiss` | `bool` | `True` | 点击提示区域时是否关闭提示。 |
| `exclude_from_semantics` | `bool | None` | `False` | 是否从辅助功能语义树中排除。 |
| `trigger_mode` | `TooltipTriggerMode | None` | `None` | 触发提示出现的交互方式。 |
| `mouse_cursor` | `object` | `None` | 悬停时显示的鼠标指针样式。 |
| `size_constraints` | `object` | `None` | 尺寸允许的最小值与最大值范围。 |
