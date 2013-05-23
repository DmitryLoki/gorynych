# coding=utf-8
from io import BytesIO
from struct import pack

import psycopg2
from twisted.python import log
from twisted.internet import threads, defer
import numpy as np

from gorynych.common.infrastructure import persistence as pe
from gorynych.processor import trfltfs, events
from gorynych.processor.domain import TrackArchive
from gorynych.common.domain.model import DomainIdentifier
from gorynych.common.application import EventPollingService
from gorynych.common.domain.services import APIAccessor
from gorynych import OPTS


NEW_TRACK = """
    INSERT INTO track (start_time, end_time, track_type, track_id)
    VALUES (%s, %s, (SELECT id FROM track_type WHERE name=%s), %s)
    RETURNING ID;
    """
INSERT_SNAPSHOT = """
    INSERT INTO track_snapshot (timestamp, id, snapshot) VALUES(%s, %s, %s)
    """

API = APIAccessor()

def find_snapshots(item, dbid):
    result = []
    if item.has_key('finish_time'):
        sn = dict(timestamp=int(item['finish_time']),
                  id=long(dbid),
                  snapshot="finished")
        result.append(sn)
    else:
        sn = dict(timestamp=int(item['times'][-1]),
                  id=long(dbid),
                  snapshot="landed")
        result.append(sn)
    return result


class ProcessorService(EventPollingService):
    '''
    Orchestrate track creation and parsing.
    '''
    @defer.inlineCallbacks
    def process_ArchiveURLReceived(self, ev):
        '''
        Download and process track archive.
        '''
        race_id = str(ev.aggregate_id)
        # TODO: add resource race/{id}/track_archive
        res = yield API.get_track_archive(race_id)
        if res['status'] == 'no archive':
            ta = TrackArchive(race_id, ev.payload)
            archinfo = yield threads.deferToThread(ta.process_archive)
            yield self._inform_about_paragliders(archinfo, race_id)
        elif res['status'] == 'unpacked':
            yield self.event_dispatched(ev.id)

    @defer.inlineCallbacks
    def _inform_about_paragliders(self, archinfo, race_id):
        '''
        Emit ParagliderFoundInArchive events for every received paraglider,
        also delete ArchiveURLReceived event.
        @param archinfo: ([{person_id, trackfile, contest_number}],
        [trackfile,], [person_id,])
        '''
        # TODO: add events for extra tracks and left paragliders.
        tracks, extra_tracks, left_paragliders = archinfo
        res = yield API.get_track_archive(race_id)
        if res['status'] == 'unpacked':
            # I think here will be list of contest numbers.
            persisted = res['progress']['paragliders_found']
            to_persist = []
            for di in tracks:
                if not di['contest_number'] in persisted:
                    to_persist.append(di)
                    tracks = to_persist
        else:
        # TODO: JSON serializer
            yield pe.event_store().persist(events
                .TrackArchiveUnpacked(race_id, aggregate_type='race',
                                      payload=archinfo))
        yield self._paragliders_found(tracks, race_id)

    def _paragliders_found(self, to_persist, race_id):
        dlist = []
        for di in to_persist:
            dlist.append(pe.event_store().persist(events
                .ParagliderFoundInArchive(race_id,
                                          aggregate_type='race',
                                          payload=di))
            )
        d = defer.gatherResults(dlist, consumeErrors=True)
        return d


class TrackService(EventPollingService):
    '''
    TrackService parse track archive.
    '''
    def process_ArchiveURLReceived(self, aggregate_id, payload, event_id):
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
        log.msg("Data corrected")
        # calculate speeds and distance to Goal
        calculator = trfltfs.BatchProcessor(task, race_id)
        calculated_values = calculator.calculate(corrected_data)
        del calculator
        log.msg("Values calculated")
        pic(calculated_values, race_id, 'processed')
        log.msg("Ready for inserting")
        return self.insert_offline_tracks(calculated_values, race_id,
                                          event_id)

    def insert_offline_tracks(self, tracksdata, race_id, event_id):
        '''
        @param tracksdata: list of dicts which looks like
        {'_id': 'contest_number', 'name': 'name', 'surname': 'surname',
        'country': 'country', 'nid': 'person_id',
        'glider_number': glider_number,
        'alt':[int], 'lon': [str], 'lat':[str], 'times':[int],
        'v_speed':float, 'h_speed':float, 'left_distance':int}
        '''
        # psycopg2 can't user copy_from in async mode. This is a SashaGrey
        # workaround
        conn = psycopg2.connect(database=OPTS['db']['database'],
                                host=OPTS['db']['host'],
                                user=OPTS['db']['user'],
                                password=OPTS['db']['password'])
        cur = conn.cursor()
        for i, item in enumerate(tracksdata):
            track_id = str(DomainIdentifier())
            cur.execute(NEW_TRACK, (item['times'][0],item['times'][-1],
                                   'competition aftertask', track_id))
            dbid = cur.fetchone()
            data = prepare_text(prepare_data(dbid, item))
            snaps = find_snapshots(item, dbid[0])
            for snap in snaps:
                cur.execute(INSERT_SNAPSHOT, (snap['timestamp'], snap['id'],
                snap['snapshot']))
            cur.copy_expert("COPY track_data FROM STDIN ", data)
            persistence.event_store().persist(
                events.PersonGotTrack(item['nid'], track_id, 'person'))
            persistence.event_store().persist(
                 events.TrackAddedToRace(race_id,
                                         (track_id, item['glider_number']),
                                         'race'))
            log.msg("Inserted track ", i)
        cur.execute("DELETE FROM dispatch WHERE event_id=%s", (event_id,))
        conn.commit()
        log.msg('Tracks has been inserted successfully.')
        return conn.close()
        # log.msg("Start data inserting.")
        # print "INSERTING"
        # def inserting_transaction(cur):
        #     d = defer.Deferred()
        #     log.msg("In transaction function.")
        #     print "IN TRANSACTION"
        #     for i, item in enumerate(tracksdata):
        #         print "ITEM", i
        #         this create new track and return it's id
                # track_id = str(DomainIdentifier())
                # d.addCallback(lambda _: cur.execute(NEW_TRACK,
                #                                   (item['times'][0],
                #                            item['times'][-1],
                #                            'competition aftertask',
                #                            track_id)))
                # d.addCallback(lambda _: cur.fetchone())

                # d.addCallback(prepare_binary, item)
                # d.addCallback(lambda x: cur.copy_expert(
                #     "COPY track_data FROM STDIN WITH BINARY", x))
                # Inform person and race about new tracks.
                # d.addCallback(lambda _: persistence.event_store().persist(
                #     events.PersonGotTrack(item['nid'], track_id, 'person')))
                # d.addCallback(lambda _: persistence.event_store().persist(
                #     events.TrackAddedToRace(race_id, track_id, 'race')))

                # d.addCallback(lambda _:log.msg("Track inserted."))
                # d.callback(1)
            # return d
        # return self.pool.runInteraction(inserting_transaction)


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
        return '/home/gorynych/data/0.1/1120-5321.zip'
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

def prepare_data(trackdb_id, item):
    '''
    Convert data from dict to numpy array for inserting into db.
    @param trackdb_id:
    @type trackdb_id:
    @param item:
    @type item:
    @return: 2d-array which looks like table in DB.
    @rtype: numpy.array
    '''
    log.msg("Preparing for ", trackdb_id)
    dtype = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
             ('lon', 'f4'),
             ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
             ('distance', 'i4')]
    # rows, columns
    shape = len(item['times'])
    # creating numpy data
    data = np.empty(shape, dtype)
    data['id'] = np.ones(shape) * long(trackdb_id[0])
    data['timestamp'] = np.array(item['times'])
    data['lat'] = np.array(item['lat'])
    data['lon'] = np.array(item['lon'])
    data['alt'] = np.array(item['alt'])
    data['g_speed'] = np.array(item['h_speed'])
    data['v_speed'] = np.array(item['v_speed'])
    data['distance'] = np.array(item['left_distance'])
    return data

def prepare_binary(data):
    '''
    Prepare binary file for inserting into PostgreSQL.
    Was taken from http://stackoverflow.com/questions/8144002/use-binary-copy-table-from-with-psycopg2/8150329#8150329
    '''

    # Preparing binary data for inserting into db.
    pgcopy_dtype = [('num_fields', '>i2')]
    for field, dtype in data.dtype.descr:
        pgcopy_dtype += [(field + '_length', '>i4'),
                         (field, dtype.replace('<', '>'))]
    pgcopy = np.empty(data.shape, pgcopy_dtype)
    pgcopy['num_fields'] = len(data.dtype)
    for i in range(len(data.dtype)):
        field = data.dtype.names[i]
        # field length in bytes
        pgcopy[field + '_length'] = data.dtype[i].alignment
        pgcopy[field] = data[field]
    log.msg("Binary prepared")

    cpy = BytesIO()
    # Write as specified: http://www.postgresql.org/docs/current/interactive/sql-copy.html
    cpy.write(pack('!11sii', b'PGCOPY\n\377\r\n\0', 0, 0))
    cpy.write(pgcopy.tostring()) # all rows
    cpy.write(pack('!h', -1)) # file trailer
    cpy.seek(0)
    return(cpy)

def prepare_text(data):
    cpy = BytesIO()
    for row in data:
        cpy.write('\t'.join([repr(x) for x in row]) + '\n')
    cpy.seek(0)
    return(cpy)
