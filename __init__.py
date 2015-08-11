# -*- coding: UTF-8 -*-

from meshlayer import MeshLayerType, MeshLayer
from winddataprovider import WindDataProvider
from meshdataproviderregistry import MeshDataProviderRegistry

from qgis.core import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import os

class Plugin():
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        MeshDataProviderRegistry.instance().addDataProviderType("wind", WindDataProvider)
        QgsPluginLayerRegistry.instance().addPluginLayerType(MeshLayerType())
        
        self.meshLayer = MeshLayer(\
                'directory='+os.path.dirname(__file__)+'/exemple/wind_fields crs=epsg:2154',
                'mesh layer',
                'wind')

        # configure legend
        self.meshLayer.colorLegend().setMaxValue( self.meshLayer.dataProvider().maxValue() )
        self.meshLayer.colorLegend().setMinValue( self.meshLayer.dataProvider().minValue() )
        self.meshLayer.colorLegend().setTitle('Wind speed')
        self.meshLayer.colorLegend().setUnits('m/s')
        QgsMapLayerRegistry.instance().addMapLayer(self.meshLayer)

        # create slider to animate results
        self.timeSlider = QSlider(Qt.Horizontal)
        self.timeSlider.setMinimum(0)
        self.timeSlider.setMaximum(len(self.meshLayer.dataProvider().dates())-1)
        self.actions = [self.iface.addToolBarWidget(self.timeSlider)]
        self.timeSlider.valueChanged.connect(self.meshLayer.dataProvider().setDate)

        # create play button
        self.timer = QTimer(None)
        self.playButton = QPushButton('play')
        self.playButton.setCheckable(True)
        self.actions.append(self.iface.addToolBarWidget(self.playButton))
        self.playButton.clicked.connect(self.play)

    def unload(self):
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        QgsPluginLayerRegistry.instance().removePluginLayerType(MeshLayer.LAYER_TYPE)
        MeshDataProviderRegistry.instance().removeDataProviderType("wind")

    def animate(self):
        if self.iface.mapCanvas().isDrawing():
            return
        self.timeSlider.setValue(
                (self.timeSlider.value() + 1) 
                % (self.timeSlider.maximum() + 1) )

    def play(self, checked):
        if checked:
            self.timer.stop()
            self.timer.timeout.connect(self.animate)
            self.timer.start(.1)
            self.playButton.setText('pause')
        else:
            self.timer.stop()
            self.playButton.setText('play')

def classFactory(iface):
    return Plugin(iface)

