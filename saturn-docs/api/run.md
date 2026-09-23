# run

启动 Saturn 应用并把 Page 交给入口函数。

[← API 索引](./README.md)

源码：[`saturn/app.py`](../../saturn/app.py)（第 480 行）。

## 调用参数

```python
saturn.run(main, *, backend: 'Render | None' = None, width: 'int' = 800, height: 'int' = 600, title: 'str' = 'saturn', **_flet_ignored)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `main` | `—` | `必填` | 应用入口函数，接收 Page 对象。 |
| `backend` | `Render | None` | `None` | 绘制后端的选择。 |
| `width` | `int` | `800` | 应用窗口的初始宽度，单位为像素。 |
| `height` | `int` | `600` | 应用窗口的初始高度，单位为像素。 |
| `title` | `str` | `'saturn'` | 应用窗口标题。 |
| `**_flet_ignored` | `—` | `额外关键字参数` | 为兼容 Flet 风格调用而接收的额外参数；当前不会自动产生功能。 |
