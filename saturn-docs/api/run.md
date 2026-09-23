# run

Starts a Saturn app and passes its Page to the entry point.

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 480).

## Call parameters

```python
saturn.run(main, *, backend: 'Render | None' = None, width: 'int' = 800, height: 'int' = 600, title: 'str' = 'saturn', **_flet_ignored)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `main` | `—` | `required` | Application entry point that receives a Page. |
| `backend` | `Render | None` | `None` | Rendering backend to use. |
| `width` | `int` | `800` | Initial application window width in pixels. |
| `height` | `int` | `600` | Initial application window height in pixels. |
| `title` | `str` | `'saturn'` | Application window title. |
| `**_flet_ignored` | `—` | `additional keyword arguments` | Extra arguments accepted for Flet compatibility without automatic behavior. |
