import importlib
import os
import tempfile
from typing import Optional

# similar to base::system.file()
def package_dir(package: str) -> str:
    with tempfile.TemporaryDirectory():
        pkg_file = importlib.import_module(".", package=package).__file__
        if pkg_file is None:
            raise ImportError(f"Couldn't load package {package}")
        return os.path.dirname(pkg_file)


def is_instance_of_class(
    x: object, class_name: str, module_name: Optional[str] = None
) -> bool:
    typ = type(x)
    res = typ.__name__ == class_name
    if module_name is None:
        return res
    else:
        return res and typ.__module__ == module_name
