"""pms-ai — a staging ground for projects.

Subsystem #1: the plugin shell + configuration core. ``pms_ai.config`` is the
single source of truth for config logic; the ``config`` skill, the ``/onboard``
command, and the ``pms-ai`` CLI all wrap it (never reimplement it).
"""

__version__ = "0.1.0"
