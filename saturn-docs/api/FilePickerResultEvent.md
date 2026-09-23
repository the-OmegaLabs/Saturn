# FilePickerResultEvent

Result event from a file selection or save operation.

[← API index](./README.md)

Source: [`saturn/services.py`](../../saturn/services.py) (line 37).

## Constructor parameters

```python
saturn.FilePickerResultEvent(name: 'str', control: "'FilePicker'", files: 'list[FilePickerFile]', data: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `FilePicker` | `required` | Control that produced the event or holds the data. |
| `files` | `list[FilePickerFile]` | `required` | Files selected, uploaded, or returned. |
| `data` | `object` | `None` | Custom data attached to the control or event. |
