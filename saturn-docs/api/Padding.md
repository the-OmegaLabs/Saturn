# Padding

定义控件内侧四个方向的留白。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 217 行）。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `all(cls, value: 'float')` | 用同一个值创建各方向一致的配置。 |
| `symmetric(cls, vertical: 'float' = 0.0, horizontal: 'float' = 0.0)` | 分别为水平和垂直方向设置对称值。 |
| `only(cls, left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0)` | 分别设置指定方向的值。 |
| `zero(cls)` | 创建四个方向均为零的配置。 |

## 构造参数

```python
saturn.Padding(left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `left` | `float` | `0.0` | 相对 Stack 左边的定位距离。 |
| `top` | `float` | `0.0` | 相对 Stack 上边的定位距离。 |
| `right` | `float` | `0.0` | 相对 Stack 右边的定位距离。 |
| `bottom` | `float` | `0.0` | 相对 Stack 底边的定位距离。 |
