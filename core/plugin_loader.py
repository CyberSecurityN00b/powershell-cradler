import importlib
import pkgutil

from typing import Dict, Type
from plugins._base import BaseCradlePlugin


def discover_plugins() -> Dict[str, Type[BaseCradlePlugin]]:
    """Walk the plugins package and collect every BaseCradle subclass."""
    import plugins as _plugins_pkg

    plugin_map: Dict[str, Type[BaseCradlePlugin]] = {}

    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=_plugins_pkg.__path__,
        prefix=_plugins_pkg.__name__ + ".",
        onerror=lambda x: None
    ):
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseCradlePlugin)
                and attr is not BaseCradlePlugin
                and getattr(attr, "NAME", "undefined") != "undefined"
            ):
                plugin_map[attr.NAME.lower()] = attr
    
    return plugin_map