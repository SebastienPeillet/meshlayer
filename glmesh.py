# -*- coding: utf-8 -*-

from OpenGL.GL import *
from OpenGL.GL import shaders

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat, QGLContext

import numpy
from math import log, ceil, exp

from utilities import complete_filename

def roundUpSize(size):
    """return size roudup to the nearest power of 2"""
    return QSize(pow(2, ceil(log(size.width())/log(2))),
                 pow(2, ceil(log(size.height())/log(2))))

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
        grp = self.createItems()
        for item in grp.childItems():
            self.addItem(item);

    def createItems(self):
        """returns a QGraphicsItemGroup that contains legend items"""
        grp = QGraphicsItemGroup()
        values = self.values()
        format_ = "%.2e"
        if self.__maxValue < 10000 and self.__minValue > 0.01:
            format_ = "%.1f"

        textHeight = QFontMetrics(QFont()).height()
        legendWidth = textHeight*20
        barWidth = textHeight
        barHeight = textHeight*len(values)*1.2
        barPosition = QPoint(0, 1.75*textHeight)
        headerPosition = QPoint(0,0)
        bottomSpace = 15
        tickSpacing = float(barHeight)/(len(values)-1)

        text = QGraphicsTextItem(self.__title+" ["+self.__units+"]")
        grp.addToGroup(text)
        text.setPos(headerPosition)
        img = QGraphicsPixmapItem(QPixmap.fromImage(self.__colorRamp.scaled(barWidth, barHeight)))
        grp.addToGroup(img)
        img.setPos(barPosition)
        for i, value in enumerate(values):
            text = QGraphicsTextItem(format_%(value))
            grp.addToGroup(text)
            text.setPos(barPosition+QPoint(barWidth+5, int(i*tickSpacing) - .75*textHeight))
            line = QGraphicsLineItem(QLineF(barPosition+QPoint(barWidth, int(i*tickSpacing)), barPosition+QPoint(barWidth+4, int(i*tickSpacing))))
            grp.addToGroup(line)
        return grp

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
    def __init__(self, vtx, idx, legend):
        QObject.__init__(self)
        self.__vtx = numpy.require(vtx, numpy.float32, 'F')
        self.__idx = numpy.require(idx, numpy.int32, 'F')
        self.__pixBuf = None
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
    
    def resetCoord(self, vtx):
        self.__vtx = numpy.require(vtx, numpy.float32, 'F')


    def image(self, values, imageSize, center, mapUnitsPerPixel, rotation=0):
        """Return the rendered image of a given size for values defined at each vertex.
        Values are normalized using valueRange = (minValue, maxValue).
        transparency is in the range [0,1]"""

        if QApplication.instance().thread() != QThread.currentThread():
            raise RuntimeError("trying to use gl draw calls in a thread")

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
            self.__resize(roundupSz)

        val = numpy.require(values, numpy.float32) \
                if not isinstance(values, numpy.ndarray)\
                else values

        self.__pixBuf.makeCurrent()

        glClearColor(0., 0., 0., 0.)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnable(GL_TEXTURE_2D)

        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # scale
        glScalef(2./(roundupSz.width()*mapUnitsPerPixel[0]), 
                 2./(roundupSz.height()*mapUnitsPerPixel[1]),
                 1.)
        # rotate
        glRotatef(-rotation, 0, 0, 1)

        # translate
        glTranslatef(-center[0],
                     -center[1],
                     0)

        glUseProgram(self.__shaders)

        self.__legend._setUniforms(self.__pixBuf)

        glVertexPointerf(self.__vtx)
        glTexCoordPointer(1, GL_FLOAT, 0, val)
        glDrawElementsui(GL_TRIANGLES, self.__idx)

        img = self.__pixBuf.toImage()
        self.__pixBuf.doneCurrent()
        #GlMesh.__contextMutex.unlock()

        return img.copy( .5*(roundupSz.width()-imageSize.width()), 
                         .5*(roundupSz.height()-imageSize.height()), 
                         imageSize.width(), imageSize.height()) 



bgra_dtype = numpy.dtype({'b': (numpy.uint8, 0),
						  'g': (numpy.uint8, 1),
						  'r': (numpy.uint8, 2),
						  'a': (numpy.uint8, 3)})

def qimage2numpy(qimage, dtype = 'array'):
	"""Convert QImage to numpy.ndarray.  The dtype defaults to uint8
	for QImage.Format_Indexed8 or `bgra_dtype` (i.e. a record array)
	for 32bit color images.  You can pass a different dtype to use, or
	'array' to get a 3D uint8 array for color images."""
	result_shape = (qimage.height(), qimage.width())
	temp_shape = (qimage.height(),
				  qimage.bytesPerLine() * 8 / qimage.depth())
	if qimage.format() in (QImage.Format_ARGB32_Premultiplied,
						   QImage.Format_ARGB32,
						   QImage.Format_RGB32):
		if dtype == 'rec':
			dtype = bgra_dtype
		elif dtype == 'array':
			dtype = numpy.uint8
			result_shape += (4, )
			temp_shape += (4, )
	elif qimage.format() == QImage.Format_Indexed8:
		dtype = numpy.uint8
	else:
		raise ValueError("qimage2numpy only supports 32bit and 8bit images")
	# FIXME: raise error if alignment does not match
	buf = qimage.bits().asstring(qimage.numBytes())
	result = numpy.frombuffer(buf, dtype).reshape(temp_shape)
	if result_shape != temp_shape:
		result = result[:,:result_shape[1]]
	if qimage.format() == QImage.Format_RGB32 and dtype == numpy.uint8:
		result = result[...,:3]
	return result

def numpy2qimage(array):
	if numpy.ndim(array) == 2:
		return gray2qimage(array)
	elif numpy.ndim(array) == 3:
		return rgb2qimage(array)
	raise ValueError("can only convert 2D or 3D arrays")

def gray2qimage(gray):
	"""Convert the 2D numpy array `gray` into a 8-bit QImage with a gray
	colormap.  The first dimension represents the vertical image axis.

	ATTENTION: This QImage carries an attribute `ndimage` with a
	reference to the underlying numpy array that holds the data. On
	Windows, the conversion into a QPixmap does not copy the data, so
	that you have to take care that the QImage does not get garbage
	collected (otherwise PyQt will throw away the wrapper, effectively
	freeing the underlying memory - boom!)."""
	if len(gray.shape) != 2:
		raise ValueError("gray2QImage can only convert 2D arrays")

	gray = numpy.require(gray, numpy.uint8, 'C')

	h, w = gray.shape

	result = QImage(gray.data, w, h, QImage.Format_Indexed8)
	result.ndarray = gray
	for i in range(256):
		result.setColor(i, QColor(i, i, i).rgb())
	return result

def rgb2qimage(rgb):
	"""Convert the 3D numpy array `rgb` into a 32-bit QImage.  `rgb` must
	have three dimensions with the vertical, horizontal and RGB image axes.

	ATTENTION: This QImage carries an attribute `ndimage` with a
	reference to the underlying numpy array that holds the data. On
	Windows, the conversion into a QPixmap does not copy the data, so
	that you have to take care that the QImage does not get garbage
	collected (otherwise PyQt will throw away the wrapper, effectively
	freeing the underlying memory - boom!)."""
	if len(rgb.shape) != 3:
		raise ValueError("rgb2QImage can only convert 3D arrays")
	if rgb.shape[2] not in (3, 4):
		raise ValueError("rgb2QImage can expects the last dimension to contain exactly three (R,G,B) or four (R,G,B,A) channels")

	h, w, channels = rgb.shape

	# Qt expects 32bit BGRA data for color images:
	bgra = numpy.empty((h, w, 4), numpy.uint8, 'C')
	bgra[...,0] = rgb[...,2]
	bgra[...,1] = rgb[...,1]
	bgra[...,2] = rgb[...,0]
	if rgb.shape[2] == 3:
		bgra[...,3].fill(255)
		fmt = QImage.Format_RGB32
	else:
		bgra[...,3] = rgb[...,3]
		fmt = QImage.Format_ARGB32

	result = QImage(bgra.data, w, h, fmt)
	result.ndarray = bgra
	return result

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
    rot = QTransform()
    rot.rotate(180)
    ref = QImage(complete_filename('test_data/test_gl_mesh.png'))#.transformed(rot)

    diff = qimage2numpy(img)[:,:,0:3] - qimage2numpy(ref)[:,:,0:3]
    numpy2qimage(diff).save("/tmp/diff.png")

    assert numpy.linalg.norm(diff) < 200

    legend.setLogScale(True)
    img = mesh.image( 
            QSize(800,600),
            (-4, -3, 4, 3),
            (.01, .01, .1, 33, 33, .1))
    img.save('/tmp/test_gl_mesh_log.png')

    #legend.setMinValue(.01)
    #legend.setMaxValue(33000)
    legend.image().save("/tmp/test_gl_mesh_legend.png")


