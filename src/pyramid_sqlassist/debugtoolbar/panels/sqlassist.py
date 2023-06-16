# stdlib
from typing import TYPE_CHECKING

# pypi
from pyramid_debugtoolbar.panels import DebugPanel

# typing
if TYPE_CHECKING:
    from pyramid.request import Request

# ==============================================================================


class PyramidSqlAssistDebugPanel(DebugPanel):
    """
    Sample debug panel
    """

    name = "SQLAssist"
    has_content = True
    template = "pyramid_sqlassist.debugtoolbar.panels:templates/sqlassist.dbtmako"

    def __init__(self, request):
        if hasattr(request.registry, "pyramid_sqlassist"):
            dbSessionName = request.registry.pyramid_sqlassist["request_method_name"]
            self.data = {
                "registry_data": request.registry.pyramid_sqlassist,
                "dbSession": getattr(request, dbSessionName),
            }
        else:
            self.data = {
                "registry_data": None,
                "dbSession": None,
            }

    @property
    def nav_title(self) -> str:
        return self.name

    @property
    def title(self) -> str:
        return self.name

    @property
    def url(self) -> str:
        return ""

    def render_content(self, request: "Request") -> str:
        return DebugPanel.render_content(self, request)
