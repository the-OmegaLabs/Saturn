# Window

原生窗口的尺寸、标题和状态。

[← API 索引](./README.md)

源码：[`saturn/page.py`](../../saturn/page.py)（第 46 行）。

## 构造

```python
ft.Window(app)
```

> 这些对象通常由 `ft.run()` 创建和传入，应用代码无需直接构造。

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `app` | `—` | `必填` |

## 本类属性

`full_screen`、`height`、`icon`、`maximized`、`minimized`、`title`、`width`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `close(self)` | — |
| `destroy(self)` | — |
| `center(self)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
