# Border

Border settings for each of the four sides.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 289).

## Public methods

| Method | Description |
| --- | --- |
| `all(cls, width: 'float | None' = None, color=None)` | Creates the same setting for every side. |
| `symmetric(cls, vertical: 'BorderSide | None' = None, horizontal: 'BorderSide | None' = None)` | Sets symmetric horizontal and vertical values. |
| `only(cls, left: 'BorderSide | None' = None, top: 'BorderSide | None' = None, right: 'BorderSide | None' = None, bottom: 'BorderSide | None' = None)` | Sets values for specified sides individually. |

## Constructor parameters

```python
saturn.Border(left: 'BorderSide' = <factory>, top: 'BorderSide' = <factory>, right: 'BorderSide' = <factory>, bottom: 'BorderSide' = <factory>) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `left` | `BorderSide` | `<factory>` | Distance from the left edge of a Stack. |
| `top` | `BorderSide` | `<factory>` | Distance from the top edge of a Stack. |
| `right` | `BorderSide` | `<factory>` | Distance from the right edge of a Stack. |
| `bottom` | `BorderSide` | `<factory>` | Distance from the bottom edge of a Stack. |
