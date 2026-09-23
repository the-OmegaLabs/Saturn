# Padding

Padding(left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0)

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 217 行）。

## 构造

```python
ft.Padding(left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0) -> None
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `left` | `float` | `0.0` |
| `top` | `float` | `0.0` |
| `right` | `float` | `0.0` |
| `bottom` | `float` | `0.0` |

## 本类属性

`bottom`、`left`、`right`、`top`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `all(cls, value: 'float')` | — |
| `symmetric(cls, vertical: 'float' = 0.0, horizontal: 'float' = 0.0)` | — |
| `only(cls, left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0)` | — |
| `zero(cls)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
