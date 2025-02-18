from importlib.metadata import PackageNotFoundError, version

from datashuttle.datashuttle_class import DataShuttle
from datashuttle.datashuttle_functions import quick_validate_project


try:
    __version__ = version("datashuttle")
except PackageNotFoundError:
    # package is not installed
    pass
