import logging
log = logging.getLogger(__name__)

from . import interface


import re

regex_path_excludes = None
regex_path_excludes_default = "/(img|_debug|js|css)"


from pyramid.tweens import EXCVIEW



def includeme(config):
    """set up tweens"""
    global regex_path_excludes , regex_path_excludes_default

    _regex_path_excludes = regex_path_excludes_default
    if 'pyramid_sqlassist.regex_path_excludes' in config.registry.settings :
        _regex_path_excludes = config.registry.settings['pyramid_sqlassist.regex_path_excludes']
    if _regex_path_excludes :
        regex_path_excludes = re.compile( _regex_path_excludes )
    config.add_tween('pyramid_sqlassist.sqlassist_tween_factory', under=EXCVIEW)



def sqlassist_tween_factory(handler, registry):
    def sqlassist_tween(request):
        if ( regex_path_excludes is not None ) and re.match( regex_path_excludes , request.path_info ):
            return handler(request)
        try:
            if __debug__ :
                log.debug("sqlassist_tween_factory - BEGIN")
                log.debug("sqlassist_tween_factory - BEGIN | request = %s" , id(request) )
            interface.dbSessionSetup(request)
            response = handler(request)
            return response
        finally :
            if __debug__ :
                log.debug("sqlassist_tween_factory - END")
                log.debug("sqlassist_tween_factory - END | request = %s" , id(request) )
    return sqlassist_tween


