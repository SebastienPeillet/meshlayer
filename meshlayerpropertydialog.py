from builtins import str
from builtins import range
# -*- coding: UTF-8 -*-

from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QImage, QPixmap, QIcon, QDoubleValidator
from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QMenu, QFileDialog, QAction, QColorDialog
from qgis.PyQt import uic

from .utilities import format_, complete_filename
from .glmesh import ColorLegend
from math import exp, log

from qgis.core import QgsProject

import numpy

class MeshLayerPropertyDialog(QDialog):
    __colorRampChanged = pyqtSignal(str)
    __classColorChanged = pyqtSignal(str)
    DEFAULT_NB_OF_CLASSES = 10

    def __init__(self, layer):
        super(MeshLayerPropertyDialog, self).__init__()
        uic.loadUi(complete_filename('meshlayerproperties.ui'), self)

        self.layer = layer
        if self.layer.colorLegend().nbClass():
            self.nbClassesSpinBox.setValue(self.layer.colorLegend().nbClass())
        else :
            self.nbClassesSpinBox.setValue(MeshLayerPropertyDialog.DEFAULT_NB_OF_CLASSES)
        fmt = format_(self.layer.colorLegend().minValue(), layer.colorLegend().maxValue())
        self.minValue.setText(fmt%self.layer.colorLegend().minValue())
        self.maxValue.setText(fmt%self.layer.colorLegend().maxValue())
        self.transparencySlider.setValue(self.layer.colorLegend().transparencyPercent())

        self.menu = QMenu(self.colorButton)
        self.colorButton.setMenu(self.menu)
        for name, fil in ColorLegend.availableRamps().items():
            img = QImage(fil).scaled(QSize(30,30))
            action = QAction(QIcon(QPixmap.fromImage(img)), name, self.colorButton)
            def emitter(f):
                def func(flag=None):
                    self.colorButton.setIcon(QIcon(f))
                    self.__colorRampChanged.emit(f)
                return func
            emitter(fil)()
            action.triggered.connect(emitter(fil))
            self.menu.addAction(action)

        self.colorButton.setIcon(QIcon(self.layer.colorLegend().colorRamp()))

        self.classMenu = QMenu(self.classColorButton)
        self.classColorButton.setMenu(self.classMenu)
        self.__classColor = None
        firstAction = None
        for name, fil in ColorLegend.availableRamps().items():
            if fil[-14:] != 'continuous.svg':
                continue
            img = QImage(fil).scaled(QSize(24,24))
            action = QAction(QIcon(QPixmap.fromImage(img)), name, self.classColorButton)
            def emitter(f):
                def func(flag=None):
                    img = QImage(f).scaled(QSize(24,24))
                    self.classColorButton.setIcon(QIcon(QPixmap.fromImage(QImage(f).scaled(QSize(24,24)))))
                    self.__classColor = f
                    self.__classColorChanged.emit(f)
                return func
            emitter(fil)()
            action.triggered.connect(emitter(fil))
            if not firstAction:
                firstAction = action
                self.__classColor = fil
                self.classColorButton.setIcon(QIcon(QPixmap.fromImage(QImage(fil).scaled(QSize(24,24)))))

            self.classMenu.addAction(action)

        self.__colorRampChanged.connect(self.layer.colorLegend().setColorRamp)
        self.minValue.textChanged.connect(self.setMinValue)
        self.maxValue.textChanged.connect(self.setMaxValue)
        self.transparencySlider.valueChanged.connect(
             self.layer.colorLegend().setTransparencyPercent)

        # floatValidator = QDoubleValidator()
        # self.minValue.setValidator(floatValidator)
        # self.maxValue.setValidator(floatValidator)

        self.updateMinMaxButton.clicked.connect(self.updateMinMax)
        if self.layer.colorLegend().graduated():
            self.symboTypeComboBox.setCurrentIndex(1)
        self.logCheckBox.setChecked(self.layer.colorLegend().hasLogScale())
        self.logCheckBox.toggled.connect(self.logOnOff)

        if layer.colorLegend().graduation():
            self.setFromGraduation(layer.colorLegend().graduation())

        self.classifyButton.clicked.connect(self.classify)
        self.plusButton.clicked.connect(self.addGraduation)
        self.minusButton.clicked.connect(self.removeGraduation)
        self.tableWidget.cellDoubleClicked.connect(self.editColor)
        self.tableWidget.itemChanged.connect(self.updateGraduation)
        self.symboTypeComboBox.currentIndexChanged.connect(self.setSymbology)
        self.loadButton.clicked.connect(self.loadClasses)
        self.saveButton.clicked.connect(self.saveClasses)

        self.show()

    def setMinValue(self):
        try :
            min = float(self.minValue.text())
            self.layer.colorLegend().setMinValue(min)
        except ValueError:
            pass

    def setMaxValue(self):
        try :
            max = float(self.maxValue.text())
            self.layer.colorLegend().setMaxValue(min)
        except ValueError:
            pass

    def updateMinMax(self):
        min_ = self.layer.dataProvider().minValue()
        max_ = self.layer.dataProvider().maxValue()
        fmt = format_(min_, max_)
        self.minValue.setText(fmt%min_)
        self.maxValue.setText(fmt%max_)

    def logOnOff(self,flag):
        self.layer.colorLegend().setLogScale(self.logCheckBox.isChecked())


    def updateGraduation(self,item=None):
        self.layer.colorLegend().setColorRamp(self.__classColor)
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
                #Avoid values outside range
                if row==0 :
                    max_=1000
                elif row==self.tableWidget.rowCount()-1 :
                    min_=-.09
                classes.append((self.tableWidget.item(row, 0).background().color(), min_, max_))

        self.layer.colorLegend().setGraduation(classes)

    def addGraduation(self,flag=None):
        idx = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(idx+1)
        colorItem = QTableWidgetItem()
        colorItem.setFlags(colorItem.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEditable)
        colorItem.setBackground(QBrush(Qt.red))
        self.tableWidget.setItem(idx, 0, colorItem)
        min_ = self.layer.dataProvider().minValue()
        max_ = self.layer.dataProvider().maxValue()
        fmt = format_(min_, max_)
        self.tableWidget.setItem(idx, 1, QTableWidgetItem(fmt%min_))
        self.tableWidget.setItem(idx, 2, QTableWidgetItem(fmt%max_))

    def editColor(self, row, colum):
        if colum != 0:
            return

        item = self.tableWidget.item(row, 0)
        color = QColorDialog.getColor(item.background().color(), self)
        if color.isValid(): # false on user cancel
            item.setBackground(QBrush(color))

    def removeGraduation(self, flag=None):
        while len(self.tableWidget.selectedRanges()):
            for range_ in self.tableWidget.selectedRanges():
                self.tableWidget.removeRow(range_.bottomRow())
        self.updateGraduation()

    def setFromGraduation(self, graduation):
        self.tableWidget.setRowCount(0)
        min_, max_ = (min([c[1] for c in graduation]), max([c[2] for c in graduation])) if len(graduation) else (0,0)
        # fmt = format_(min_, max_)
        fmt = "%.2e"
        for class_ in graduation:
            idx = self.tableWidget.rowCount()
            self.tableWidget.setRowCount(idx+1)
            colorItem = QTableWidgetItem()
            colorItem.setFlags(colorItem.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEditable)
            colorItem.setBackground(QBrush(class_[0]))
            self.tableWidget.setItem(idx, 0, colorItem)
            self.tableWidget.setItem(idx, 1, QTableWidgetItem(fmt%class_[1]))
            self.tableWidget.setItem(idx, 2, QTableWidgetItem(fmt%class_[2]))

    def setSymbology(self, idx):
        if idx==0:
            self.layer.colorLegend().toggleGraduation(False)
        else:
            self.layer.colorLegend().toggleGraduation(True)



    def changeClassColors(self, f):
        img = QImage(f)
        nbClass = self.tableWidget.rowCount()
        dh = (img.size().height()-1)/(nbClass-1) if nbClass>1 else 0
        x = img.size().width()/2
        for row in range(nbClass):
            self.tableWidget.item(row, 0).setBackground(QBrush(QColor(img.pixel(x, dh*row))))
        self.updateGraduation()

    def classify(self, flag=None):
        self.tableWidget.setRowCount(0)
        nbClass = self.nbClassesSpinBox.value()
        self.layer.colorLegend().setNbClass(nbClass)
        values = self.layer.colorLegend().values(nbClass+1)
        fmt = format_(min(values), max(values))
        for i in range(nbClass):
            self.tableWidget.setRowCount(self.tableWidget.rowCount()+1)
            colorItem = QTableWidgetItem()
            colorItem.setFlags(colorItem.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEditable)
            colorItem.setBackground(QBrush(Qt.red))
            self.tableWidget.setItem(i, 0, colorItem)
            self.tableWidget.setItem(i, 1, QTableWidgetItem(fmt%values[i+1]))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(fmt%values[i]))
        self.changeClassColors(self.__classColor)

    def saveClasses(self, flag=None):
       fileName, __ = QFileDialog.getSaveFileName(None, u"Color scale", QgsProject.instance().fileName(), "Text file (*.txt)")
       if not fileName:
           return #cancelled
       with open(fileName, 'w') as fil:
           for color, min_, max_ in self.layer.colorLegend().graduation():
               fil.write("%s %s %s\n"%(color.name(), str(min_), str(max_)))

    def loadClasses(self, flag=None):
        fileName, __ = QFileDialog.getOpenFileName(None, u"Color scale", QgsProject.instance().fileName(), "Text file (*.txt)")
        if not fileName:
            return #cancelled
        graduation = []
        with open(fileName) as fil:
            for line in fil:
                spl = line.split()
                graduation.append((QColor(spl[0]), float(spl[1]), float(spl[2])))
        self.setFromGraduation(graduation)
        self.updateGraduation()