from pyramid_debugtoolbar.panels import DebugPanel

_ = lambda x: x


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
            self.data = {"registry_data": None, "dbSession": None}

    @property
    def nav_title(self):
        return _(self.name)

    @property
    def title(self):
        return _(self.name)

    @property
    def url(self):
        return ""

    def render_content(self, request):
        return DebugPanel.render_content(self, request)
