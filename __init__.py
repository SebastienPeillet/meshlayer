# -*- coding: UTF-8 -*-

from meshlayer import MeshLayerType, MeshLayer

class Plugin():
    def __init__(self, iface):
        self.iface = iface
    def initGui(self):
        QgsPluginLayerRegistry.instance().addPluginLayerType(MeshLayerType())
    def unload(self):
        QgsPluginLayerRegistry.instance().removePluginLayerType(MeshLayerType.LAYER_TYPE)

def classFactory(iface):
    return Plugin(iface)

