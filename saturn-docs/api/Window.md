# Window

原生窗口的尺寸、标题和状态。

[← API 索引](./README.md)

源码：[`saturn/page.py`](../../saturn/page.py)（第 46 行）。

> 这些对象通常由 `saturn.run()` 创建和传入，应用代码无需直接构造。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `close(self)` | 关闭窗口或展开的菜单。 |
| `destroy(self)` | 销毁原生窗口并释放资源。 |
| `center(self)` | 创建位于中心位置的对齐值。 |

## 构造参数

```python
saturn.Window(app)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `app` | `—` | `必填` | 当前应用实例，由运行时传入。 |
