import logging
log = logging.getLogger(__name__)

from . import interface


import re
re_excludes= re.compile("/(img|_debug|js|css)")


from pyramid.tweens import EXCVIEW

def includeme(config):
    """set up tweens"""
    config.add_tween('pyramid_sqlassist.sqlassist_tween_factory', under=EXCVIEW)


def sqlassist_tween_factory(handler, registry):
    def sqlassist_tween(request):
        if re.match( re_excludes , request.path_info ):
            return handler(request)
        try:
            response = handler(request)
            return response
        finally :
            if __debug__ :
                log.debug("sqlassist_tween_factory - dbSessionCleanup()")
            interface.dbSessionCleanup()
    return sqlassist_tween


