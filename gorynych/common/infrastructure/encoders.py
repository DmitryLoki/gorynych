from gorynych.common.domain.model import DomainIdentifier
import simplejson as json


class InfoJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, DomainIdentifier):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
