__author__ = 'Boris Tsema'

class NoAggregate(Exception):
    '''
    Raised in repositories when aggregate can't be found.
    '''

class BadCheckpoint(Exception):
    '''
    Raise when checkpoints don't satisfy some conditions.
    '''