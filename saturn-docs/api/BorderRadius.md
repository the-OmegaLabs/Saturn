# BorderRadius

分别定义四个角的圆角半径。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 246 行）。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `all(cls, radius: 'float')` | 用同一个值创建各方向一致的配置。 |
| `horizontal(cls, left: 'float' = 0.0, right: 'float' = 0.0)` | 设置水平方向的两个值。 |
| `vertical(cls, top: 'float' = 0.0, bottom: 'float' = 0.0)` | 设置垂直方向的两个值。 |
| `only(cls, top_left: 'float' = 0.0, top_right: 'float' = 0.0, bottom_right: 'float' = 0.0, bottom_left: 'float' = 0.0)` | 分别设置指定方向的值。 |

## 构造参数

```python
saturn.BorderRadius(top_left: 'float' = 0.0, top_right: 'float' = 0.0, bottom_right: 'float' = 0.0, bottom_left: 'float' = 0.0) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `top_left` | `float` | `0.0` | 左上角的圆角大小。 |
| `top_right` | `float` | `0.0` | 右上角的圆角大小。 |
| `bottom_right` | `float` | `0.0` | 右下角的圆角大小。 |
| `bottom_left` | `float` | `0.0` | 左下角的圆角大小。 |
