# Margin

定义控件外侧四个方向的留白。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 242 行）。

**基类：** [Padding](./Padding.md)

## 构造参数

```python
saturn.Margin(left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `left` | `float` | `0.0` | 相对 Stack 左边的定位距离。 |
| `top` | `float` | `0.0` | 相对 Stack 上边的定位距离。 |
| `right` | `float` | `0.0` | 相对 Stack 右边的定位距离。 |
| `bottom` | `float` | `0.0` | 相对 Stack 底边的定位距离。 |
