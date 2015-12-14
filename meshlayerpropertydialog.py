# -*- coding: UTF-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from utilities import format_, complete_filename
from glmesh import ColorLegend

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

        self.colorButton.setIcon(QIcon(layer.colorLegend().colorRamp()))
        
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

        self.logCheckBox.setChecked(layer.colorLegend().hasLogScale())
        def logOnOff(flag):
            layer.colorLegend().setLogScale(self.logCheckBox.isChecked())
        self.logCheckBox.toggled.connect(logOnOff)

        def updateGraduation(item=None):
            classes = []
            for row in range(self.tableWidget.rowCount()):
                min_, max_ = None, None
                if self.tableWidget.item(row, 1) and self.tableWidget.item(row, 2):
                    try:
                        min_ = float(self.tableWidget.item(row, 1).text())
                        self.tableWidget.item(row, 1).setBackground(QBrush(Qt.white))
                    except ValueError:
                        self.tableWidget.item(row, 1).setBackground(QBrush(Qt.red))
                    try:
                        max_ = float(self.tableWidget.item(row, 2).text())
                        self.tableWidget.item(row, 2).setBackground(QBrush(Qt.white))
                    except ValueError:
                        self.tableWidget.item(row, 2).setBackground(QBrush(Qt.red))
                if min_ and max_:
                    classes.append((self.tableWidget.item(row, 0).background().color(), min_, max_))

            layer.colorLegend().setGraduation(classes)

        def addGraduation(flag=None):
            idx = self.tableWidget.rowCount()
            self.tableWidget.setRowCount(idx+1)
            colorItem = QTableWidgetItem()
            colorItem.setFlags(colorItem.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEditable)
            colorItem.setBackground(QBrush(Qt.red))
            self.tableWidget.setItem(idx, 0, colorItem)
            min_ = layer.dataProvider().minValue()
            max_ = layer.dataProvider().maxValue()
            fmt = format_(min_, max_)
            self.tableWidget.setItem(idx, 1, QTableWidgetItem(fmt%min_))
            self.tableWidget.setItem(idx, 2, QTableWidgetItem(fmt%max_))

        def editColor(row, colum):
            if colum != 0:
                return

            item = self.tableWidget.item(row, 0)
            color = QColorDialog.getColor(item.background().color(), self) 
            if color.isValid(): # false on user cancel
                item.setBackground(QBrush(color)) 

        def removeGraduation(flag=None):
            while len(self.tableWidget.selectedRanges()):
                for range_ in self.tableWidget.selectedRanges():
                    self.tableWidget.removeRow(range_.bottomRow())
            updateGraduation()

        if layer.colorLegend().graduated():
            self.symboTypeComboBox.setCurrentIndex(1)

        if layer.colorLegend().graduation():
            graduation = layer.colorLegend().graduation()
            min_, max_ = (min([c[1] for c in graduation]), max([c[2] for c in graduation])) if len(graduation) else (0,0)
            fmt = format_(min_, max_)
            for class_ in graduation:
                idx = self.tableWidget.rowCount()
                self.tableWidget.setRowCount(idx+1)
                colorItem = QTableWidgetItem()
                colorItem.setFlags(colorItem.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEditable)
                colorItem.setBackground(QBrush(class_[0]))
                self.tableWidget.setItem(idx, 0, colorItem)
                self.tableWidget.setItem(idx, 1, QTableWidgetItem(fmt%class_[1]))
                self.tableWidget.setItem(idx, 2, QTableWidgetItem(fmt%class_[2]))

        self.plusButton.clicked.connect(addGraduation)
        self.minusButton.clicked.connect(removeGraduation)
        self.tableWidget.cellDoubleClicked.connect(editColor)
        self.tableWidget.itemChanged.connect(updateGraduation)
        self.tableWidget.itemChanged.connect(updateGraduation)

        def setSymbology(idx):
            if idx==0:
                layer.colorLegend().toggleGraduation(False)
            else:
                layer.colorLegend().toggleGraduation(True)

        self.symboTypeComboBox.currentIndexChanged.connect(setSymbology)
        
