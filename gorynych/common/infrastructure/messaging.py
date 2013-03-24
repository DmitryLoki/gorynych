'''
Base classes for messaging infrastructure.
'''

class DomainEventsPublisher(object):
    '''
    Is used to publish events.
    '''

    def publish(self, event):
        pass
