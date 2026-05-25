import importlib
import pkgutil

from typing import Dict, Tuple, Type
from plugins._base import BaseCradle


def discover_plugins() -> Dict[Tuple[str, str], Type[BaseCradle]]:
    """Walk the plugins package and collect every BaseCradle subclass."""
    import plugins as _plugins_pkg

    plugin_map: Dict[Tuple[str, str], Type[BaseCradle]] = {}

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
                and issubclass(attr, BaseCradle)
                and attr is not BaseCradle
                and getattr(attr, "TYPE", "undefined") != "undefined"
            ):
                plugin_map[attr.TYPE.lower()] = attr
    
    return plugin_map