"""Server-built primitives with stable control IDs and per-view geometry."""
import threading
from contextlib import contextmanager
from pathlib import Path
from .. import colors, text
from ..animation import animation_spec
from ..types import as_padding
from .context import current_view, current_session

_font_lock = threading.RLock()


@contextmanager
def render_context(page):
    # pygame measurement is retained initially; configuration is restored after
    # each synchronous layout pass. No lock is held across application awaits.
    with _font_lock:
        before = (dict(text.registered_fonts), dict(text._font_sources), text.default_family)
        fonts = {k: str(Path(v) if Path(v).is_file() else Path("assets")/v) for k, v in page.fonts.items()}
        switched = fonts != text.registered_fonts or page._theme_key[1] != text.default_family
        if switched:
            text.registered_fonts.clear()
            text.registered_fonts.update(fonts)
            text._font_sources.clear()
            text._font_sources.update(fonts)
            text.default_family = page._theme_key[1]
            text.invalidate_fonts()
        dark, _, seed, expressive = page._theme_key
        roles = dict(colors.EXPRESSIVE_LIGHT) if expressive and not dark else {}
        if seed is not None and colors.parse_color(seed)[:3] == (63, 81, 181):
            roles.update(colors.INDIGO_DARK if dark else colors.INDIGO_LIGHT)
        token = colors._render_colors.set((dark, roles))
        try:
            yield
        finally:
            colors._render_colors.reset(token)
            if switched:
                text.registered_fonts.clear()
                text.registered_fonts.update(before[0])
                text._font_sources.clear()
                text._font_sources.update(before[1])
                text.default_family = before[2]
                text.invalidate_fonts()


def css(value):
    r, g, b, a = colors.parse_color(value)
    return f"rgba({r},{g},{b},{a/255:.5f})"


def build_scene(session, view):
    import pygame
    from ..widgets import Text, Container, Row, Column, Stack, TextField, Checkbox, Switch, ListView, Image, Divider
    from ..widgets.shader import Shader
    from ..widgets.buttons import FilledButton
    ButtonBase = FilledButton.__mro__[1]
    from ..widgets.inputs import RadioGroup
    pygame.font.init()
    page = session.page
    origin, scope = current_view.set(view), current_session.set(session)
    page._apply_theme()
    nodes, order, fonts, font_labels = {}, [], {}, {}
    active = set()
    def font(family=None):
        family = family or page._theme_key[1]
        if family in font_labels:
            return font_labels[family]
        path = page.fonts.get(family)
        if path is None and family and Path(family).is_file():
            path = family
        if path is not None:
            if not Path(path).is_file():
                path = Path("assets")/path
            label = "font-"+session.runtime.resources.register(path)
            fonts[label] = session.runtime.resources.register(path)
            font_labels[family] = label
            return label
        fonts["SaturnDefault"] = session.runtime.resources.register(text.INTER)
        fonts["SaturnCJK"] = session.runtime.resources.register(text.NOTO_REGULAR)
        font_labels[family] = "SaturnDefault,SaturnCJK,sans-serif"
        return font_labels[family]
    def add(identifier, kind, bounds, **props):
        node = dict(id=identifier, kind=kind, bounds=list(bounds), **props)
        nodes[identifier] = node
        order.append(identifier)
    def walk(control, disabled=False, clips=(), offset=(0, 0), opacity=1, scrollers=(), animation=None):
        active.add(control)
        identifier = session.control_id(control)
        if not control.visible:
            return
        disabled = disabled or control.disabled
        x, y, w, h = control._rect
        x, y = x+offset[0], y+offset[1]
        bounds = (x, y, w, h)
        opacity *= object.__getattribute__(control, '__dict__').get('opacity', control.opacity)
        common = dict(control=identifier, disabled=disabled, opacity=opacity,
                      clips=[list(c) for c in clips], scrollers=list(scrollers))
        spec = animation_spec(control.animate_opacity)
        if spec:
            animation = dict(duration=spec[0]*1000, curve=getattr(spec[1], 'value', 'linear'))
        if animation:
            common['animation'] = animation
        if isinstance(control, Text):
            align = getattr(control.text_align, "value", control.text_align) or "start"
            add(identifier, "text", bounds, text=control.value, lines=list(control._lines),
                line_height=control._line_h, size=control.size,
                weight=text.weight_num(control.weight), italic=control.italic,
                font=font(control.font_family), color=css(control.color or "onsurface"), align=align, **common)
        elif isinstance(control, ButtonBase):
            _, _, _, _, size, weight, _, _ = control._metrics()
            add(identifier, "button", bounds, text=control._label(), size=size,
                weight=weight, font=font(), color=css(control._fg_raw()),
                background=css(control._bg() or "transparent"), radius=control._radius(h),
                border=css(control.variant_border) if control.variant_border else None,
                clickable=bool(control.on_click), **common)
            for child in control._children():
                walk(child, disabled, clips, offset, opacity, scrollers, animation)
        elif isinstance(control, TextField):
            add(identifier, "input", bounds, value=str(control.value), label=control.label,
                placeholder=control.hint_text or "", password=control.password,
                multiline=control.multiline, read_only=control.read_only,
                max_length=control.max_length, size=control.text_size or 16,
                font=font(getattr(control.text_style, "font_family", None)),
                color=css(control.color or "onsurface"),
                background=css(control.bgcolor or "surfacecontainerhighest"),
                border=css(control.border_color or "outline"), radius=control.border_radius or 12,
                input_revision=session.input_revisions.get(identifier, 0), **common)
        elif isinstance(control, (Checkbox, Switch)):
            add(identifier, "toggle", bounds, label=str(control.label or ""),
                value=bool(control.value), size=14, font=font(),
                color=css("onsurface"), background=css("primary"), **common)
        elif isinstance(control, ListView):
            add(identifier, "scroll", bounds, content_size=control._content_size,
                horizontal=control.horizontal, offset=control._offset, **common)
            start = (x if control.horizontal else y)+control._offset
            extent = w if control.horizontal else h
            candidates = control._candidates(start-512, start+extent+512)
            for child in candidates:
                child._place(*child._rect, 1)
                walk(child, disabled, (*clips, bounds), offset, opacity,
                     (*scrollers, [identifier, control.horizontal]), animation)
        elif isinstance(control, Container):
            radius = control.border_radius
            if radius is not None and not isinstance(radius, (int, float)):
                radius = getattr(radius, "top_left", 0)
            add(identifier, "rect", bounds, background=css(control.bgcolor or "transparent"),
                radius=radius or 0, clickable=bool(getattr(control, "on_click", None)), **common)
            for child in control._children():
                walk(child, disabled, clips, offset, opacity, scrollers, animation)
        elif isinstance(control, (Row, Column, Stack, RadioGroup)):
            for child in control._children():
                walk(child, disabled, clips, offset, opacity, scrollers, animation)
        elif isinstance(control, Divider):
            add(identifier, "rect", (x, y+h/2, w, control.thickness),
                background=css(control.color or "outlinevariant"), radius=0, **common)
        elif isinstance(control, Image):
            if not isinstance(control.src, str) or control.src.startswith(("http:", "https:", "data:")):
                raise NotImplementedError("Web Image currently requires a local file path")
            add(identifier, "image", bounds, resource=session.runtime.resources.register(control.src), **common)
        elif isinstance(control, Shader):
            add(identifier, "rect", bounds, background=css(control.fallback_color or control.color), radius=0, **common)
        else:
            raise NotImplementedError(f"{type(control).__name__} does not yet have a Web scene adapter")
    try:
        with render_context(page):
            def prepare(control):
                if control.on_size_change:
                    raise NotImplementedError("Web control size callbacks are not supported yet; use page.on_resize")
                active.add(control)
                identifier = session.control_id(control)
                if isinstance(control, ListView):
                    control._offset = view.scroll.get(identifier, 0)
                for child in control._children():
                    prepare(child)
            for control in [*page.controls, *page.overlay]:
                prepare(control)
            p = as_padding(page.padding)
            col = Column(*page.controls, alignment=page.vertical_alignment,
                         horizontal_alignment=page.horizontal_alignment, spacing=page.spacing)
            col._place(p.left, p.top, max(0, view.width-p.left-p.right),
                       max(0, view.height-p.top-p.bottom), 1)
            for control in page.controls:
                if page.visible:
                    walk(control, page.disabled, opacity=page.opacity)
            for control in page.overlay:
                walk(control, page.disabled)
            background = css(page.bgcolor or "surface")
        # Removed controls cannot remain valid event targets.
        for control in list(session.ids):
            if control not in active:
                session.controls.pop(session.ids.pop(control), None)
        return dict(nodes=nodes, order=order, fonts=fonts, background=background,
                    title=page.title, route=page.route, width=view.width, height=view.height,
                    focus=getattr(view, 'focus_id', None))
    finally:
        current_view.reset(origin)
        current_session.reset(scope)


def scene_patch(view, scene, session):
    previous = view.scene
    if scene == previous and not view.needs_snapshot:
        return None
    base = view.revision
    view.revision += 1
    if view.needs_snapshot or not previous:
        message = dict(type="snapshot", scene=scene)
        view.needs_snapshot = False
    else:
        old, new = previous['nodes'], scene['nodes']
        ops = [dict(op="remove", id=k) for k in old if k not in new]
        ops += [dict(op="create" if k not in old else "patch", node=v)
                for k, v in new.items() if old.get(k) != v]
        message = dict(type="patch", ops=ops, metadata={k:v for k,v in scene.items() if k != 'nodes'})
    view.scene = scene
    view.scene_revision = session.revision
    message.update(revision=view.revision, base_revision=base, state_revision=session.revision)
    return message
