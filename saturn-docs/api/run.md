# run

启动 Saturn 应用并把 Page 交给入口函数。

[← API 索引](./README.md)

源码：[`saturn/app.py`](../../saturn/app.py)（第 480 行）。

## 调用

```python
ft.run(main, *, backend: 'Render | None' = None, width: 'int' = 800, height: 'int' = 600, title: 'str' = 'saturn', **_flet_ignored)
```

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `main` | `—` | `必填` |
| `backend` | `Render | None` | `None` |
| `width` | `int` | `800` |
| `height` | `int` | `600` |
| `title` | `str` | `'saturn'` |
| `_flet_ignored` | `—` | `额外关键字参数` |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
