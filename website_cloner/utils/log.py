"""
Logging utilities for the website cloner.

Provides colorful CLI logging using the rich library.
"""

import logging
import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Global console instance
console = Console() if RICH_AVAILABLE else None

# Logger instances cache
_loggers: dict = {}


def setup_logger(
    name: str = "website_cloner",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger with optional rich formatting.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    if RICH_AVAILABLE:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
    
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    _loggers[name] = logger
    return logger


def get_logger(name: str = "website_cloner") -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]


def create_progress() -> Optional[Progress]:
    """
    Create a rich progress bar instance.
    
    Returns:
        Progress instance if rich is available, None otherwise
    """
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
    return None


def print_status(message: str, style: str = "bold blue") -> None:
    """
    Print a styled status message.
    
    Args:
        message: Message to print
        style: Rich style string
    """
    if RICH_AVAILABLE and console:
        console.print(f"[{style}]{message}[/{style}]")
    else:
        print(message)


def print_error(message: str) -> None:
    """
    Print an error message.
    
    Args:
        message: Error message to print
    """
    print_status(f"❌ {message}", "bold red")


def print_success(message: str) -> None:
    """
    Print a success message.
    
    Args:
        message: Success message to print
    """
    print_status(f"✅ {message}", "bold green")


def print_warning(message: str) -> None:
    """
    Print a warning message.
    
    Args:
        message: Warning message to print
    """
    print_status(f"⚠️ {message}", "bold yellow")


def print_info(message: str) -> None:
    """
    Print an info message.
    
    Args:
        message: Info message to print
    """
    print_status(f"ℹ️ {message}", "bold cyan")
