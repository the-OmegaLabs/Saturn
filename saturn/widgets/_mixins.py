"""Reusable widget mixins and base classes.

Eliminates code duplication across button, input, and interactive widgets
by extracting common state management, animation, and rendering logic.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..control import Control

# Material state layer constants
_STATE_LAYER_OPACITY = {
    "hover": 0.08,
    "focus": 0.12,
    "press": 0.12,
    "drag": 0.16,
}

_RIPPLE_DURATION = 0.3  # seconds


class StatefulMixin:
    """Mixin for widgets with hover/focus/press states.
    
    Eliminates duplication across Button, Checkbox, Switch, etc.
    Provides standardized state tracking and state layer animations.
    """
    
    def __init__(self):
        # State flags
        self._hovered = False
        self._focused = False
        self._pressed = False
        self._disabled = False
        
        # State layer animation
        self._state_layer_opacity = 0.0
        self._target_layer_opacity = 0.0
        self._state_layer_transition_start = 0.0
        self._state_layer_transition_duration = 0.15
        
        # Ripple animation (press feedback)
        self._ripple_active = False
        self._ripple_progress = 0.0
        self._ripple_start_time = 0.0
        self._ripple_x = 0.0
        self._ripple_y = 0.0
    
    def _set_hover(self, hovered: bool) -> None:
        """Update hover state and trigger animations."""
        if self._hovered == hovered:
            return
        
        self._hovered = hovered
        self._update_state_layer_target()
        
        # Trigger repaint
        if hasattr(self, 'repaint'):
            self.repaint()
    
    def _set_focused(self, focused: bool) -> None:
        """Update focus state and trigger animations."""
        if self._focused == focused:
            return
        
        self._focused = focused
        self._update_state_layer_target()
        
        if hasattr(self, 'repaint'):
            self.repaint()
    
    def _pressed_hook(self, x: float, y: float) -> None:
        """Called when widget is pressed (pointer down).
        
        Starts ripple animation at the press location.
        """
        self._pressed = True
        self._ripple_active = True
        self._ripple_progress = 0.0
        self._ripple_start_time = time.perf_counter()
        self._ripple_x = x
        self._ripple_y = y
        self._update_state_layer_target()
    
    def _released_hook(self, x: float, y: float) -> None:
        """Called when widget is released (pointer up)."""
        self._pressed = False
        self._update_state_layer_target()
    
    def _update_state_layer_target(self) -> None:
        """Calculate target state layer opacity based on current state."""
        if self._disabled:
            target = 0.0
        elif self._pressed:
            target = _STATE_LAYER_OPACITY["press"]
        elif self._focused:
            target = _STATE_LAYER_OPACITY["focus"]
        elif self._hovered:
            target = _STATE_LAYER_OPACITY["hover"]
        else:
            target = 0.0
        
        if target != self._target_layer_opacity:
            self._target_layer_opacity = target
            self._state_layer_transition_start = time.perf_counter()
    
    def _tick_state_layer(self, now: float) -> bool:
        """Update state layer animation. Returns True if still animating."""
        animating = False
        
        # Animate state layer opacity
        if abs(self._state_layer_opacity - self._target_layer_opacity) > 0.001:
            elapsed = now - self._state_layer_transition_start
            progress = min(1.0, elapsed / self._state_layer_transition_duration)
            
            # Ease in-out
            t = progress * progress * (3.0 - 2.0 * progress)
            
            self._state_layer_opacity = (
                self._state_layer_opacity * (1 - t) +
                self._target_layer_opacity * t
            )
            animating = True
        else:
            self._state_layer_opacity = self._target_layer_opacity
        
        # Animate ripple
        if self._ripple_active:
            elapsed = now - self._ripple_start_time
            self._ripple_progress = min(1.0, elapsed / _RIPPLE_DURATION)
            
            if self._ripple_progress >= 1.0:
                self._ripple_active = False
            
            animating = True
        
        return animating
    
    def _get_state_layer_color(self, base_color: str) -> tuple[int, int, int, int]:
        """Get state layer color with current opacity.
        
        Args:
            base_color: Base color (usually on_surface or on_primary)
        
        Returns:
            RGBA tuple
        """
        from ..colors import parse_color
        r, g, b, _ = parse_color(base_color)
        alpha = int(self._state_layer_opacity * 255)
        return (r, g, b, alpha)
    
    def _should_show_ripple(self) -> bool:
        """Check if ripple should be rendered."""
        return self._ripple_active and self._ripple_progress > 0


class InputMixin:
    """Mixin for input widgets (TextField, Checkbox, etc).
    
    Provides common input handling: validation, change events, etc.
    """
    
    def __init__(self):
        self._value: Any = None
        self._error_text: str | None = None
        self._validators: list[Callable[[Any], str | None]] = []
        self.on_change: Callable | list[Callable] | None = None
    
    def add_validator(self, validator: Callable[[Any], str | None]) -> None:
        """Add a validation function.
        
        The validator should return None if valid, or an error message string.
        
        Example:
            def validate_email(value):
                if '@' not in value:
                    return "Invalid email"
                return None
            
            field.add_validator(validate_email)
        """
        self._validators.append(validator)
    
    def validate(self) -> bool:
        """Run all validators and update error state.
        
        Returns:
            True if valid, False otherwise
        """
        for validator in self._validators:
            error = validator(self._value)
            if error is not None:
                self._error_text = error
                if hasattr(self, 'update'):
                    self.update()
                return False
        
        self._error_text = None
        return True
    
    def _emit_change(self) -> None:
        """Emit change event to handlers."""
        if self.on_change is None:
            return
        
        from ..event import fire
        if hasattr(self, 'page') and self.page is not None:
            fire(self, "change", self._value)


class AnimatedMixin:
    """Mixin for widgets with built-in animations.
    
    Tracks animation state and provides update scheduling.
    """
    
    def __init__(self):
        self._animating = False
        self._last_animation_tick = 0.0
    
    def _start_animation(self) -> None:
        """Mark widget as animating and request repaints."""
        if not self._animating:
            self._animating = True
            self._last_animation_tick = time.perf_counter()
            self._schedule_animation_tick()
    
    def _stop_animation(self) -> None:
        """Stop animation."""
        self._animating = False
    
    def _schedule_animation_tick(self) -> None:
        """Request next animation frame."""
        if hasattr(self, 'page') and self.page is not None:
            self.page.repaint()
    
    def _tick_animations(self, now: float) -> bool:
        """Update all animations. Override in subclasses.
        
        Returns:
            True if still animating, False if complete
        """
        return False


def draw_state_layer(
    renderer,
    x: float,
    y: float,
    width: float,
    height: float,
    color: tuple[int, int, int, int],
    radius: float = 0.0
) -> None:
    """Draw a state layer overlay (hover/focus/press feedback).
    
    This is a reusable helper that replaces duplicated drawing code.
    
    Args:
        renderer: Renderer instance
        x, y, width, height: Geometry
        color: RGBA color tuple
        radius: Corner radius
    """
    if color[3] == 0:
        return  # Fully transparent, skip
    
    renderer.overlay_rect(x, y, width, height, color, radius=radius)


def draw_ripple(
    renderer,
    x: float,
    y: float,
    width: float,
    height: float,
    ripple_x: float,
    ripple_y: float,
    progress: float,
    color: tuple[int, int, int, int],
    radius: float = 0.0
) -> None:
    """Draw expanding ripple effect from a point.
    
    Args:
        renderer: Renderer instance
        x, y, width, height: Widget geometry
        ripple_x, ripple_y: Ripple origin (relative to widget)
        progress: Animation progress (0-1)
        color: RGBA color tuple
        radius: Corner radius for clipping
    """
    if progress <= 0 or color[3] == 0:
        return
    
    # Calculate ripple radius (expands to cover widget)
    max_radius = max(
        (ripple_x ** 2 + ripple_y ** 2) ** 0.5,
        ((width - ripple_x) ** 2 + ripple_y ** 2) ** 0.5,
        (ripple_x ** 2 + (height - ripple_y) ** 2) ** 0.5,
        ((width - ripple_x) ** 2 + (height - ripple_y) ** 2) ** 0.5,
    )
    
    current_radius = max_radius * progress
    
    # Fade out as it expands
    alpha = int(color[3] * (1 - progress))
    ripple_color = (color[0], color[1], color[2], alpha)
    
    # Draw ripple circle (clipped to widget bounds)
    renderer.clip_push(x, y, width, height)
    renderer.circle(
        x + ripple_x,
        y + ripple_y,
        current_radius,
        ripple_color,
        fill=True
    )
    renderer.clip_pop()


class FocusableMixin:
    """Mixin for keyboard-focusable widgets."""
    
    _focusable = True
    
    def __init__(self):
        self.on_focus: Callable | None = None
        self.on_blur: Callable | None = None
    
    def focus(self) -> None:
        """Request keyboard focus."""
        if hasattr(self, 'page') and self.page is not None:
            self.page.focus(self)


# Convenience base class combining common mixins
class InteractiveControl(StatefulMixin, FocusableMixin, AnimatedMixin):
    """Base for interactive controls (buttons, inputs, etc).
    
    Combines state management, focus handling, and animation support.
    Eliminates ~500 lines of duplicated code across widgets.
    """
    
    def __init__(self):
        StatefulMixin.__init__(self)
        FocusableMixin.__init__(self)
        AnimatedMixin.__init__(self)
