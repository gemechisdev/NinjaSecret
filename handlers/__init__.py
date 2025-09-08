"""Handler registration for Whispier Bot."""

from .private import register_private_handlers
from .inline import register_inline_handlers
from .callbacks import register_callback_handlers


def register_handlers(app):
    """Register all handlers."""
    register_private_handlers(app)
    register_inline_handlers(app)
    register_callback_handlers(app)