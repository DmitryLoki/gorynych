'''
Common types.
'''
from gorynych.common.domain.model import ValueObject

class Name(ValueObject):
    '''
    A type for names.
    Usage can be found in test_types
    '''

    def __init__(self, firstname=None, lastname=None):
        if firstname:
            self.firstname = firstname
        else:
            raise ValueError("Firstname must be set.")

        if lastname:
            self.lastname = lastname
        else:
            raise ValueError("Lastname must be set.")

    def get_shortname(self):
        return '. '.join((self.firstname.capitalize()[0],
            self.lastname.capitalize()))

    def get_fullname(self):
        return ' '.join((self.firstname.capitalize(),
                         self.lastname.capitalize()))


class Country(ValueObject):

    def __init__(self, code=None):
        if code:
            self.code = code.upper()
        else:
            raise ValueError("Country can't be set with null code.")

    def get_code(self):
        return self.code

