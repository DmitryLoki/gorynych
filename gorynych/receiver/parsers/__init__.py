from zope.interface import Interface


class IParseMessage(Interface):

    '''
    I parse incoming messages from gps-trackers.
    '''
    def check_message_correctness(msg):
        '''
        I check is message correct by checking it's checksum or another
        method.
        @param msg: message from tracker.
        @type msg:
        @return: message from tracker if it was correct.
        @rtype: bytes
        @raise ValueError if message is incorrect.
        '''

    def parse(msg):
        '''
        I do the work.
        @param msg: message from device.
        @type msg:
        @return: parsed message.
        @rtype: dict
        '''


from tr203 import GlobalSatTR203
from logonly_tr203 import LogOnlyGlobalSatTR203
from telt_gh3000 import TeltonikaGH3000UDP
from old_mobile import MobileTracker
from app13.parser import App13Parser, PathMakerParser, SBDParser
from gt60 import RedViewGT60

tr203 = GlobalSatTR203
app13 = App13Parser
telt_gh3000 = TeltonikaGH3000UDP
gt60 = RedViewGT60
pmtracker = PathMakerParser
