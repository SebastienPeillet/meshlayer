# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from OpenGL.GL import *
from OpenGL.GL import shaders

from qgis.core import *

from PyQt5.QtCore import Qt, QSizeF, QSize, QRectF, QThread
from PyQt5.QtGui import QOpenGLContext, QOffscreenSurface
from PyQt5.QtWidgets import QApplication

import numpy
from math import pow, log, ceil, sin, cos, pi

import os
import re
import time
import traceback

from .glmesh import GlMesh, ColorLegend
from .opengl_layer import OpenGlLayer

from .meshdataproviderregistry import MeshDataProviderRegistry
from .meshlayerpropertydialog import MeshLayerPropertyDialog

from .utilities import Timer
from shapely.ops import linemerge
from shapely.geometry import LineString, MultiLineString

class MeshLayerType(QgsPluginLayerType):
    def __init__(self):
        QgsPluginLayerType.__init__(self, MeshLayer.LAYER_TYPE)
        self.__dlg = None

    def createLayer(self):
        return MeshLayer()

        # indicate that we have shown the properties dialog
        return True

    def showLayerProperties(self, layer):
        self.__dlg = MeshLayerPropertyDialog(layer)
        return True


class MeshLayerLegendNode(QgsLayerTreeModelLegendNode):
    def __init__(self, nodeLayer, parent, legend):
        QgsLayerTreeModelLegendNode.__init__(self, nodeLayer, parent)
        self.text = ""
        self.__legend = legend

    def data(self, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.text
        elif role  == Qt.DecorationRole:
            return self.__legend.image()
        else:
            return None

    def draw(self, settings, ctx):
        symbolLabelFont = settings.style(QgsComposerLegendStyle.SymbolLabel).font()
        textHeight = settings.fontHeightCharacterMM(symbolLabelFont, '0');

        im = QgsLayerTreeModelLegendNode.ItemMetrics()
        context = QgsRenderContext()
        context.setScaleFactor( settings.dpi() / 25.4 )
        context.setRendererScale( settings.mapScale() )
        context.setMapToPixel( QgsMapToPixel( 1 / ( settings.mmPerMapUnit() * context.scaleFactor() ) ) )

        sz = self.__legend.sceneRect().size()
        aspect = sz.width() / sz.height()
        h = textHeight*16
        w = aspect*h
        im.symbolSize = QSizeF(w, h)
        im.labeSize =  QSizeF(0, 0)
        if ctx:
            currentXPosition = ctx.point.x()
            currentYCoord = ctx.point.y() #\
                    #+ settings.symbolSize().height()/2;
            ctx.painter.save()
            ctx.painter.translate(currentXPosition, currentYCoord)
            rect = QRectF()
            rect.setSize(QSizeF(im.symbolSize))
            self.__legend.render(ctx.painter, rect)
            #ctx.painter.drawImage(0, 0, self.image)
            ctx.painter.restore()
        return im

class MeshLayerLegend(QgsMapLayerLegend):
    def __init__(self, layer, legend):
        QgsMapLayerLegend.__init__(self, layer)
        self.nodes = []
        self.__legend = legend

    def createLayerTreeModelLegendNodes(self, nodeLayer):
        node = MeshLayerLegendNode(nodeLayer, self, self.__legend)
        self.nodes = [node]
        return self.nodes

class MeshLayer(OpenGlLayer):
    """This class must be instanciated in the main thread"""

    LAYER_TYPE="mesh_layer"

    def __init__(self, uri=None, name=None, providerKey=None):
        """optional parameters are here only in the case the layer is created from
        .gqs file, without them the layer is invalid"""
        OpenGlLayer.__init__(self, MeshLayer.LAYER_TYPE, name)
        self.__meshDataProvider = None
        self.__legend = None
        if uri:
            self.__load(MeshDataProviderRegistry.instance().provider(providerKey, uri))
        self.__destCRS = None
        self.__timing = False
        self.willBeDeleted.connect(self.clean_texture)

    def clean_texture(self):
        self.__glMesh._GlMesh__gl_ctx.makeCurrent(self.__glMesh._GlMesh__gl_surface)
        self._MeshLayer__glMesh._GlMesh__legend.tex.destroy()

    def setColorLegend(self, legend):
        if self.__legend:
            self.__legend.symbologyChanged.disconnect(self.__symbologyChanged)
        self.__legend = legend
        self.__glMesh.setLegend(self.__legend)
        self.__legend.symbologyChanged.connect(self.__symbologyChanged)

    def colorLegend(self):
        return self.__legend

    def __load(self, meshDataProvider):
        self.setCrs(meshDataProvider.crs())
        self.setExtent(meshDataProvider.extent())
        self.__meshDataProvider = meshDataProvider
        self.__meshDataProvider.dataChanged.connect(self.triggerRepaint)

        self.__legend = ColorLegend()
        self.__legend.setParent(self)
        self.__legend.symbologyChanged.connect(self.__symbologyChanged)
        assert QApplication.instance().thread() == QThread.currentThread()
        self.__glMesh = GlMesh(
                meshDataProvider.nodeCoord(),
                meshDataProvider.triangles(),
                self.__legend
                )
        self.setValid(self.__meshDataProvider.isValid())
        self.__symbologyChanged()

    def __symbologyChanged(self):
        self.__layerLegend = MeshLayerLegend(self, self.__legend)
        self.setLegend(self.__layerLegend)
        self.legendChanged.emit()
        self.triggerRepaint()

    def readXml(self, node, rwcontext):
        element = node.toElement()
        provider = node.namedItem("meshDataProvider").toElement()
        meshDataProvider = MeshDataProviderRegistry.instance().provider(
                provider.attribute("name"), provider.attribute("uri"))
        if not meshDataProvider.readXml(node.namedItem("meshDataProvider"), rwcontext):
            return False

        self.__load(meshDataProvider)

        if not self.__legend.readXml(node.namedItem("colorLegend"), rwcontext):
            return False
        return True

    def writeXml(self, node, doc, rwcontext):
        """write plugin layer type to project (essential to be read from project)"""
        element = node.toElement()
        element.setAttribute("debug", "just a test")
        element.setAttribute("type", "plugin")
        element.setAttribute("name", MeshLayer.LAYER_TYPE)

        dataProvider = doc.createElement("meshDataProvider")
        if not self.__meshDataProvider.writeXml(dataProvider, doc, rwcontext):
            return False
        element.appendChild(dataProvider)

        colorLegend = doc.createElement("colorLegend")
        if not self.__legend.writeXml(colorLegend, doc, rwcontext):
            return False
        element.appendChild(colorLegend)
        return True

    def dataProvider(self):
        return self.__meshDataProvider

    def image(self, rendererContext, size):
        timer = Timer() if self.__timing else None
        transform = rendererContext.coordinateTransform()
        ext = rendererContext.extent()
        mapToPixel = rendererContext.mapToPixel()

        size = QSize((ext.xMaximum()-ext.xMinimum())/mapToPixel.mapUnitsPerPixel(),
                     (ext.yMaximum()-ext.yMinimum())/mapToPixel.mapUnitsPerPixel()) \
                             if abs(mapToPixel.mapRotation()) < .01 else size

        if transform:
            ext = transform.transform(ext)
            if transform.destinationCrs() != self.__destCRS:
                self.__destCRS = transform.destinationCrs()
                vtx = numpy.array(self.__meshDataProvider.nodeCoord())
                def transf(x):
                    p = transform.transform(x[0], x[1])
                    return [p.x(), p.y(), x[2]]
                vtx = numpy.apply_along_axis(transf, 1, vtx)
                self.__glMesh.resetCoord(vtx)

        self.__glMesh.setColorPerElement(self.__meshDataProvider.valueAtElement())
        img = self.__glMesh.image(
                self.__meshDataProvider.elementValues()
                   if self.__meshDataProvider.valueAtElement() else
                   self.__meshDataProvider.nodeValues(),
                size,
                (.5*(ext.xMinimum() + ext.xMaximum()),
                 .5*(ext.yMinimum() + ext.yMaximum())),
                (mapToPixel.mapUnitsPerPixel(),
                 mapToPixel.mapUnitsPerPixel()),
                 mapToPixel.mapRotation())
        if self.__timing:
            # fix_print_with_import
            print(timer.reset("render 2D mesh image"))
        return img

    def isovalues(self, values):
        """return a list of multilinestring, one for each value in values"""
        idx = self.__meshDataProvider.triangles()
        vtx = self.__meshDataProvider.nodeCoord()
        lines = []
        for value in values:
            lines.append([])
            if self.__meshDataProvider.valueAtElement():
                val = self.__meshDataProvider.elementValues() - float(value)
            else:
                val = self.__meshDataProvider.nodeValues() - float(value)

            # we filter triangles in which the value is negative on at least
            # one node and positive on at leat one node
            filtered = idx[numpy.logical_or(
                val[idx[:, 0]]*val[idx[:, 1]] <= 0,
                val[idx[:, 0]]*val[idx[:, 2]] <= 0
                ).reshape((-1,))]
            # create line segments
            for tri in filtered:
                line = []
                # the edges are sorted to avoid interpolation error
                for edge in [sorted([tri[0], tri[1]]),
                             sorted([tri[1], tri[2]]),
                             sorted([tri[2], tri[0]])]:
                    if val[edge[0]]*val[edge[1]] <= 0:
                        if val[edge[1]] != val[edge[0]]:
                            alpha = -val[edge[0]]/(val[edge[1]] - val[edge[0]])
                            assert alpha >= 0 and alpha <= 1
                            line.append(tuple((1-alpha)*vtx[edge[0]] + alpha*vtx[edge[1]]))
                        else: # the edge is part of the isoline
                            # fix_print_with_import
                            print("meshlayer:isovalues: ", value, edge[0], edge[1], val[edge[0]], val[edge[1]], vtx[edge[0]], vtx[edge[1]])
                            line.append(tuple(vtx[edge[0]]))
                            line.append(tuple(vtx[edge[1]]))
                # avoiding loops
                l = list(set(line))
                if len(l) > 1:
                    lines[-1].append(l)
            if len(lines[-1]):
                m = linemerge([LineString(l) for l in lines[-1]])
                if isinstance(m, LineString):
                    lines[-1] = [list(m.coords)]
                else:
                    assert(isinstance(m, MultiLineString))
                    lines[-1] = [list(l.coords) for l in m]
        return lines


if __name__ == "__main__":
    import sys
    from winddataprovider import WindDataProvider

    #app = QgsApplication(sys.argv, False)
    QgsApplication.setPrefixPath('/usr/local', True)
    QgsApplication.initQgis()

    MeshDataProviderRegistry.instance().addDataProviderType("wind", WindDataProvider)

    assert len(sys.argv) >= 2



    uri = 'directory='+sys.argv[1]+' crs=epsg:2154'
    provider = MeshDataProviderRegistry.instance().provider("wind", uri)
    # fix_print_with_import
    print(provider)
    # fix_print_with_import
    print(provider.crs())
    # fix_print_with_import
    print(provider.isValid())
    # fix_print_with_import
    print("####################")




    layer = MeshLayer(uri, 'test_layer', "wind")
    layer.dataProvider().setDate(int(sys.argv[2]))
    # fix_print_with_import
    print(layer.dataProvider().dataSourceUri())
    # fix_print_with_import
    print(layer.dataProvider().nodeValues())

    exit(0)
    # the rest should be ported to a specific test


    start = time.time()
    values = [float(v) for v in sys.argv[4:]]
    lines = layer.isovalues(values)
    # fix_print_with_import
    print("total time ", time.time() - start)
    isolines = QgsVectorLayer("MultiLineString?crs=epsg:27572&field=value:double", "isovalues", "memory")
    pr = isolines.dataProvider()
    features = []
    for i, mutilineline in enumerate(lines):
        features.append(QgsFeature())
        features[-1].setGeometry(QgsGeometry.fromMultiPolyline([[QgsPoint(point[0], point[1]) \
                for point in line] for line in mutilineline]))
        features[-1].setAttributes([values[i]])
    pr.addFeatures(features)

    QgsVectorFileWriter.writeAsVectorFormat(isolines, "isovalues.shp", "isovalues", None, "ESRI Shapefile")



