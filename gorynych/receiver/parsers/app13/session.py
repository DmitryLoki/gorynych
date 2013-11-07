
class App13Session(object):
    fields = ['imei']
    params = None

    def init(self, params):
        self.params = params

    def is_valid(self):
        if not self.params or not isinstance(self.params, dict):
            return False
        for f in self.fields:
            if f not in self.params:
                return False
        return True


        