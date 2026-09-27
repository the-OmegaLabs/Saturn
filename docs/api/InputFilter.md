# InputFilter

InputFilter(allow: 'bool' = True, regex_string: 'str' = '', replacement_string: 'str' = '')

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 519).

## Constructor parameters

```python
saturn.InputFilter(allow: 'bool' = True, regex_string: 'str' = '', replacement_string: 'str' = '') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `allow` | `bool` | `True` | Accept matching text when True; reject it when False. |
| `regex_string` | `str` | `''` | Pattern matching text to accept or reject. |
| `replacement_string` | `str` | `''` | Replacement for rejected filter matches. |
