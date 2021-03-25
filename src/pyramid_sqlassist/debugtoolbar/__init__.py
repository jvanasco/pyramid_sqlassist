from .panels.sqlassist import PyramidSqlAssistDebugPanel


def includeme(config):
    """
    Pyramid API hook
    """
    config.add_debugtoolbar_panel(PyramidSqlAssistDebugPanel)
