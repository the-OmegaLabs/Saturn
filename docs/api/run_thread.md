# run_thread

Like `run`, but the window runs on a daemon thread and this returns

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 718).

## Call parameters

```python
saturn.run_thread(main, *, backend: 'Renderer | None' = None, title: 'str' = 'saturn', gpu: 'str | int | None' = None)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `main` | `—` | `required` | Application entry point that receives a Page. |
| `backend` | `Renderer | None` | `None` | Rendering backend to use. For saturn.run(), omission selects OpenGL unless SATURN_BACKEND overrides it. |
| `title` | `str` | `'saturn'` | Title of a dialog, notification, or window. |
| `gpu` | `str | int | None` | `None` | Startup GPU name or nonnegative index; None keeps default selection. OpenGL selection requires driver support; see the renderer guide. |
