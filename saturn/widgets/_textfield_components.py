"""TextField component architecture - replaces monolithic 2000+ line class.

Splits TextField into focused, testable components:
- TextEditor: Core text editing logic
- InputDecorator: Border, label, prefix/suffix rendering
- IMEHandler: Input method composition
- TextFieldAnimator: State animations

This reduces the main TextField class to ~300 lines of coordination code.
"""
from __future__ import annotations

import re
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import TextSelection

from .._errors import validate_type, ConfigurationError


class TextEditor:
    """Core text editing logic without UI concerns.
    
    Handles:
    - Text insertion/deletion
    - Selection management
    - Cursor movement
    - Clipboard operations
    - Input filtering
    """
    
    def __init__(
        self,
        value: str = "",
        multiline: bool = False,
        max_length: int | None = None,
        input_filter=None,
    ):
        self._value = value
        self._multiline = multiline
        self._max_length = max_length
        self._input_filter = input_filter
        
        # Selection state
        self._selection_base = 0
        self._selection_extent = 0
        
        # Change callback
        self.on_change: Callable[[str], None] | None = None
    
    @property
    def value(self) -> str:
        """Current text value."""
        return self._value
    
    @value.setter
    def value(self, text: str) -> None:
        """Set text value and reset selection."""
        validate_type(text, str, "value")
        self._value = self._apply_filter(text)
        self._selection_base = len(self._value)
        self._selection_extent = len(self._value)
        self._emit_change()
    
    @property
    def selection_start(self) -> int:
        """Start of selection (min of base and extent)."""
        return min(self._selection_base, self._selection_extent)
    
    @property
    def selection_end(self) -> int:
        """End of selection (max of base and extent)."""
        return max(self._selection_base, self._selection_extent)
    
    @property
    def has_selection(self) -> bool:
        """Check if text is selected."""
        return self._selection_base != self._selection_extent
    
    def select_all(self) -> None:
        """Select all text."""
        self._selection_base = 0
        self._selection_extent = len(self._value)
    
    def select_range(self, start: int, end: int) -> None:
        """Set selection to specific range."""
        start = max(0, min(start, len(self._value)))
        end = max(0, min(end, len(self._value)))
        self._selection_base = start
        self._selection_extent = end
    
    def move_cursor(self, offset: int, extend_selection: bool = False) -> None:
        """Move cursor by offset.
        
        Args:
            offset: Character offset (negative = left, positive = right)
            extend_selection: If True, extend selection; if False, move cursor
        """
        if not extend_selection and self.has_selection:
            # Collapse selection
            if offset < 0:
                self._selection_base = self.selection_start
            else:
                self._selection_base = self.selection_end
            self._selection_extent = self._selection_base
            return
        
        new_pos = self._selection_extent + offset
        new_pos = max(0, min(new_pos, len(self._value)))
        
        if extend_selection:
            self._selection_extent = new_pos
        else:
            self._selection_base = new_pos
            self._selection_extent = new_pos
    
    def move_to_line_start(self, extend_selection: bool = False) -> None:
        """Move cursor to start of current line."""
        pos = self._selection_extent
        # Find start of current line
        line_start = self._value.rfind('\n', 0, pos)
        new_pos = 0 if line_start == -1 else line_start + 1
        
        if extend_selection:
            self._selection_extent = new_pos
        else:
            self._selection_base = new_pos
            self._selection_extent = new_pos
    
    def move_to_line_end(self, extend_selection: bool = False) -> None:
        """Move cursor to end of current line."""
        pos = self._selection_extent
        # Find end of current line
        line_end = self._value.find('\n', pos)
        new_pos = len(self._value) if line_end == -1 else line_end
        
        if extend_selection:
            self._selection_extent = new_pos
        else:
            self._selection_base = new_pos
            self._selection_extent = new_pos
    
    def insert(self, text: str) -> bool:
        """Insert text at cursor or replace selection.
        
        Returns:
            True if text was inserted, False if max_length exceeded
        """
        # Delete selection first if any
        if self.has_selection:
            self.delete_selection()
        
        # Apply filter
        text = self._apply_filter(text)
        if not text:
            return True
        
        # Check max length
        if self._max_length is not None:
            new_length = len(self._value) + len(text)
            if new_length > self._max_length:
                # Truncate to fit
                available = self._max_length - len(self._value)
                if available <= 0:
                    return False
                text = text[:available]
        
        # Handle multiline
        if not self._multiline:
            text = text.replace('\n', '').replace('\r', '')
        
        # Insert text
        pos = self._selection_extent
        self._value = self._value[:pos] + text + self._value[pos:]
        
        # Move cursor to end of inserted text
        new_pos = pos + len(text)
        self._selection_base = new_pos
        self._selection_extent = new_pos
        
        self._emit_change()
        return True
    
    def delete_selection(self) -> None:
        """Delete selected text."""
        if not self.has_selection:
            return
        
        start = self.selection_start
        end = self.selection_end
        self._value = self._value[:start] + self._value[end:]
        self._selection_base = start
        self._selection_extent = start
        self._emit_change()
    
    def backspace(self) -> None:
        """Delete character before cursor or delete selection."""
        if self.has_selection:
            self.delete_selection()
        elif self._selection_extent > 0:
            pos = self._selection_extent - 1
            self._value = self._value[:pos] + self._value[self._selection_extent:]
            self._selection_base = pos
            self._selection_extent = pos
            self._emit_change()
    
    def delete(self) -> None:
        """Delete character after cursor or delete selection."""
        if self.has_selection:
            self.delete_selection()
        elif self._selection_extent < len(self._value):
            pos = self._selection_extent
            self._value = self._value[:pos] + self._value[pos + 1:]
            self._emit_change()
    
    def _apply_filter(self, text: str) -> str:
        """Apply input filter to text."""
        if self._input_filter is None:
            return text
        
        # Support InputFilter objects
        if hasattr(self._input_filter, 'regex_string'):
            pattern = re.compile(self._input_filter.regex_string)
            replacement = getattr(self._input_filter, 'replacement_string', '')
            
            if getattr(self._input_filter, 'allow', True):
                # Keep only matching characters
                return ''.join(pattern.findall(text))
            else:
                # Remove matching characters
                return pattern.sub(replacement, text)
        
        # Support regex strings directly
        if isinstance(self._input_filter, str):
            pattern = re.compile(self._input_filter)
            return ''.join(pattern.findall(text))
        
        return text
    
    def _emit_change(self) -> None:
        """Notify change callback."""
        if self.on_change:
            self.on_change(self._value)


class InputDecorator:
    """TextField border, label, and adornment rendering.
    
    Handles the visual decoration around the text input:
    - Border styles (outline, underline, none)
    - Floating label animation
    - Prefix/suffix/helper text
    - Error state
    """
    
    def __init__(
        self,
        label: str | None = None,
        hint_text: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        helper_text: str | None = None,
        error_text: str | None = None,
        border_style: str = "outline",
    ):
        self.label = label
        self.hint_text = hint_text
        self.prefix = prefix
        self.suffix = suffix
        self.helper_text = helper_text
        self.error_text = error_text
        self.border_style = border_style
        
        # Animation state
        self._label_progress = 0.0  # 0=hint position, 1=floating position
        self._target_label_progress = 0.0
    
    def update_label_position(self, has_content: bool, is_focused: bool) -> None:
        """Update label floating animation target.
        
        Label should float up when:
        - Field is focused
        - Field has content
        """
        should_float = has_content or is_focused
        self._target_label_progress = 1.0 if should_float else 0.0
    
    def tick_animations(self, delta_time: float) -> bool:
        """Update animations. Returns True if animating."""
        if abs(self._label_progress - self._target_label_progress) < 0.01:
            self._label_progress = self._target_label_progress
            return False
        
        # Animate label position
        speed = 5.0  # Units per second
        if self._label_progress < self._target_label_progress:
            self._label_progress = min(
                self._target_label_progress,
                self._label_progress + speed * delta_time
            )
        else:
            self._label_progress = max(
                self._target_label_progress,
                self._label_progress - speed * delta_time
            )
        
        return True


class IMEHandler:
    """Input Method Editor support for CJK languages.
    
    Handles composition text (候補/候选) display and management.
    """
    
    def __init__(self):
        self._composition_text = ""
        self._composition_start = 0
        self._composition_length = 0
        self._active = False
    
    @property
    def active(self) -> bool:
        """Check if IME composition is active."""
        return self._active
    
    @property
    def composition_text(self) -> str:
        """Current composition text."""
        return self._composition_text
    
    def update_composition(
        self,
        text: str,
        start: int = 0,
        length: int | None = None
    ) -> None:
        """Update IME composition state.
        
        Args:
            text: Composition text
            start: Cursor position in composition
            length: Selected length in composition
        """
        self._composition_text = text
        self._composition_start = start
        self._composition_length = length if length is not None else len(text)
        self._active = bool(text)
    
    def clear_composition(self) -> None:
        """Clear composition state."""
        self._composition_text = ""
        self._composition_start = 0
        self._composition_length = 0
        self._active = False
    
    def get_display_text(self, base_text: str, cursor_pos: int) -> str:
        """Get text with composition inserted at cursor.
        
        Args:
            base_text: The committed text
            cursor_pos: Cursor position
        
        Returns:
            Text with composition inserted
        """
        if not self._active:
            return base_text
        
        return (
            base_text[:cursor_pos] +
            self._composition_text +
            base_text[cursor_pos:]
        )


class TextFieldAnimator:
    """Manages TextField state animations.
    
    - Border color transitions
    - Label floating
    - Error shake
    """
    
    def __init__(self):
        self._border_color_progress = 0.0
        self._error_shake_time = 0.0
        self._error_shake_duration = 0.5
    
    def trigger_error_shake(self) -> None:
        """Trigger error shake animation."""
        self._error_shake_time = 0.0
    
    def tick(self, delta_time: float) -> bool:
        """Update animations. Returns True if animating."""
        animating = False
        
        # Error shake
        if self._error_shake_time < self._error_shake_duration:
            self._error_shake_time += delta_time
            animating = True
        
        return animating
    
    def get_error_shake_offset(self) -> float:
        """Get current horizontal shake offset."""
        if self._error_shake_time >= self._error_shake_duration:
            return 0.0
        
        # Damped sine wave
        progress = self._error_shake_time / self._error_shake_duration
        amplitude = 4.0 * (1 - progress)  # Decay
        frequency = 3.0
        
        import math
        return amplitude * math.sin(progress * frequency * 2 * math.pi)
