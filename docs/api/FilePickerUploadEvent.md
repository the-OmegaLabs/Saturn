# FilePickerUploadEvent

File upload progress or error event.

[← API index](./README.md)

Source: [`saturn/services.py`](../../saturn/services.py) (line 49).

## Constructor parameters

```python
saturn.FilePickerUploadEvent(name: 'str', control: "'FilePicker'", file_name: 'str', progress: 'float | None' = None, error: 'str | None' = None, data: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `FilePicker` | `required` | Control that produced the event or holds the data. |
| `file_name` | `str` | `required` | Suggested name for a saved file. |
| `progress` | `float | None` | `None` | Completion progress of an upload or operation. |
| `error` | `str | None` | `None` | Error message when an operation fails. |
| `data` | `object` | `None` | Custom data attached to the control or event. |
