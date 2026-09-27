# run

Starts a Saturn app and passes its Page to the entry point.

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 542).

## Call parameters

```python
saturn.run(main, *, backend: 'Renderer | None' = None, title: 'str' = 'saturn')
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `main` | `—` | `required` | Application entry point that receives a Page. |
| `backend` | `Renderer | None` | `None` | Rendering backend to use. For saturn.run(), omission selects OpenGL unless SATURN_BACKEND overrides it. |
| `title` | `str` | `'saturn'` | Application window title. |
