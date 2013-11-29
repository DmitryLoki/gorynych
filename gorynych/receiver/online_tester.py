'''
Mindless copy/paste.
'''
__author__ = 'Boris Tsema'
import subprocess
import sys
from twisted.application import service, internet
import ast
import os
import cPickle
import socket
from twisted.internet import  task
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web import server
from twisted.web.template import Element, renderer, XMLFile, flatten
import simplejson as json

sys.path.append('..')


from gorynych.receiver.receiver import ReceiverRabbitQueue, ReceiverService, DumbAuditLog
from gorynych.receiver.protocols import UDPReceivingProtocol

HOST, PORT = 'localhost', 9998
DIR = 'test_data'

class TesterService(service.Service):

    sleep = 0.01

    def __init__(self):
        # {eventid.taskid: [{ts: time, msg: msg}]}
        self.datas = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cur_index = 0
        self.res = None
        self.started = False
        self.emitter = task.LoopingCall(self._send)

    def load_data(self, name):
        if not self.datas.has_key(name):
            data = cPickle.load(open(os.path.join(DIR,
                '.'.join(('auditlog', name, 'pickle')))))
            self.datas[name] = data
        return name

    def get_datas(self):
        if self.datas.keys():
            return self.datas.keys()
        return []

    def start(self, res, index):
        if index == '':
            index = 0
        index = int(index)
        self.res = res
        self.cur_index = index
        self.remove_file_with_state(res)
        subprocess.check_call('./dp_restart.sh &', shell=True)
        self.emitter.start(self.sleep)
        self.started = True
        return "%s is started from time %s", res, self.datas[res][index]['ts']

    def remove_file_with_state(self, res):
        tid = res.split('.')[1]
        state_file = '.'.join(('pilots_state', tid))
        if os.path.isfile(state_file):
            os.remove(state_file)

    def _send(self):
        if self.cur_index < len(self.datas[self.res]):
            self.sock.sendto(self.datas[self.res][self.cur_index]['msg'],
                (HOST, PORT))
            self.cur_index += 1
        else:
            self.stop()
            return "End of data reached. Stopped."

    def stop(self):
        if not self.res is None:
            self.emitter.stop()
        self.started = False
        self.res = None

    def _search_files(self):
        a = lambda x: isinstance(x, int)
        f_list = filter(lambda x: x.endswith('pickle'), os.listdir(DIR))
        for filename in f_list:
            name = '.'.join(filename.split('.')[1:3])
            self.load_data(name)

    def startService(self):
        self._search_files()
        service.Service.startService(self)

    def stopService(self):
        service.Service.stopService(self)
        self.stop()

def prepare_data(filename, eventid, taskid):
    fd = open(filename, 'r')
    result = []
    for line in fd.readlines():
        try:
            line_dict= ast.literal_eval(line)
        except Exception as err:
            print "error occured ", err
            print "on line ", line
            continue
        cd = {}
        cd['msg'] = line_dict['msg']
        cd['ts'] = line_dict['ts']
        result.append(cd)
    try:
        os.mkdir(DIR)
    except OSError as (num, err):
        if num == 17:
            pass
        else:
            raise OSError(err)
    pf = open(os.path.join(DIR, '.'.join(('auditlog', str(eventid), str(taskid),
    'pickle' ))), 'wb')
    cPickle.dump(result, pf)
    return 'ready'


class WebUI(Resource):

    def __init__(self, service):
        Resource.__init__(self)
        self.service = service
        self.element = MyElement(service)

    def render_GET(self, request):
        self._render_page(request, self.element)
        return server.NOT_DONE_YET

    def render_POST(self, request):
        if self.service.started:
            self.service.stop()
        else:
            if not self.service.datas.keys():
                return "No data for tests."
            self.service.start(request.args['data'][0],
                index=request.args['index'][0])
        self._render_page(request, self.element)
        return server.NOT_DONE_YET

    def _render_page(self, request, element):
        d = flatten(request, element, request.write)
        def done(x):
            request.finish()
            return x
        d.addBoth(done)


    def getChild(self, path, request):
        return self


class RetreiveJSON(Resource):
    def __init__(self, service):
        Resource.__init__(self)
        self.service = service

    def render_GET(self, request):
        result_ = []
        di = self.service.coords
        for key in di.keys():
            result = dict()
            result['imei'] = key
            result['lat'] = di[key][0]
            result['lon'] = di[key][1]
            result['alt'] = di[key][2]
            result['speed'] = di[key][3]
            result['time'] = di[key][4]
            result_.append(result)
        return json.dumps(result_)

    def getChild(self, path, request):
        return self

class MyElement(Element):
    a = os.path.join(os.path.dirname(__file__),'online_tester_template.xml')

    #loader = XMLFile(open(a))

    def __init__(self, service):
        self.service = service

    @renderer
    def has_data(self, request, tag):
        for item in self.service.get_datas():
            yield tag.clone().fillSlots(value=item, data_text=item)

    @renderer
    def run_info(self, request, tag):
        '''return currently testing event and task'''
        if self.service.res:
            eventid, taskid = self.service.res.split('.')
            tag.fillSlots(running="""Task {task} of event {event} is
                running currently.""".format(event=eventid,
                task=taskid))
        else:
            tag.fillSlots(running="No task is running now.")
        return tag

    @renderer
    def link_to_run(self, request, tag):
        if self.service.res:
            event, task = self.service.res.split('.')
            tag.fillSlots(see_url='''http://dev.airtribune.com/scanex_world?nid={event}&tid={task}&online=1&display=2d'''.format(event=event, task=task),
                text='watch the race')
        else:
            tag.fillSlots(see_url='', text='')
        return tag

    @renderer
    def submit(self, request, tag):
        if self.service.res:
            tag.fillSlots(text="stop testing")
        else:
            tag.fillSlots(text="start testing")
        return tag


application = service.Application('hui')

sc = service.IServiceCollection(application)

audit_log = DumbAuditLog()
sender = ReceiverRabbitQueue(host='localhost', port=5672, exchange='receiver')
receiver_service = ReceiverService(sender, audit_log)

sender.setServiceParent(sc)
receiver_service.setServiceParent(sc)

udp_server = UDPReceivingProtocol(receiver_service)
udp_receiver = internet.UDPServer(PORT, udp_server)
udp_receiver.setServiceParent(sc)

ts = TesterService()

ts.setServiceParent(sc)

root = WebUI(ts)

internet.TCPServer(8083, Site(root)).setServiceParent(sc)
