# -*- coding: UTF-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from utilities import format_, complete_filename
from meshlayer import ColorLegend

import numpy

class MeshLayerPropertyDialog(QDialog):
    __colorRampChanged = pyqtSignal(str)
    def __init__(self, layer):
        super(MeshLayerPropertyDialog, self).__init__()
        uic.loadUi(complete_filename('meshlayerproperties.ui'), self)

        fmt = format_(layer.colorLegend().minValue(), layer.colorLegend().maxValue())
        self.minValue.setText(fmt%layer.colorLegend().minValue())
        self.maxValue.setText(fmt%layer.colorLegend().maxValue())
        self.transparencySlider.setValue(layer.colorLegend().transparencyPercent())

        menu = QMenu(self.colorButton)
        self.colorButton.setMenu(menu)
        for name, fil in ColorLegend.availableRamps().iteritems():
            img = QImage(fil).scaled(QSize(30,30))
            action = QAction(QIcon(QPixmap.fromImage(img)), name, self.colorButton)
            def emitter(f):
                def func(flag=None): 
                    self.__colorRamp = f
                    self.colorButton.setIcon(QIcon(f))
                    self.__colorRampChanged.emit(f)
                return func
            emitter(fil)()
            action.triggered.connect(emitter(fil))
            menu.addAction(action)
        self.__colorRampChanged.connect(layer.colorLegend().setColorRamp)
        self.minValue.textChanged.connect(layer.colorLegend().setMinValue)
        self.maxValue.textChanged.connect(layer.colorLegend().setMaxValue)
        self.transparencySlider.valueChanged.connect(
             layer.colorLegend().setTransparencyPercent)
        def updateMinMax():
            min_ = layer.dataProvider().minValue()
            max_ = layer.dataProvider().maxValue()
            fmt = format_(min_, max_)
            self.minValue.setText(fmt%min_)
            self.maxValue.setText(fmt%max_)
        self.updateMinMaxButton.clicked.connect(updateMinMax)
        self.show()

