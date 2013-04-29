#! /usr/bin/python
#coding=utf-8
'''
Created on 29.04.2013
Реестр служб. Синглетон.
@author: licvidator
'''


class ServiceRegistry(object):
    '''
    Тут будут храниться все ссылки на инициализированные службы
    Этот объект можно передавать в конструкторы
    '''
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ServiceRegistry, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

    def instance(self):
        print "instance called"
        global _instance
        return _instance

    def __init__(self):
        self._registry = dict()

    def register_service(self, service_name, service_instance):
        self._registry[service_name] = service_instance

    def get_service(self, service_name):
        if service_name in self._registry:
            return self._registry[service_name]
        return None

    def remove_service(self, service_name):
        if service_name in self._registry:
            service = self.get_service(service_name)
            del self._registry[service_name]
            return service
        return None
