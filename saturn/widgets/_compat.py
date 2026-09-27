"""Small value adapters shared by the native controls."""
from ..types import as_border_radius


def value(item):
    return getattr(item, "value", item)


def reject_options(owner, **options):
    for name, item in options.items():
        if item is not None:
            raise NotImplementedError(f"{owner}.{name} is not supported by Saturn")


def state_value(control, item):
    if not isinstance(item, dict):
        return item
    states = [("disabled", control.disabled),
              ("pressed", getattr(control, "_pressed", False)),
              ("hovered", getattr(control, "_hovered", False)),
              ("focused", getattr(control, "_focused", False)),
              ("selected", getattr(control, "selected", False)), ("", True)]
    normalized = {value(key): val for key, val in item.items()}
    for name, enabled in states:
        if enabled and name in normalized:
            return normalized[name]
    return normalized.get("default")


def style_value(control, name, fallback=None):
    style = getattr(control, "style", None)
    item = state_value(control, getattr(style, name, None)) if style else None
    return fallback if item is None else item


def shape_radius(shape, width, height, fallback=0):
    if shape is None:
        return fallback
    kind = getattr(shape, "_type", type(shape).__name__)
    if kind in ("stadium", "StadiumBorder", "circle", "CircleBorder"):
        return min(width, height) / 2
    if kind in ("roundedRectangle", "RoundedRectangleBorder"):
        radii = as_border_radius(shape.radius)
        corners = (radii.top_left,radii.top_right,radii.bottom_right,radii.bottom_left)
        if len(set(corners)) != 1:
            raise NotImplementedError("different corner radii are not supported for button shapes")
        return corners[0]
    raise NotImplementedError(f"shape {kind!r} is not supported by Saturn")


def constrain(width, height, constraints):
    if constraints is None:
        return width, height
    return (max(constraints.min_width or 0, min(width, constraints.max_width or float("inf"))),
            max(constraints.min_height or 0, min(height, constraints.max_height or float("inf"))))


def axis_distribution(alignment, free, count, spacing):
    """Return the leading free space and gap for a flex or wrap run."""
    kind = value(alignment)
    if kind == "end":
        return free, spacing
    if kind == "center":
        return free / 2, spacing
    if kind == "spaceBetween" and count > 1:
        return 0, spacing + free / (count - 1)
    if kind == "spaceAround" and count:
        extra = free / count
        return extra / 2, spacing + extra
    if kind == "spaceEvenly" and count:
        extra = free / (count + 1)
        return extra, spacing + extra
    return 0, spacing
