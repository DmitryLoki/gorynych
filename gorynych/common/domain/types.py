'''
Common types.
'''
from gorynych.common.domain.model import ValueObject

class Name(ValueObject):
    '''
    A type for names.
    Usage can be found in test_types
    '''

    def __init__(self, name=None, surname=None):
        if name:
            self.firstname = name
        else:
            raise ValueError("Firstname must be set.")

        if surname:
            self.lastname = surname
        else:
            raise ValueError("Lastname must be set.")

    def short(self):
        return '. '.join((self.firstname.capitalize()[0],
            self.lastname.capitalize()))

    def full(self):
        return ' '.join((self.firstname.capitalize(),
                         self.lastname.capitalize()))


class Country(ValueObject):

    def __init__(self, code=None):
        if code:
            self._code = code.upper()
        else:
            raise ValueError("Country can't be set with null code.")

    def code(self):
        return self._code

