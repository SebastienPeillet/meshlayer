QGis Plugin Layer to render simulation results
==============================================

This python module defines a MeshLayer class that can be loaded as a layer in QGIS.

The user of this class must define a MeshDataProvider suitable for his data format. Two exemples of such a class are provided in [meshlayerdemo](https://github.com/Oslandia/meshlayerdemo).



Requirements
============

The module depends on:
- QGIS > 2.8 along with it's python bindings
- OpenGL python package
- PyQt4 with the submodule QtOpenGL
- numpy

Installation
============

   make install


Credits
=======

This plugin has been developed by Oslandia ( http://www.oslandia.com ).

Oslandia provides support and assistance for QGIS and associated tools, including this plugin.

This work has been funded by CEA ( httl://www.cea.fr ).

License
=======

This work is free software and licenced under the GNU GPL version 2 or any later version.
See LICENSE file.

