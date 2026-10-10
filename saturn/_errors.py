"""Unified error handling and logging system for Saturn.

Replaces scattered try-except blocks with proper error handling,
logging, and user-friendly error reporting.
"""
from __future__ import annotations

import logging
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import Callable, Any, TypeVar, Optional

# Configure Saturn logger
logger = logging.getLogger("saturn")
logger.setLevel(logging.INFO)

# Console handler
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
_console_handler.setFormatter(_formatter)
logger.addHandler(_console_handler)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SaturnError(Exception):
    """Base exception for all Saturn framework errors."""
    
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class RendererError(SaturnError):
    """Rendering backend initialization or operation failed."""
    pass


class ResourceError(SaturnError):
    """Resource loading failed (fonts, images, etc)."""
    pass


class LayoutError(SaturnError):
    """Layout calculation error."""
    pass


class ThreadingError(SaturnError):
    """Thread synchronization or concurrency error."""
    pass


class ConfigurationError(SaturnError):
    """Invalid configuration or parameters."""
    pass


def handle_error(
    error: Exception,
    context: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    fallback_value: Any = None,
    reraise: bool = False
) -> Any:
    """Unified error handler with logging and optional fallback.
    
    Args:
        error: The exception that occurred
        context: Human-readable context (e.g., "loading font")
        severity: Error severity level
        fallback_value: Value to return if not re-raising
        reraise: Whether to re-raise the exception after logging
    
    Returns:
        fallback_value if reraise=False, otherwise raises
    
    Example:
        try:
            font = load_font(path)
        except Exception as e:
            font = handle_error(e, "loading font", fallback_value=default_font)
    """
    # Log with appropriate level
    log_func = getattr(logger, severity.value)
    
    if isinstance(error, SaturnError):
        # Saturn errors are already structured
        log_func(f"{context}: {error}")
        if error.cause:
            logger.debug(f"Caused by: {error.cause}", exc_info=error.cause)
    else:
        # Wrap external errors
        log_func(f"{context}: {type(error).__name__}: {error}")
        logger.debug(f"Traceback:", exc_info=error)
    
    if reraise:
        if isinstance(error, SaturnError):
            raise error
        raise SaturnError(f"{context}: {error}", cause=error)
    
    return fallback_value


def safe_call(
    func: Callable[..., T],
    *args: Any,
    context: str = "",
    fallback: T | None = None,
    log_errors: bool = True,
    **kwargs: Any
) -> T | None:
    """Safely call a function with error handling.
    
    Args:
        func: Function to call
        *args: Positional arguments
        context: Error context for logging
        fallback: Value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments
    
    Returns:
        Function result or fallback value
    
    Example:
        result = safe_call(
            risky_operation,
            arg1, arg2,
            context="processing data",
            fallback=[]
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            handle_error(
                e,
                context or f"calling {func.__name__}",
                severity=ErrorSeverity.ERROR,
                fallback_value=fallback
            )
        return fallback


def try_or_none(func: Callable[..., T], *args: Any, **kwargs: Any) -> T | None:
    """Execute function and return None on any error (silent failure).
    
    Use sparingly - prefer safe_call with proper logging.
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


def validate_type(
    value: Any,
    expected_type: type | tuple[type, ...],
    name: str,
    allow_none: bool = False
) -> None:
    """Validate parameter type and raise ConfigurationError if invalid.
    
    Args:
        value: Value to validate
        expected_type: Expected type(s)
        name: Parameter name for error message
        allow_none: Whether None is acceptable
    
    Raises:
        ConfigurationError: If validation fails
    
    Example:
        validate_type(opacity, (int, float), "opacity")
    """
    if allow_none and value is None:
        return
    
    if not isinstance(value, expected_type):
        expected_names = (
            expected_type.__name__ if isinstance(expected_type, type)
            else " or ".join(t.__name__ for t in expected_type)
        )
        raise ConfigurationError(
            f"{name} must be {expected_names}, got {type(value).__name__}"
        )


def validate_range(
    value: float,
    min_val: float,
    max_val: float,
    name: str,
    inclusive: bool = True
) -> None:
    """Validate numeric value is within range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        name: Parameter name for error message
        inclusive: Whether bounds are inclusive
    
    Raises:
        ConfigurationError: If out of range
    """
    if inclusive:
        if not (min_val <= value <= max_val):
            raise ConfigurationError(
                f"{name} must be between {min_val} and {max_val}, got {value}"
            )
    else:
        if not (min_val < value < max_val):
            raise ConfigurationError(
                f"{name} must be strictly between {min_val} and {max_val}, got {value}"
            )


class ErrorCollector:
    """Collect multiple errors during a batch operation.
    
    Useful for validation where you want to report all errors at once
    rather than failing on the first one.
    """
    
    def __init__(self):
        self.errors: list[tuple[str, Exception]] = []
    
    def add(self, context: str, error: Exception) -> None:
        """Add an error to the collection."""
        self.errors.append((context, error))
        logger.debug(f"{context}: {error}")
    
    def try_call(self, func: Callable, context: str, *args: Any, **kwargs: Any) -> Any:
        """Try calling function and collect any errors."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.add(context, e)
            return None
    
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0
    
    def raise_if_errors(self, message: str = "Multiple errors occurred") -> None:
        """Raise combined error if any were collected."""
        if not self.errors:
            return
        
        error_details = "\n".join(
            f"  - {ctx}: {err}" for ctx, err in self.errors
        )
        raise SaturnError(f"{message}:\n{error_details}")
    
    def clear(self) -> None:
        """Clear collected errors."""
        self.errors.clear()


def setup_file_logging(log_path: str | Path) -> None:
    """Add file handler to Saturn logger.
    
    Args:
        log_path: Path to log file
    """
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_formatter)
    logger.addHandler(file_handler)


def set_log_level(level: str) -> None:
    """Set Saturn logger level.
    
    Args:
        level: "DEBUG", "INFO", "WARNING", "ERROR", or "CRITICAL"
    """
    logger.setLevel(getattr(logging, level.upper()))
    _console_handler.setLevel(getattr(logging, level.upper()))
