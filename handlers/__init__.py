"""Handler registration for Whispier Bot."""
from .commands import register_command_handlers
from .inline import register_inline_handlers
from .callbacks import register_callback_handlers
from .stats import register_stats_handlers

def register_handlers(app):
    register_command_handlers(app)
    register_stats_handlers(app)
    register_inline_handlers(app)
    register_callback_handlers(app)
