from datetime import date
import re
from gorynych.common.domain.model import IdentifierObject
import uuid


class ContestID(IdentifierObject):
    def __init__(self):
        fmt = '%y%m%d'
        self.__creation_date = date.today().strftime(fmt)
        self.__aggregate_type = 'cnts'
        self.__random = uuid.uuid4().fields[0]
        self._id = '-'.join((self.__aggregate_type, self.__creation_date,
                             str(self.__random)))

    def _string_is_valid_id(self, string):
        agr_type, creation_date, random_number = string.split('-')
        assert agr_type == 'cnts', "Wrong aggregate type in id string."
        assert re.match('[0-9]{6}', creation_date), "Wrong creation date in " \
                                                    "id string."
        try:
            int(random_number)
        except ValueError as error:
            raise ValueError("Wrong third part of id string: %r" % error)
        return True


class PersonID(IdentifierObject):
    '''
    Person identificator is a uuid string.
    '''
    pass


class RaceID(IdentifierObject):
    pass


class TrackerID(IdentifierObject):
    pass

