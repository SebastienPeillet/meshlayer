# -*- coding: utf-8 -*-

class MeshDataProviderRegistry(object):
    """a singleton to register MeshDataProviders"""

    __INSTANCE = None

    class __MeshDataProviderRegistry(object):
        def __init__(self):
            self.__providers = {}

        def provider(self, providerKey, dataSource):
            """returns a mesh provider instance"""
            if not providerKey:
                raise RuntimeError("Missing providerKey")

            prvdr = self.__providers[providerKey](dataSource)

            if not prvdr:
                raise RuntimeError("Cannot create provider "+providerKey+" from uri:"+dataSource)
            if not prvdr.isValid():
                raise RuntimeError("Invalid provider "+providerKey+" from uri:"+dataSource)

            return prvdr

        def addDataProviderType(self, providerKey, type_):
            """add provider type to registry"""
            self.__providers[providerKey] = type_

        def removeDataProviderType(self, providerKey):
            """remove provider from registry"""

    @staticmethod
    def instance():
        """returns the singleton instance"""
        if not MeshDataProviderRegistry.__INSTANCE:
            MeshDataProviderRegistry.__INSTANCE = \
                    MeshDataProviderRegistry.__MeshDataProviderRegistry()
        return MeshDataProviderRegistry.__INSTANCE
