# Tooltip

Flet-compatible tooltip value used by every Control.tooltip.

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 364 行）。

## 构造

```python
ft.Tooltip(message: 'str', decoration: 'object' = None, enable_feedback: 'bool | None' = None, vertical_offset: 'float | None' = None, margin: 'object' = None, padding: 'object' = None, bgcolor: 'object' = None, text_style: 'TextStyle | None' = None, text_align: 'TextAlign | None' = None, prefer_below: 'bool | None' = None, show_duration: 'object' = None, wait_duration: 'object' = None, exit_duration: 'object' = None, tap_to_dismiss: 'bool' = True, exclude_from_semantics: 'bool | None' = False, trigger_mode: 'TooltipTriggerMode | None' = None, mouse_cursor: 'object' = None, size_constraints: 'object' = None) -> None
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `message` | `str` | `必填` |
| `decoration` | `object` | `None` |
| `enable_feedback` | `bool | None` | `None` |
| `vertical_offset` | `float | None` | `None` |
| `margin` | `object` | `None` |
| `padding` | `object` | `None` |
| `bgcolor` | `object` | `None` |
| `text_style` | `TextStyle | None` | `None` |
| `text_align` | `TextAlign | None` | `None` |
| `prefer_below` | `bool | None` | `None` |
| `show_duration` | `object` | `None` |
| `wait_duration` | `object` | `None` |
| `exit_duration` | `object` | `None` |
| `tap_to_dismiss` | `bool` | `True` |
| `exclude_from_semantics` | `bool | None` | `False` |
| `trigger_mode` | `TooltipTriggerMode | None` | `None` |
| `mouse_cursor` | `object` | `None` |
| `size_constraints` | `object` | `None` |

## 本类属性

`bgcolor`、`decoration`、`enable_feedback`、`exclude_from_semantics`、`exit_duration`、`margin`、`message`、`mouse_cursor`、`padding`、`prefer_below`、`show_duration`、`size_constraints`、`tap_to_dismiss`、`text_align`、`text_style`、`trigger_mode`、`vertical_offset`、`wait_duration`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
