# FilePickerUploadFile

Upload destination and request method for a file.

[← API index](./README.md)

Source: [`saturn/services.py`](../../saturn/services.py) (line 29).

## Constructor parameters

```python
saturn.FilePickerUploadFile(upload_url: 'str', method: 'str' = 'PUT', id: 'int | None' = None, name: 'str | None' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `upload_url` | `str` | `required` | Destination URL for file uploads. |
| `method` | `str` | `'PUT'` | Name of the method that triggered the operation. |
| `id` | `int | None` | `None` | Identifier of the file or object. |
| `name` | `str | None` | `None` | Name of the object, file, or resource. |
