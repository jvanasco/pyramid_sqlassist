# stdlib
from typing import TYPE_CHECKING

# local
from .panels.sqlassist import PyramidSqlAssistDebugPanel

# typing
if TYPE_CHECKING:
    from pyramid.config import Configurator  # type: ignore[import]

# ==============================================================================


def includeme(config: "Configurator") -> None:
    """
    Pyramid API hook
    """
    config.add_debugtoolbar_panel(PyramidSqlAssistDebugPanel)
