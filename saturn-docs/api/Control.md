# Control

所有可视控件的基类，提供尺寸、状态和更新方法。

[← API 索引](./README.md)

源码：[`saturn/control.py`](../../saturn/control.py)（第 24 行）。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `update(self)` | 请求重绘本控件及其变化。 |
| `handle_event(self, e) -> 'bool'` | 处理传入的控件事件。 |

## 构造参数

```python
saturn.Control(*, visible: 'bool' = True, disabled: 'bool' = False, opacity: 'float' = 1.0, expand: 'bool | int | None' = None, tooltip: 'str | None' = None, data=None, width: 'float | None' = None, height: 'float | None' = None, margin=None, align: 'Alignment | None' = None, left: 'float | None' = None, top: 'float | None' = None, right: 'float | None' = None, bottom: 'float | None' = None, rotate=None, scale=None, offset=None, animate_opacity=None, animate_size=None, animate_position=None, animate_align=None, animate_margin=None, animate_rotation=None, animate_scale=None, animate_offset=None, on_animation_end=None, **_flet_ignored)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `visible` | `bool` | `True` | 为 False 时不显示控件。 |
| `disabled` | `bool` | `False` | 为 True 时禁用交互，并使用禁用状态外观。 |
| `opacity` | `float` | `1.0` | 控件透明度；0 为透明，1 为不透明。 |
| `expand` | `bool | int | None` | `None` | 占用父布局中的剩余空间；数字可作为伸缩比例。 |
| `tooltip` | `str | None` | `None` | 鼠标悬停时显示的简短提示。 |
| `data` | `—` | `None` | 附着在控件或事件上的自定义数据。 |
| `width` | `float | None` | `None` | 控件的指定宽度。 |
| `height` | `float | None` | `None` | 控件的指定高度。 |
| `margin` | `—` | `None` | 控件外侧的留白。 |
| `align` | `Alignment | None` | `None` | 控件在可用区域内的对齐位置。 |
| `left` | `float | None` | `None` | 相对 Stack 左边的定位距离。 |
| `top` | `float | None` | `None` | 相对 Stack 上边的定位距离。 |
| `right` | `float | None` | `None` | 相对 Stack 右边的定位距离。 |
| `bottom` | `float | None` | `None` | 相对 Stack 底边的定位距离。 |
| `rotate` | `—` | `None` | 绘制控件时使用的旋转值。 |
| `scale` | `—` | `None` | 绘制控件时使用的缩放值。 |
| `offset` | `—` | `None` | 在布局位置之外施加的位移。 |
| `animate_opacity` | `—` | `None` | opacity 属性变化时的动画配置。 |
| `animate_size` | `—` | `None` | size 属性变化时的动画配置。 |
| `animate_position` | `—` | `None` | position 属性变化时的动画配置。 |
| `animate_align` | `—` | `None` | align 属性变化时的动画配置。 |
| `animate_margin` | `—` | `None` | margin 属性变化时的动画配置。 |
| `animate_rotation` | `—` | `None` | rotation 属性变化时的动画配置。 |
| `animate_scale` | `—` | `None` | scale 属性变化时的动画配置。 |
| `animate_offset` | `—` | `None` | offset 属性变化时的动画配置。 |
| `on_animation_end` | `—` | `None` | 控件动画完成时调用的回调。 |
| `**_flet_ignored` | `—` | `额外关键字参数` | 为兼容 Flet 风格调用而接收的额外参数；当前不会自动产生功能。 |
