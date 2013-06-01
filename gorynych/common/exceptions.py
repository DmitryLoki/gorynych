__author__ = 'Boris Tsema'


class NoAggregate(Exception):
    '''
    Raised in repositories when aggregate can't be found.
    '''


class DatabaseValueError(Exception):
    '''
    Raise when values from database are not so good as expected.
    '''


class BadCheckpoint(Exception):
    '''
    Raise when checkpoints don't satisfy some conditions.
    '''


class DeserializationError(Exception):
    '''
    Wrapper for errors in serializers.
    '''


class TrackArchiveAlreadyExist(Exception):
    '''
    Raised when someone try to add track archive after it has been parsed.
    '''