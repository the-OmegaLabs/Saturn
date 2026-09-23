# Border

分别定义四个方向的边框。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 289 行）。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `all(cls, width: 'float | None' = None, color=None)` | 用同一个值创建各方向一致的配置。 |
| `symmetric(cls, vertical: 'BorderSide | None' = None, horizontal: 'BorderSide | None' = None)` | 分别为水平和垂直方向设置对称值。 |
| `only(cls, left: 'BorderSide | None' = None, top: 'BorderSide | None' = None, right: 'BorderSide | None' = None, bottom: 'BorderSide | None' = None)` | 分别设置指定方向的值。 |

## 构造参数

```python
saturn.Border(left: 'BorderSide' = <factory>, top: 'BorderSide' = <factory>, right: 'BorderSide' = <factory>, bottom: 'BorderSide' = <factory>) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `left` | `BorderSide` | `<factory>` | 相对 Stack 左边的定位距离。 |
| `top` | `BorderSide` | `<factory>` | 相对 Stack 上边的定位距离。 |
| `right` | `BorderSide` | `<factory>` | 相对 Stack 右边的定位距离。 |
| `bottom` | `BorderSide` | `<factory>` | 相对 Stack 底边的定位距离。 |
