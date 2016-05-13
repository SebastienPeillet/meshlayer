# coding: utf-8

from OpenGL.GL import *
from OpenGL.GL import shaders

from qgis.core import *

from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class OpenGlLayer(QgsPluginLayer):
    """Base class to encapsulate the tricks to create OpenGL layers
    /!\ the layer is drwn in main thread due to current Qt limitations
    care must be taken not to stall the event loop while requesting
    a render job since since the rendering thread signal will not be
    passed to the main thread.

    Child class must implement the image method
    """

    __msg = pyqtSignal(str)
    __drawException = pyqtSignal(str)
    __imageChangeRequested = pyqtSignal()

    def __print(self, msg):
        print msg

    def __raise(self, err):
        raise Exception(err)

    def __init__(self, type_ ="opengl_layer", name=None):
        QgsPluginLayer.__init__(self, type_, name)
        self.__imageChangedMutex = QMutex()
        self.__imageChangeRequested.connect(self.__drawInMainThread)
        self.__img = None
        self.__rendererContext = None
        self.__drawException.connect(self.__raise)
        self.__msg.connect(self.__print)

    def image(self, rendererContext):
        """This is the function that should be overwritten
        the rendererContext does not have a painter and an
        image must be returned instead
        """
        print "default image, we should not be here"
        return QImage(QSize(512,512))

    def __drawInMainThread(self):
        self.__imageChangedMutex.lock()
        self.__img = self.image(self.__rendererContext)
        self.__imageChangedMutex.unlock()

    def draw(self, rendererContext):
        """This function is called by the rendering thread. 
        GlMesh must be created in the main thread."""
        try:
            # /!\ DO NOT PRIN IN THREAD
            painter = rendererContext.painter()
            self.__imageChangedMutex.lock()
            self.__rendererContext = QgsRenderContext(rendererContext)
            self.__rendererContext.setPainter(None)
            self.__img = None
            self.__imageChangedMutex.unlock()

            if QApplication.instance().thread() != QThread.currentThread():
                self.__imageChangeRequested.emit()
                while not self.__img and not rendererContext.renderingStopped():
                    # active wait to avoid deadlocking if envent loop is stopped
                    # this happens when a render job is cancellled
                    QThread.msleep(1)

                if not rendererContext.renderingStopped():
                    painter.drawImage(0, 0, self.__img)
            else:
                self.__drawInMainThread()
                painter.drawImage(0, 0, self.__img)

            return True
        except Exception as e:
            # since we are in a thread, we must re-raise the exception
            self.__drawException.emit(traceback.format_exc())
            return False

