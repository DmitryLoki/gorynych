# coding=utf-8
from twisted.application.service import Service
from twisted.python import log
from twisted.internet import task, reactor, threads, defer

from gorynych.common.infrastructure import persistence
from gorynych.processor import trfltfs


GET_EVENTS = """
    SELECT e.event_name, e.aggregate_id, e.event_payload
    FROM events e, dispatch d
    WHERE (event_name = %s OR event_name = %s) AND e.event_id = d.event_id;
    """

class TrackService(Service):
    '''
    TrackService parse track archive.
    '''
    def __init__(self, pool):
        self.pool = pool
        self.event_poller = task.LoopingCall(self.poll_for_events)

    def startService(self):
        d = self.pool.start()
        d.addCallback(lambda _: log.msg("DB pool started."))
        d.addCallback(lambda _: self.event_poller.start(2))
        return d.addCallback(lambda _: Service.startService(self))

    def stopService(self):
        d = self.pool.close()
        d.addCallback(lambda _: self.event_poller.stop())
        return d.addCallback(lambda _: Service.stopService(self))

    def poll_for_events(self):
        # log.msg("polling...")
        d = self.pool.runQuery(GET_EVENTS, ('ArchiveURLReceived',
                                                        'TrackArchiveParsed'))
        d.addCallback(self.process_events)
        return d.addCallback(lambda _:self.event_poller.stop())

    def process_events(self, events):
        while events:
            name, aggrid, payload = events.pop()
            reactor.callLater(0, getattr(self, 'process_'+str(name)),
                aggrid, payload)

    def process_ArchiveURLReceived(self, aggregate_id, payload):
        # d = self.create_track_archive(aggregate_id, payload)
        # d.addCallback(lambda ta: (ta, ta.download()))
        # d.addCallback(lambda ta, filename: (ta, ta.unarchive(filename)))
        # d.addCallback(lambda ta, namelist: (ta, ta.get_track_files(namelist)))
        # d.addCallback(lambda ta, filelist: ta.parse(filelist))
        # processor = OfflineTracksProcessor(race_info)
        # processor.calculate(corrected_data)

        race_id = str(aggregate_id)
        archive = self.get_url(str(payload))
        # копипаста из старого кода с некоторыми вкраплениями.
        task = trfltfs.init_task(race_id)
        par = trfltfs.Parser(task, archive, race_id)

        f_list = par.get_filelist()
        for f in f_list:
            par.parse(f)
        del f_list
        par.clean_data()
        parsed_data = par.datalist[::]
        pic(par.datalist, race_id, 'parsed')
        del par
        log.msg("go to correct data for a list with length %s", len(parsed_data))

        #try:
        corrected_data = trfltfs.correct_data(parsed_data)
        pic(corrected_data, race_id, 'corrected')
        del parsed_data
        log.msg("$" * 80)
        log.msg("$" * 80)
        log.msg("$" * 80)
        log.msg("Data corrected")
        log.msg("$" * 80)
        log.msg("$" * 80)
        # calculate speeds and distance to Goal
        calculator = trfltfs.BatchProcessor(task, race_id)
        calculated_values = calculator.calculate(corrected_data)
        del calculator
        log.msg("$" * 80)
        log.msg("$" * 80)
        log.msg("Values calculated")
        log.msg("$" * 80)
        pic(corrected_data, race_id, 'processed')
        log.msg("$" * 80)
        log.msg("Prepared for inserting")


    # def create_track_archive(self, race_id, payload):
    #     '''
    #
    #     @param race_id:
    #     @type race_id:
    #     @return:
    #     @rtype: L{Parser} instance
    #     '''
    #     dlist = [self.get_race_info(race_id),
    #              self.get_paragliders_info(race_id)]
    #     d = defer.gatherResults(dlist)
    #     d.addCallback(lambda x: TrackArchive(payload, self, x[0], x[1]))
    #     return d


    # def get_race_info(self, race_id):
    #     url = ''
    #     return self.get_url(url)

    # def get_paragliders_info(self, race_id):
    #     url = ''
    #     return self.get_url(url)

    def get_url(self, url):
        '''
        Download file from url.
        @param url:
        @type url: C{str}
        @return: path to file.
        @rtype: C{str}
        '''
        log.msg("I'VE GOT URL!!!", url)
        return '/Users/asumch2n/PycharmProjects/gorynych/1120-5321.zip'
        # return filename

    # def unarchive(self, filename):
    #     return threads.deferToThread(archive_service, filename)


def pic(x, name, suf):
    import cPickle
    try:
        f = open('.'.join((name, suf, 'pickle')), 'wb')
        cPickle.dump(x, f)
        f.close()
    except Exception as e:
        print "in pic", str(e)

