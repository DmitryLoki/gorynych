# -*- coding: utf-8 -*-
from datetime import date
import re
from gorynych.common.domain.model import DomainIdentifier
import uuid

def namespace_date_random_validator(string, atype):
    aggr_type, creation_date, random_number = string.split('-')
    assert aggr_type == atype, "Wrong aggregate type in id string."
    assert re.match('[0-9]{6}', creation_date), "Wrong creation date in " \
                                                "id string."
    try:
        int(random_number)
    except ValueError as error:
        raise ValueError("Wrong third part of id string: %r" % error)
    return True


def namespace_uuid_validator(string, namespace):
    aggr_type, uid = string.split('-', 1)
    assert aggr_type == namespace, "Wrong aggregate type %s in id string %s"\
                                   % (namespace, string)
    _uid = uuid.UUID(uid)
    return True


class ContestID(DomainIdentifier):
    '''
    cnts-130513-12345341234
    namespace-ddmmyy-random
    '''
    def __init__(self):
        fmt = '%y%m%d'
        self.__creation_date = date.today().strftime(fmt)
        self.__aggregate_type = 'cnts'
        self.__random = uuid.uuid4().fields[0]
        self._id = '-'.join((self.__aggregate_type, self.__creation_date,
                             str(self.__random)))

    def _string_is_valid_id(self, string):
        return namespace_date_random_validator(string, 'cnts')


class PersonID(DomainIdentifier):
    '''
    pers-130513-424141234123
    namespace-ddmmyy-random
    '''
    def __init__(self):
        fmt = '%y%m%d'
        self.__creation_date = date.today().strftime(fmt)
        self.__aggregate_type = 'pers'
        self.__random = uuid.uuid4().fields[0]
        self._id = '-'.join((self.__aggregate_type, self.__creation_date,
                             str(self.__random)))

    def _string_is_valid_id(self, string):
        return namespace_date_random_validator(string, 'pers')


class RaceID(DomainIdentifier):
    '''
    r-b4e75299-c7c5-4b73-a7b0-17f57320231c
    r-uuid4
    '''
    def __init__(self):
        _uid = str(uuid.uuid4())
        self._id = '-'.join(('r', _uid))

    def _string_is_valid_id(self, string):
        return namespace_uuid_validator(string, 'r')


class TrackerID(DomainIdentifier):
    '''
    trckr-749e0d12574a4d4594e72488461574d0'
    device_type-device_id
    '''
    device_types = ['tr203']

    def __init__(self, device_type, device_id):
        super(TrackerID, self).__init__()
        if not device_type in self.device_types:
            raise ValueError("Device type %s not in allowed device types %s"
                             % (device_type, self.device_types))
        if not device_id:
            raise ValueError("Empty device id passed.")
        self._id = '-'.join((str(device_type), str(device_id)))

    def _string_is_valid_id(self, string):
        dtype, did = string.split('-', 1)
        assert dtype in self.device_types, "Incorrect device type %s" % dtype
        return True

    @classmethod
    def fromstring(cls, string):
        dtype, did = string.split('-', 1)
        id = cls(dtype, did)
        if id._string_is_valid_id(str(string)):
            id._id = str(string)
            return id

    @property
    def device_type(self):
        dtype, did = self._id.split('-', 1)
        return dtype

    @property
    def device_id(self):
        dtype, did = self._id.split('-', 1)
        return did
