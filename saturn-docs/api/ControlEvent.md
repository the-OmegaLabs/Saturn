# ControlEvent

控件回调收到的事件数据。

[← API 索引](./README.md)

源码：[`saturn/event.py`](../../saturn/event.py)（第 13 行）。

## 构造参数

```python
saturn.ControlEvent(name: 'str', control: "'Control'", data: 'Any' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `name` | `str` | `必填` | 对象、文件或资源的名称。 |
| `control` | `Control` | `必填` | 产生事件或关联数据的控件。 |
| `data` | `Any` | `None` | 附着在控件或事件上的自定义数据。 |
