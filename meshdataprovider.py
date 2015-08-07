# -*- coding: utf-8 -*-

from qgis.core import *

from PyQt4.QtCore import *

import numpy

class MeshDataProvider(QgsDataProvider):
    """base class for mesh data providers, please note that this class
    is called in a multithreaded context"""

    PROVIDER_KEY = "mesh_provider"

    dataChanged = pyqtSignal()

    def __init__(self, uri):
        self.__uri = QgsDataSourceURI(uri)
        QgsDataProvider.__init__(self, uri)
        self.__didx = 0
        self.__dates = []

    def setResultColumn(self, columnName):
        self.__uri.setParam('resultColumn', columnName)
        self.dataChanged.emit()

    def resultColumn(self):
        return self.__uri.param('resultColumn')\
                if self.__uri.hasParam('resultColumn')\
                else None

    def name(self):
        return MeshDataProvider.PROVIDER_KEY

    def crs(self):
        assert(self.isValid())
        return QgsCoordinateReferenceSystem(self.__uri.param('crs'))

    def description(self):
        return "mesh data provider"

    def isValid(self):
        return self.__uri.hasParam('crs')

    def nodeCoord(self):
        """return a list of coordinates"""
        return numpy.empty((0,3), dtype=numpy.float32)

    def triangles(self):
        """return a list of triangles described by node indices, 
        watch out: indices start at zero"""
        return numpy.empty((0,3), dtype=numpy.int32)

    def setDates(self, dates):
        """set list of dates in case node values vary with time"""
        self.__dates = dates

    def dates(self):
        """return a list of dates in case node values vary with time"""
        return self.__dates

    def setDate(self, didx):
        """in case the node values can vary"""
        self.__didx = didx
        self.dataChanged.emit()

    def date(self):
        return self.__didx

    def nodeValues(self):
        """return values at nodes"""
        return numpy.empty((0,), dtype=numpy.float32)

    def dataSourceUri(self):
        return self.__uri.uri()

    def readXml(self, node):
        element = node.toElement()
        self.__uri = QgsDataSourceURI(element.attribute("uri"))
        self.__didx = int(element.attribute("dateIndex"))
        return True

    def writeXml(self, node, doc):
        element = node.toElement()
        element.setAttribute("name", self.name())
        element.setAttribute("uri", self.dataSourceUri())
        element.setAttribute("dateIndex", self.__didx)
        return True

