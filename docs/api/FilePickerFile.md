# FilePickerFile

Information about one file returned by the file picker.

[← API index](./README.md)

Source: [`saturn/services.py`](../../saturn/services.py) (line 20).

## Constructor parameters

```python
saturn.FilePickerFile(id: 'int', name: 'str', size: 'int', path: 'str | None' = None, bytes: 'bytes | None' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `id` | `int` | `required` | Identifier of the file or object. |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `size` | `int` | `required` | Size of the text, icon, or control. |
| `path` | `str | None` | `None` | Local file or directory path. |
| `bytes` | `bytes | None` | `None` | Byte content of the file or resource. |
