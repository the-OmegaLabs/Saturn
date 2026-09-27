# run

Starts a Saturn app and passes its Page to the entry point.

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 746).

## Call parameters

```python
saturn.run(main, *, backend: 'Renderer | None' = None, title: 'str' = 'saturn', gpu: 'str | int | None' = None)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `main` | `—` | `required` | Application entry point that receives a Page. |
| `backend` | `Renderer | None` | `None` | Rendering backend to use. For saturn.run(), omission selects OpenGL unless SATURN_BACKEND overrides it. |
| `title` | `str` | `'saturn'` | Application window title. |
| `gpu` | `str | int | None` | `None` | Startup GPU name or nonnegative index; None keeps default selection. OpenGL selection requires driver support; see the renderer guide. |
