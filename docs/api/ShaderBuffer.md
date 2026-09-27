# ShaderBuffer

One additive instanced GPU pass sampled by a Shader's final fragment; see the Shader guide.

[← API index](./README.md)

Source: [`saturn/widgets/shader.py`](../../saturn/widgets/shader.py) (line 25).

## Constructor parameters

```python
saturn.ShaderBuffer(vertex_shader: 'str | Path', fragment_shader: 'str | Path', instances: 'int' = 1) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `vertex_shader` | `str | Path` | `required` | GLSL vertex source string or pathlib.Path; defines void main() and portable SATURN vertex/instance identifiers. |
| `fragment_shader` | `str | Path` | `required` | GLSL fragment source string or pathlib.Path; defines void main() and returns premultiplied RGBA. |
| `instances` | `int` | `1` | Number of six-vertex instances, from 1 to 1,000,000. |
