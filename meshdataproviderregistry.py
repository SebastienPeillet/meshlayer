# -*- coding: utf-8 -*-

class MeshDataProviderRegistry(object):
    """a singleton to register MeshDataProviders"""

    __INSTANCE = None

    class __MeshDataProviderRegistry(object):
        def __init__(self):
            self.__providers = {}

        def provider(self, providerKey, dataSource):
            """returns a mesh provider instance"""
            return self.__providers[providerKey](dataSource)

        def addDataProviderType(self, providerKey, type_):
            """add provider type to registry"""
            self.__providers[providerKey] = type_

    @staticmethod 
    def instance():
        """returns the singleton instance"""
        if not MeshDataProviderRegistry.__INSTANCE:
            MeshDataProviderRegistry.__INSTANCE = \
                    MeshDataProviderRegistry.__MeshDataProviderRegistry()
        return MeshDataProviderRegistry.__INSTANCE
    
