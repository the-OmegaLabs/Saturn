# Border

Border(left: 'BorderSide' = <factory>, top: 'BorderSide' = <factory>, right: 'BorderSide' = <factory>, bottom: 'BorderSide' = <factory>)

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 289 行）。

## 构造

```python
ft.Border(left: 'BorderSide' = <factory>, top: 'BorderSide' = <factory>, right: 'BorderSide' = <factory>, bottom: 'BorderSide' = <factory>) -> None
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `left` | `BorderSide` | `<factory>` |
| `top` | `BorderSide` | `<factory>` |
| `right` | `BorderSide` | `<factory>` |
| `bottom` | `BorderSide` | `<factory>` |

## 本类属性

`bottom`、`left`、`right`、`top`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `all(cls, width: 'float | None' = None, color=None)` | — |
| `symmetric(cls, vertical: 'BorderSide | None' = None, horizontal: 'BorderSide | None' = None)` | — |
| `only(cls, left: 'BorderSide | None' = None, top: 'BorderSide | None' = None, right: 'BorderSide | None' = None, bottom: 'BorderSide | None' = None)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
