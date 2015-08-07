# -*- coding: utf-8 -*-

from qgis.core import *

from meshdataprovider import MeshDataProvider

import os
import numpy

class WindDataProvider(MeshDataProvider):

    PROVIDER_KEY = "wind_provider"

    def __init__(self, uri):
        print "WindDataProvider uri", uri
        MeshDataProvider.__init__(self, uri)
        self.__directory = str(QgsDataSourceURI(self.dataSourceUri()).param("directory"))
        print "WindDataProvider directory ", self.__directory
    
    def description(self):
        return "data provider for wind simulation"
    
    def nodeCoord(self):
        coord = []
        with open(os.path.join(self.__directory, 'visu_nodes')) as fil:
            for line in fil:
                xStr, yStr = line.split()
                coord.append((float(xStr), float(yStr), 0))
        return numpy.require(coord, numpy.float32)

    def triangles(self):
        triangles = []
        with open(os.path.join(self.__directory, 'visu_faces')) as fil:
            for line in fil:
                triangles.append(tuple([int(v) for v in line.split()]))
        return numpy.require(triangles, numpy.int32)

    def extent(self):
        vtx = self.nodeCoord()
        return QgsRectangle(numpy.min(vtx[:,0]), numpy.min(vtx[:,1]), \
                numpy.max(vtx[:,0]), numpy.max(vtx[:,1]))


    
