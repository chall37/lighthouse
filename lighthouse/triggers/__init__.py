"""
Built-in trigger implementations for Lighthouse.

Automatically discovers and imports all trigger modules with validation.
"""

import importlib
import inspect
import pkgutil

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.logging_config import get_logger

logger = get_logger(__name__)

# Automatically import all trigger modules and collect their exports
__all__ = []
_seen_names = set()

for module_info in pkgutil.iter_modules(__path__):
    # Import the module
    module = importlib.import_module(f"{__name__}.{module_info.name}")

    # Validate and add all exported names
    if hasattr(module, '__all__'):
        for name in module.__all__:
            # Check for name conflicts
            if name in _seen_names:
                logger.warning(
                    "Duplicate trigger name '%s' in module '%s' - skipping",
                    name,
                    module_info.name
                )
                continue

            cls = getattr(module, name)

            # Validate it's a class and subclass of BaseTrigger
            if not inspect.isclass(cls):
                logger.warning(
                    "Export '%s' in module '%s' is not a class - skipping",
                    name,
                    module_info.name
                )
                continue

            if not issubclass(cls, BaseTrigger):
                logger.warning(
                    "Export '%s' in module '%s' is not a Trigger subclass - skipping",
                    name,
                    module_info.name
                )
                continue

            # Validation passed - add to namespace
            globals()[name] = cls
            __all__.append(name)
            _seen_names.add(name)
