"""Aggregate command registration."""
from .start import register_start_command
from .help import register_help_command

def register_command_handlers(app):
    register_start_command(app)
    register_help_command(app)
