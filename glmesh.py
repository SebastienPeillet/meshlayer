# -*- coding: utf-8 -*-

from OpenGL.GL import *
from OpenGL.GL import shaders

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat, QGLContext

import numpy
from math import log, ceil, exp

from utilities import complete_filename, multiplier

def roundUpSize(size):
    """return size roudup to the nearest power of 2"""
    return QSize(pow(2, ceil(log(size.width())/log(2))),
                 pow(2, ceil(log(size.height())/log(2))))

def compute_matrix(extent):
    """The openGL display is mapped on [-1,1] on x and y
    we want the matrix that transform the coordinates in extend
    to openGL.
    """
    [xMin, yMin, xMax, yMax] = extent
    sx, sy = 2. / (xMax-xMin), 2. / (yMax - yMin)
    dx, dy = -.5 * (xMin + xMax), -.5 * (yMin + yMax)
    return numpy.require([[sx, 0., 0., 0.],
                       [0., sy, 0., 0.],
                       [0., 0., 1., 0.],
                       [dx*sx, dy*sy, 0., 1.]], numpy.float32, 'F')

class ColorLegend(QGraphicsScene):
    """A legend provides the symbology for a layer.
    The legend is responsible for the translation of values into color.
    For performace and flexibility reasons the legend provide shader 
    functions that will take a value and return a color.
    """

    symbologyChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        QGraphicsScene.__init__(self, parent)
        self.__minValue = 0
        self.__maxValue = 1
        self.__transparency = 0
        self.__uniformLocations = {}
        self.__title = "no title"
        self.__colorRampFile = ColorLegend.availableRamps()[u"Bleu - Rouge"]
        self.__colorRamp = QImage(self.__colorRampFile)
        self.__units = ""
        self.__scale = "linear"

    @staticmethod
    def availableRamps():
        return {u"Bleu - Rouge": complete_filename('images/ramp_blue_red_continuous.svg'),
                u"Bleu - Mauve": complete_filename('images/ramp_blue_purple_discrete.png'),
                u"Brûlé": complete_filename('images/ramp_burn_continuous.svg')}
     
    def _fragmentShader(self):
        """Return a string containing the definition of the GLSL pixel shader 
            vec4 pixelColor(float value)
        This may contain global shader variables and should therefore
        be included in the fragment shader between the global variables
        definition and the main() declaration.
        Note that:
            varying float value
        must be defined by the vertex shader
        """
        return """
            varying float value;
            varying vec3 normal;
            varying vec4 ecPos;
            uniform float transparency;
            uniform float minValue;
            uniform float maxValue;
            uniform bool logscale;
            uniform bool withNormals;
            uniform sampler2D tex;
            vec4 pixelColor(float value)
            {
                float normalizedValue = clamp(
                    logscale
                    ? (log(value)-log(minValue))/(log(maxValue)-log(minValue))
                    : (value-minValue)/(maxValue-minValue)
                    , 0.f, 1.f);
                return texture2D(tex, vec2(.5f, normalizedValue));
            }
            void main()
            {
                vec3 lightDir = vec3(gl_LightSource[0].position-ecPos);
                if (withNormals){
                    gl_FragColor.rgb = pixelColor(value).rgb *
                        max(dot(normalize(normal), normalize(lightDir)),0.0);
                    gl_FragColor.a = 1.;
                }
                else {
                    gl_FragColor = pixelColor(value)*(1.-transparency);
                }
            }
            """

    def values(self, nbValues=7):
        """Return list of numerical values in legend"""
        values = []
        for i in range(nbValues):
            alpha = 1. - float(i)/(nbValues-1)
            # inverse of the scale function in shader
            value = exp(alpha*(log(self.__maxValue)-log(self.__minValue)) + log(self.__minValue))\
                    if self.__scale == "log" else\
                    self.__minValue + alpha*(self.__maxValue-self.__minValue)
            values.append(value)
        return values

    def image(self):
        """Return an image representing the legend"""
        self.__refresh()
        sz = self.sceneRect().size().toSize()
        img = QImage(
                sz.width(), 
                sz.height(), 
                self.__colorRamp.format())
        img.fill(Qt.transparent)
        with QPainter(img) as p:
            self.render(p)
        return img

    #def render(self, painter, target = QRectF(), source = QRectF(), aspectRatioMode = Qt.KeepAspectRatio):
    #    self.__refresh()
    #    QGraphicsScene.render(self, painter, target, source, aspectRatioMode)

    def __refresh(self):
        """refresh the legend"""
        self.clear()
        # find the closest appropriate power of the max values
        mult, multText = multiplier(self.__maxValue)

        values = self.values()

        textHeight = QFontMetrics(QFont()).height()
        legendWidth = textHeight*20
        barWidth = textHeight
        barHeight = textHeight*len(values)*1.2
        barPosition = QPoint(0, 2.75*textHeight if multText else 1.75*textHeight)
        headerPosition = QPoint(0,0)
        bottomSpace = 15
        tickSpacing = float(barHeight)/(len(values)-1)

        text = self.addText(self.__title+" ["+self.__units+"]")
        text.setPos(headerPosition)
        if multText:
            text = self.addText(multText)
            text.setPos(headerPosition+QPoint(0,textHeight))
            
        img = self.addPixmap(QPixmap.fromImage(self.__colorRamp.scaled(barWidth, barHeight)))
        img.setPos(barPosition)
        for i, value in enumerate(values):
            text = self.addText("%4.5f"%(float("%.2g"%(value/mult))))
            text.setPos(barPosition+QPoint(barWidth+5, int(i*tickSpacing) - .75*textHeight))
            self.addLine(QLineF(barPosition+QPoint(barWidth, int(i*tickSpacing)), barPosition+QPoint(barWidth+4, int(i*tickSpacing))))


    def setLogScale(self, trueOrFalse=True):
        self.__scale = "log" if trueOrFalse else "linear"
        self.__checkValues()
        self.__refresh()
        self.symbologyChanged.emit()

    def hasLogScale(self):
        return self.__scale == "log"

    def setTitle(self, text):
        self.__title = text
        self.__refresh()
        self.symbologyChanged.emit()

    def title(self):
        return self.__title
    
    def setUnits(self, text):
        """set the units to display in legend"""
        self.__units = text
        self.__refresh()
        self.symbologyChanged.emit()

    def units(self):
        return self.__units

    #def setMinMaxConverter(self, converter):
    #    """The converter provides the methods to() that
    #    convert the min and max values to .
    #    The converter also provides the displayText() method."""
    #    self.__unitsConverter = converter
    #    self.symbologyChanged.emit()

    def __checkValues(self):
        # in case of log scales, the min and max must be positive
        if self.__scale == "log":
            self.__minValue = max(self.__minValue, 1e-32)
            self.__maxValue = max(self.__maxValue, 1e-32)

    def setMinValue(self, value):
        try:
            self.__minValue = float(value)
            self.__checkValues()
            self.__refresh()
            self.symbologyChanged.emit()
        except ValueError:
            return

    def setMaxValue(self, value):
        try:
            self.__maxValue = float(value)
            self.__checkValues()
            self.__refresh()
            self.symbologyChanged.emit()
        except ValueError:
            return

    def setTransparencyPercent(self, value):
        self.setTransparency(value/100.)

    def setTransparency(self, value):
        try:
            self.__transparency = float(value)
            self.__refresh()
            self.symbologyChanged.emit()
        except ValueError:
            return

    def setColorRamp(self, rampImageFile):
        self.__colorRampFile = rampImageFile
        self.__colorRamp = QImage(rampImageFile)
        self.__refresh()
        self.symbologyChanged.emit()

    def transparencyPercent(self):
        return int(self.__transparency*100)

    def minValue(self):
        return self.__minValue

    def maxValue(self):
        return self.__maxValue

    def colorRamp(self):
        return self.__colorRampFile

    def _setUniformsLocation(self, shaders_):
        """Should be called once the shaders are compiled"""
        for name in ["transparency", "minValue", "maxValue", "tex", "logscale", "withNormals"]:
            self.__uniformLocations[name] = glGetUniformLocation(shaders_, name)

    def _setUniforms(self, glcontext, withNormals=False):
        """Should be called before the draw"""
        glUniform1f(self.__uniformLocations["transparency"], self.__transparency)
        glUniform1f(self.__uniformLocations["minValue"], self.__minValue)
        glUniform1f(self.__uniformLocations["maxValue"], self.__maxValue)
        glUniform1f(self.__uniformLocations["logscale"], int(self.hasLogScale()))
        glUniform1f(self.__uniformLocations["withNormals"], int(withNormals))

        # texture
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, glcontext.bindTexture(self.__colorRamp))
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_MIRRORED_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT)

    def readXml(self, node):
        element = node.toElement()
        self.setTitle(element.attribute("title"))
        self.setMinValue(element.attribute("minValue"))
        self.setMaxValue(element.attribute("maxValue"))
        self.setTransparency(element.attribute("transparency"))
        self.setColorRamp(element.attribute("colorRampFile"))
        self.setUnits(element.attribute("units"))
        self.setLogScale(element.attribute("scale")=="log")
        self.__refresh()
        return True

    def writeXml(self, node, doc):
        element = node.toElement()
        element.setAttribute("title", self.__title)
        element.setAttribute("minValue", str(self.__minValue))
        element.setAttribute("maxValue", str(self.__maxValue))
        element.setAttribute("transparency", str(self.__transparency))
        element.setAttribute("colorRampFile", self.__colorRampFile)
        element.setAttribute("units", self.__units)
        element.setAttribute("scale", self.__scale)
        return True

class GlMesh(QObject):
    """This class provides basic function to render results on a 2D mesh.
    The class must be instanciated in the main thread, but the draw function
    can be called in another thread.
    This class encapsulates the transformation between an extend and an image size.
    """
    #__contextMutex = QMutex()

    __sizeChangeRequested = pyqtSignal(QSize)

    def __init__(self, vtx, idx, legend):
        QObject.__init__(self)
        self.__vtx = numpy.require(vtx, numpy.float32, 'F')
        self.__idx = numpy.require(idx, numpy.int32, 'F')
        self.__pixBuf = None
        self.__sizeChangeRequested.connect(self.__resize)
        self.__sizeChangedCondition = QWaitCondition()
        self.__sizeChangedMutex = QMutex()
        self.__sizeChanged = False
        self.__legend = legend

        #self.__previousLegend = legend

    #def setLegend(self, legend):
    #    self.__legend = legend

    def __resize(self, roundupImageSize):
        # QGLPixelBuffer size must be power of 2
        assert roundupImageSize == roundUpSize(roundupImageSize)

        # force alpha format, it should be the default, 
        # but isn't all the time (uninitialized)
        fmt = QGLFormat()
        fmt.setAlpha(True)

        self.__pixBuf = QGLPixelBuffer(roundupImageSize, fmt)
        assert self.__pixBuf.format().alpha()
        #GlMesh.__contextMutex.lock()
        self.__pixBuf.makeCurrent()
        self.__pixBuf.bindToDynamicTexture(self.__pixBuf.generateDynamicTexture())
        vertex_shader = shaders.compileShader("""
            varying float value;
            varying vec3 normal;
            varying vec4 ecPos;
            void main()
            {
                ecPos = gl_ModelViewMatrix * gl_Vertex;
                normal = normalize(gl_NormalMatrix * gl_Normal);
                value = gl_MultiTexCoord0.st.x;
                gl_Position = ftransform();
            }
            """, GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader(
            self.__legend._fragmentShader(), GL_FRAGMENT_SHADER)

        self.__shaders = shaders.compileProgram(vertex_shader, fragment_shader)
        self.__legend._setUniformsLocation(self.__shaders)
        self.__pixBuf.doneCurrent()
        #GlMesh.__contextMutex.unlock()

        self.__sizeChangedMutex.lock()
        self.__sizeChanged = True
        self.__sizeChangedMutex.unlock()
        self.__sizeChangedCondition.wakeOne();
    
    def image(self, imageSize, extent, values):
        """Return the rendered image of a given size for values defined at each vertex.
        Values are normalized using valueRange = (minValue, maxValue).
        transparency is in the range [0,1]"""

        if not len(values):
            img = QImage(imageSize)
            img.fill(Qt.transparent)
            return img

        roundupSz = roundUpSize(imageSize)
        if not self.__pixBuf \
                or roundupSz.width() != self.__pixBuf.size().width() \
                or roundupSz.height() != self.__pixBuf.size().height():
                #or self.__legend != self.__previousLegend:
            # we need to call the main thread for a change of the
            # pixel buffer and wait for the change to happen
            if QApplication.instance().thread() == QThread.currentThread():
                self.__resize(roundupSz)
            else:
                self.__sizeChangedMutex.lock()
                self.__sizeChanged = False
                self.__sizeChangeRequested.emit(roundupSz)
                while not self.__sizeChanged:
                    self.__sizeChangedCondition.wait(self.__sizeChangedMutex);
                self.__sizeChangedMutex.unlock()
            #self.__previousLegend = self.__legend

        val = numpy.require(values, numpy.float32) \
                if not isinstance(values, numpy.ndarray)\
                else values

        #GlMesh.__contextMutex.lock()
        self.__pixBuf.makeCurrent()

        glClearColor(0., 0., 0., 0.)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnable(GL_TEXTURE_2D)

        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # compute the transformation
        ratio = (float(roundupSz.width()-imageSize.width())/imageSize.width(),
                 float(roundupSz.height()-imageSize.height())/imageSize.height())
        roundupExtent = (extent[0],
                         extent[1] - ratio[1]*(extent[3]-extent[1]),
                         extent[2] + ratio[0]*(extent[2]-extent[0]),
                         extent[3])

        glMultMatrixf(compute_matrix(roundupExtent))

        glUseProgram(self.__shaders)

        self.__legend._setUniforms(self.__pixBuf)

        glVertexPointerf(self.__vtx)
        glTexCoordPointer(1, GL_FLOAT, 0, val)
        glDrawElementsui(GL_TRIANGLES, self.__idx)

        img = self.__pixBuf.toImage()
        self.__pixBuf.doneCurrent()
        #GlMesh.__contextMutex.unlock()

        return img.copy( 0, 0, imageSize.width(), imageSize.height()) 

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    legend = ColorLegend()
    legend.setMinValue(.01)
    legend.setMaxValue(33)
    legend.setTransparencyPercent(50)
    mesh = GlMesh(((0,0,0),(1,0,0),(1,1,0),(1,2,0),(0,2,0),(0,1,0)),
            ((0,1,2),(0,2,5),(5,2,3),(5,3,4)), legend)
    img = mesh.image( 
            QSize(800,600),
            (-4, -3, 4, 3),
            (.01, .01, .5*33.01, 33, 33,  .5*33.01))
    img.save('/tmp/test_gl_mesh.png')
    img = QImage('/tmp/test_gl_mesh.png')
    ref = QImage(complete_filename('test_data/test_gl_mesh.png'))
    assert img == ref

    legend.setLogScale(True)
    img = mesh.image( 
            QSize(800,600),
            (-4, -3, 4, 3),
            (.01, .01, .1, 33, 33, .1))
    img.save('/tmp/test_gl_mesh_log.png')

    #legend.setMinValue(.01)
    #legend.setMaxValue(33000)
    legend.image().save("/tmp/test_gl_mesh_legend.png")


