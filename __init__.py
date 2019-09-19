from builtins import object
# -*- coding: UTF-8 -*-

class Plugin(object):
    def __init__(self, iface):
        pass

    def initGui(self):
        pass

    def unload(self):
        pass

def classFactory(iface):
    return Plugin(iface)

