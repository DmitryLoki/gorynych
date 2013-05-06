'''
Old working code.
'''
import zipfile
import shutil
import os
import time
import math
from calendar import timegm
# from lxml import etree
from xml import etree
import numpy as np
from scipy import signal, interpolate


from twisted.python import log
import requests


URL = 'http://localhost:8085'
EARTH_RADIUS = 6371000
NECESSARY_KEYS = ['alt', 'times', 'lat', 'lon']
MAX_TIME_DIF = 300
MAX_ALT = 6000
MIN_ALT = 50
MAXDIFS = [('alt', 40), ('lat', 0.001), ('lon', 0.001)]
WP_ERROR = 30
MAX_VERT_SPEED = 7
MAX_H_SPEED = 85


def coroutine(func):
    def start(*args, **kwargs):
        g = func(*args, **kwargs)
        g.next()
        return g
    return start


class Parser(object):
    '''
    Parse given tracks.
    '''

    def __init__(self, task, archive_file, race_id):
        self.race_id = str(race_id)
        self.unpack_dir = archive_file.split('.')[0]
        self.datalist = get_pilots_from_resource(race_id)
        self.task = task
        log.msg("Task is %s", self.task)
        log.msg("datalist is %s", self.datalist)

    def get_filelist(self):
        return filter(lambda x : x.endswith('.igc') or x.endswith('.kml'),
                      archive_processor(self.unpack_dir, 'zip'))

    def parse(self, filename):
        if filename.endswith('.igc'):
            self._igc_parse(filename)
        elif filename.endswith('.kml'):
            self._kml_parse(filename)

    def clean_data(self, keys=NECESSARY_KEYS):
        '''
        Delete datalist items without specified keys or with empty values.
        '''
        assert isinstance(keys, list), "Keys must be list."
        bads = []
        for i, item in enumerate(self.datalist):
            for key in keys:
                if not (item.has_key(key) and len(item[key]) > 0):
                    log.msg("Pilot %s don't has key %s", item['_id'], key)
                    bads.append(i)
                    break
        bads.sort(reverse=True)
        for i in bads:
            del self.datalist[i]

    def _kml_parse(self, filename):
        element = find_element(filename)
        times, gl_num = get_times_and_gl_num(element, filename)
        has = False
        for i, item in enumerate(self.datalist):
            if item['_id'] == str(gl_num):
                num = i
                has = True
                log.msg("Begin to insert data for pilot %s ...", gl_num)
                break
        if not has: return
        times, indices = np.unique(times, return_index=True)

        lat, lon, alt = get_coords(element)
        lat = lat[indices]
        lon = lon[indices]
        alt = alt[indices]
        if not (len(times) * gl_num * len(lat) * len(lon) * len(alt)):
            log.err('No coordinates for pilot %s', gl_num)
            return
        y = (times < self.task['start']).nonzero()[0]
        if y.any():
            left_point = y[-1]
        else:
            left_point = None
        x = ((np.ediff1d(times, to_begin=1) >
              MAX_TIME_DIF).nonzero()[0] > left_point).nonzero()[0]
        if x.any():
            right_point = x[0]
        else:
            right_point = None
        log.msg("right and left indexes are: %s, %s", right_point, left_point)
        self.datalist[num]['times'] = list(times[right_point: left_point])
        self.datalist[num]['lat'] = list(lat[right_point: left_point])
        self.datalist[num]['lon'] = list(lon[right_point: left_point])
        self.datalist[num]['alt'] = list(alt[right_point: left_point])
        log.msg("keys: %r", self.datalist[num].keys())
        log.msg("success with pilot %s", gl_num)

    def _igc_parse(self, filename):
        """Receive file, parse the file
        and fill one dictionary.

        """
        fh = open(filename, 'r')
        log.msg("got file %s", filename)
        try:
            r = self._gl_number()
            # For Paramania. Read pilot id from filename. This filename looks like:
            # Name Surname.date-time.fournumbers.ID.igc
            p_id = os.path.basename(filename).split('.')
            if len(p_id) > 2:
                log.msg("pilot id %s", p_id[-2])
                line = ':'.join(('HFCID', p_id[-2]))
                r.send(line)
            for line in fh.readlines():
                r.send(line)
            r.close()
        except StopIteration as e:
            if str(e) == 'Parsing complete':
                r.close()
                log.msg("Parsing of %s complete", filename)
            elif str(e) == 'Extra pilot':
                r.close()
                log.msg("Parsing of %s complete, extra pilot", filename)
            else:
                r.close()
        finally:
            fh.close()


    @coroutine
    def _gl_number(self):
        """Parse and check glider number and send line to liner."""
        r = self._liner()
        while True:
            line = (yield)
            if line.startswith('HFCID'):
                gl_num = int(line.split(':')[1])
                log.msg("Got data for %s type %s" % (gl_num, type(gl_num)))
                for i, item in enumerate(self.datalist):
                    if item['_id'] == str(gl_num):
                        log.msg('item %s' % i)
                        r.send('item:' + str(i))
                        while True:
                            line = (yield)
                            r.send(line)
                raise StopIteration("Extra pilot")
            else:
                r.send(line)


    @coroutine
    def _liner(self):
        """Receive lines from file, send only lines for correct date to parser.
        After receiving wrong date raise exception StopIteration, that means end of
        parsing.

        """
        switch = 1
        # Number of dictionary with date in self.datalist
        num = ''
        while switch:
            line = (yield)
            if line.startswith('item'):
                num = line.split(':')[1]
                log.msg('got item %s', num)
            if line.startswith('HFDTE') and line[-8:-2] == self.task['date'] and not num:
                while switch:
                    line = (yield)
                    if line.startswith('item'):
                        num = line.split(':')[1]
                        # start parsing
                        parse = self._parser(num)
                        while switch:
                            line = (yield)
                            if line.startswith('B'):
                                parse.send(line)
                            elif line.startswith('HFDTE') and not (line[-8:-2] ==
                                                                       self.task['date']):
                                parse.close()
                                raise StopIteration("Parsing complete")
            elif line.startswith('HFDTE') and line[-8:-2] == self.task['date'] and num:
                parse = self._parser(num)
                while switch:
                    line = (yield)
                    if line.startswith('B'):
                        parse.send(line)
                    elif line.startswith('HFDTE') and line[-8:-2] != self.task['date']:
                        parse.close()
                        raise StopIteration("Parsing complete")


    @coroutine
    def _parser(self, num):
        """Coroutine.  Receive number of dictionary in self.datalist list as initial
        value.  Receive 'B' lines for parsing and send them to {t,alt,lat,lon}_parse
        functions.

        """
        tim = self._t_parse(int(num), self.task['start'])
        alt = self._alt_parse(int(num))
        lat = self._lat_parse(int(num))
        lon = self._lon_parse(int(num))
        while True:
            line = (yield)
            alt.send(line[25:35])
            lat.send(line[7:15])
            lon.send(line[15:24])
            tim.send(line[1:7])


    @coroutine
    def _t_parse(self, num, starttime):
        """Coroutine. Parse time. Receive string, creates two lists of integers in
        self.datalist[num] dictionary:
        ['times'] - time in second from Epoch in UTC,
        ALWAYS MUST BE CALLED AFTER alt, lat and lon PARSING!

        """
        def get_timestamp(t):
            return int(timegm(time.strptime(
                self.task['date'] + t, '%d%m%y%H%M%S')))
        self.datalist[num]['times'] = []
        times = self.datalist[num]['times']
        while True:
            t = (yield)
            ts = get_timestamp(t)
            if ts < self.task['start']:
                # log.msg("time %s before task start time %s for %s",
                #           t, self.task['start'], self.datalist[num]['_id'])
                # Point before start - wrong point. Delete everything.
                self._delete_index(num, 0)
            else:
                last_ts = ts
                times.append(ts)
            while times:
                t = (yield)
                ts = get_timestamp(t)
                if ts <= last_ts:
                    # log.msg("bad or reverse time for %s: %s",
                    #           self.datalist[num]['_id'], t)
                    self._delete_index(num, len(self.datalist[num]['lat']) - 1)
                elif ts - last_ts > MAX_TIME_DIF:
                    # log.msg("time > MAX_TIME_DIF for %s: %s",
                    #           self.datalist[num]['_id'], t)
                    if ts > self.task['window_is_open']:
                        self._delete_index(num, len(self.datalist[num]['lat']) - 1)
                    else:
                        times.append(ts)
                        last_ts = ts
                else:
                    times.append(ts)
                    last_ts = ts



    def _delete_index(self, num, i):
        del self.datalist[num]['lat'][i]
        del self.datalist[num]['lon'][i]
        del self.datalist[num]['alt'][i]
        if self.datalist[num].has_key('baro'):
            del self.datalist[num]['baro'][i]


    @coroutine
    def _alt_parse(self, num):
        """Coroutine.  Parse altitude.  Receive string, creates
        two lists of integers in self.datalist[num] dictionary:
        ['alt'] - altitude in meters,

        """
        t = (yield)
        self.datalist[num]['alt'] = []
        alt = self.datalist[num]['alt']
        eb = 0
        if int(t[5:]):
            # use altitude from gps
            s = 5
            e = 10
            if int(t[:5]):
                eb = 1
                self.datalist[num]['baro'] = []
                baro = self.datalist[num]['baro']
                baro.append(float(t[:5]))
        else:
            # use altitude from barometer
            s = 0
            e = 5
        alt.append(float(t[s:e]))
        while True:
            t = (yield)
            x = float(t[s:e])
            if eb:
                baro.append(float(t[:5]))
            alt.append(x)


    @coroutine
    def _lon_parse(self, num):
        """Coroutine.  Parse longitude.  Receive string, creates
        two lists of integers in self.datalist[num] dictionary:
        ['lon'] - longitude in decimal degree format,
        ['l_dif'] - difference between i and i-1 items of ['lon'].

        """
        self.datalist[num]['lon'] = []
        lon = self.datalist[num]['lon']
        while True:
            t = (yield)
            value = longitude(t)
            lon.append(value)


    @coroutine
    def _lat_parse(self, num):
        """Coroutine.  Parse latitude.  Receive string, creates
        two lists of integers in self.datalist[num] dictionary:
        ['lat'] - latitude in decimal degree format,
        ['l_dif'] - difference between i and i-1 items of ['lat'].

        """
        self.datalist[num]['lat'] = []
        lat = self.datalist[num]['lat']
        while True:
            t = (yield)
            value = latitude(t)
            lat.append(value)


def archive_processor(unpack_dir, ext):
    """Check and unzip archive, or raise BadArchive exception
    """
    enc = 'ascii'
    errors = 'replace'
    namelist = []
    #log.msg("Will check zipfile %s", '.'.join((unpack_dir, ext)))
    if zipfile.is_zipfile(unpack_dir + '.' + ext):
        arc = zipfile.ZipFile(unpack_dir + '.' + ext)
        try:
            shutil.rmtree(unpack_dir)
        except OSError as e:
            log.msg("OSError while removing dir %s: %r", unpack_dir, e)
        try:
            os.mkdir(unpack_dir)
        except OSError as value:
            log.err("Can't create dir %s: %s" % (unpack_dir, value))
        for fd in arc.infolist():
            try:
                fn = fd.filename
                try:
                    #fnd = fn.decode('utf-8', 'ignore')
                    fnd = unicode(fn, 'utf-8', 'replace')
                except Exception as e:
                    log.err("while decoding filename: %s" % e)
                    fnd = fn
                try:
                    fne = fnd.encode(enc, errors)
                except Exception as e:
                    log.err("while encoding filename: %s"% e)
                if os.sep in fne:
                    path = os.path.join(unpack_dir, fne[:fne.rindex(os.sep)])
                    #log.msg('nested directory found in %s, path is %s', fne, path)
                    if not os.path.exists(path):
                        os.makedirs(path)
                        log.msg("dir %s created", path)
                if fne.endswith(os.sep): continue
                #log.msg("now i will extract %s into %s", fn, os.path.join(unpack_dir, fne))
                f = open(os.path.join(unpack_dir, fne), 'wb')
                f.write(arc.open(fn).read())
                f.close()
                namelist.append(fne)
            except Exception as value:
                log.err(
                    "Archive %s.%s can't be extracted: %s" %
                    (unpack_dir, ext, value))
    else:
        log.err("Bad archive %s", unpack_dir)
    log.msg("files: %s", namelist)
    return [os.path.join(unpack_dir, name) for name in namelist]


def init_task(race_id):
    """Fullfill result global dictionary with information about waypoints:
    result: {date: str, p_amount: int,
        lat1: string, lon1: string, rad1: int, dist1: int, ...}.
    dist_: distance from waypoint to goal.
    """
    result = {}
    r = requests.get('/'.join((URL, 'race', race_id)))
    a = r.json()
    result['end'] = int(a['end_time'])
    result['start'] = int(a['start_time'])
    result['racetype'] = a['race_type']
    result['bearing'] = a['bearing']
    if not result['bearing'] == 'None':
        result['bearing'] = int(result['bearing'])
    a['dists'] = calculate_distances(a['checkpoints']['features'])
    result['p_amount'] = len(a['checkpoints']['features'])

    for i, ch in enumerate(a['checkpoints']['features']):
        j = str(i+1)
        result['lat'+j] = float(ch['geometry']['coordinates'][0])
        result['lon'+j] = float(ch['geometry']['coordinates'][1])
        result['rad'+j] = int(ch['properties']['radius'])
        if ch['properties']['checkpoint_type'] == 'ss':
            result['ss_lon'] = float(ch['geometry']['coordinates'][1])
            result['ss_lat'] = float(ch['geometry']['coordinates'][0])
            result['ss_rad'] = int(ch['properties']['radius'])
            result['window_is_open'] = int(ch['properties']['open_time'])
        if ch['properties']['checkpoint_type'] == 'es':
            result['es_lon'] = float(ch['geometry']['coordinates'][1])
            result['es_lat'] = float(ch['geometry']['coordinates'][0])
            result['es_rad'] = int(ch['properties']['radius'])
        result['dist' + j] = a['dists'][i]

    dt = time.gmtime(result['start'])
    #let's do a string 'ddmmyy'
    dd = lambda x: ('0' + str(dt[x]))[-2:]
    result['date'] = dd(2) + dd(1) + str(dt[0])[-2:]
    return result


def calculate_distances(ch_list):
    ch_list.reverse()
    result = [0]
    for i, ch in enumerate(ch_list):
        result.append(point_dist(ch['geometry']['coordinates'][0],
                                 ch['geometry']['coordinates'][1],
                                 ch_list[i]['geometry']['coordinates'][0],
                                 ch_list[i]['geometry']['coordinates'][1])
                      + result[i])
    result.reverse()
    return result


def get_pilots_from_resource(race_id):
    """Fullfill list with dicts:
    {'_id': 'contest_number', 'name': 'name', 'surname': 'surname',
    'country': 'country', 'nid': 'nid', 'glider_number': glider_number}

    """
    result = []
    r = requests.get('/'.join((URL, 'race', race_id, 'paragliders')))
    pt = r.json()
    # pt is a list of dictionaries with fields:
    # {'contest_number': '12', 'name':pilotname, 'surname':, 'glider':glider
    # model, 'country':country, 'person_id':'person_id'},
    for p in pt:
        di = {}
        di['_id'] = p['contest_number']
        di['glider_number'] = int(p['contest_number'])
        di['name'] = str(p['name']).split(' ')[0]
        di['surname'] = str(p['name']).split(' ')[1]
        di['glider'] = str(p['glider'])
        di['country'] = str(p['country'])
        di['nid'] = p['person_id']
        result.append(di)
    return result


def point_dist(start_lat, start_lon, end_lat, end_lon):
    """Return distance between two points in float
    TODO: analyze function and rewrite on Cython or C if needed
    """
    try:
        start_lat = float(math.radians(float(start_lat)))
        start_lon = float(math.radians(float(start_lon)))
        end_lat = float(math.radians(float(end_lat)))
        end_lon = float(math.radians(float(end_lon)))
    except TypeError as err:
        log.err("TypeError for coordinates: %s %s %s %s" %
                      (start_lat, start_lon, end_lat, end_lon))
    d_lat = end_lat - start_lat
    d_lon = end_lon - start_lon
    df = 2 * math.asin(math.sqrt(math.sin(d_lat/2)**2 + math.cos(start_lat) * math.cos(end_lat) * math.sin(d_lon/2)**2))
    c = df * EARTH_RADIUS
    return c


def correct_data(datalist):
    #TODO: rewrite this with better numpy usage
    def place_alt_in_corridor(alt):
        for i, elem in enumerate(alt):
            if elem > MAX_ALT:
                alt[i] = MAX_ALT
            if elem < MIN_ALT:
                alt[i] = MIN_ALT
        return alt
    for itemnumber, item in enumerate(datalist):
        log.msg('got id %s', item['_id'])
        bads = []
        for i, elem in enumerate(item['alt']):
            if not MIN_ALT < elem < MAX_ALT:
                bads.append(i)
        bads.reverse()
        log.msg("list with ultrabad alts for %s: %s, percentage: %s",
                  item['_id'], bads, int((len(bads) / len(item['alt'])) * 100))
        # delete bad points if it's last
        # TODO: do smth with this XXX:
        extra_bads = []
        log.msg("initial times length is %s", len(item['times']))
        for i, elem in enumerate(bads):
            if elem == len(item['times']) - 1:
                del item['times'][elem]
                extra_bads.append(i)
            else:
                break
        log.msg("times length is %s", len(item['times']))
        log.msg("extra_bads is %s", list(extra_bads))
        bads = np.array(bads, dtype=int)
        extra_bads = np.array(extra_bads, dtype=int)
        end_points = bads[extra_bads]
        log.msg("bad end points is %s", list(end_points))
        bads = np.delete(bads, extra_bads)
        log.msg("new bads %s", list(bads))

        x = np.array(item['times'], dtype=int)
        x = np.delete(x, bads)
        #print "x[0] is ", x[0]
        for dif in MAXDIFS:
            counter = 1
            kern_size = 3
            smoothed = np.zeros(1)
            y = np.array(item[dif[0]], dtype=float)
            #print "for %s y[260] is %s before extrabads deleting" % (dif[0], y[260])
            y = np.delete(y, end_points)
            #print "for %s y[260] is %s after extrabads deleting" % (dif[0], y[260])
            y = np.delete(y, bads)
            #print "for %s y[260] is %s after bads deleting" % (dif[0], y[260])
            if len(y) - len(x):
                log.err("len(times): %s, len(%s): %s for %s" %
                        (len(x), dif[0], len(y), item['_id']))
                raise SystemExit("badbadbad")
            try:
                exc = track_looker(y, dif[1], kern_size)
            except Exception as e:
                log.err("while looking for initial exc points %s: %s",
                          dif[0], e)
                continue
            if exc:
                # log.msg("exc points in %s: %s",
                #           item['_id'], exc)
                try:
                    #there was some bug, TODO: test it and delete
                    if len(y) < 10: continue
                    smoothed = smoother(y, x, exc)
                except Exception as e:
                    log.err("error while smoothing y: %r, x: %r, exc: %s, error: %r"
                            % (y, x, exc, e))
                    # pic((y, x, exc),  item['_id'], 'smoother')
                while (exc and counter < 15):
                    exc = track_looker(smoothed, dif[1],
                                       kern_size + int(counter / 5) * 2)
                    smoothed = smoother(smoothed, x, exc)
                    counter += 1
                    # log.msg("smoothed while exc=%s in %s",
                    #           exc, item['_id'])
                if exc:
                    log.msg("still can't smooth %s[%s], exc=%s",
                             item['_id'], dif[0], exc)
                try:
                    tck = interpolate.splrep(x, smoothed, s=0)
                    # log.msg("prepared for interpolation with exc %s",
                    #           item['_id'])
                except Exception as e:
                    log.err("while preparing for interpolating %s[%s]: %s"
                        % (item['_id'], dif[0], e))
                    continue
                try:
                    result = interpolate.splev(item['times'], tck, der=0)
                    # log.msg("interpolated with exc %s", item['_id'])
                except Exception as e:
                    log.err("while interpolating %s[%s]: %s" %
                            (item['_id'], dif[0], e))
                    continue
                if dif[0] == 'alt':
                    result = place_alt_in_corridor(result)
                item[dif[0]] = result

            elif len(bads) > 0:
                # log.msg("bads points in %s: %s",
                #           item['_id'], bads)
                tck = interpolate.splrep(x, y, s=0)
                result = interpolate.splev(item['times'], tck, der=0)
                if dif[0] == 'alt':
                    result = place_alt_in_corridor(result)
                # log.msg("listed while bads=%s in %s",
                #           bads, item['_id'])
                item[dif[0]] = result
            elif len(extra_bads) > 0:
                item[dif[0]] = y
            log.msg("done for %s[%s]", item['_id'], dif[0])

    return datalist


def find_element(filename):
    root = etree.parse(filename)
    for element in root.iter():
        if element.attrib.get('type') == 'track':
            log.msg("Found track in %s", filename)
            return element.getparent()


def get_times_and_gl_num(element, filename):
    filename_glnum = filename.split('.')[-2]
    has = False
    for l in element.iter():
        if l.tag == 'FsInfo':
            gl_num = int(l.attrib.get('comp_pilot_id', filename_glnum))
            try:
                text_time = l.attrib['time_of_first_point']
                if not text_time.endswith('Z'):
                    text_time = ''.join((text_time, 'Z'))
                starttime = timegm(
                    time.strptime(text_time,
                                  "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError as e:
                log.err("Time conversion error for pilot %s: %r"% (gl_num, e))
                return None, None
            times_list = l.getchildren()[0]
            has = True
            break
    if not has:
        return None, None
    times = np.array(reduce(lambda x, y: x + y, map(lambda a: a.split(),
                                                    times_list.text.lstrip().rstrip().splitlines())),
                     dtype=int) + starttime
    log.msg("len(times) = %s for pilot %s", len(times), gl_num)
    return times, gl_num


def get_coords(element):
    has = False
    for l in element.iter():
        if l.tag == 'coordinates':
            has = True
            break
    if not has:
        return None, None, None
    ls = reduce(lambda x, y: x + y, map(lambda a: a.split(),
                                        l.text.lstrip().rstrip().splitlines()))
    lat, lon, alt = [], [], []
    for i, item in enumerate(ls):
        x = item.split(',')
        lat.append(x[1])
        lon.append(x[0])
        alt.append(x[2])
    lat = np.array(lat, dtype=float)
    lon = np.array(lon, dtype=float)
    alt = np.array(alt, dtype=int)
    log.msg("coords arrays len is %s, %s, %s", len(lat), len(lon),
              len(alt))
    return lat, lon, alt


def latitude(lat):
    """Convert gps coordinates. Use string, return string.
    >>> latitude('37550333S')
    '-37.917222'
    >>> latitude('37550333N')
    '37.917222'
    >>> latitude('3800002N')
    '38.000033'
    """
    dd_lat = int(lat[:2])
    mm_lat = lat[2:4]
    ssss_lat = lat[4:7]
    sep = '.'
    mm = round(float(sep.join((mm_lat, ssss_lat)))/60, 6)
    if lat[-1:] == "N":
        sign = ''
    else:
        sign = '-'
    return ''.join((sign, str(dd_lat + mm)))


def longitude(lon):
    """Convert gps coordinates
    >>> longitude('029072171E')
    '29.120285'
    >>> longitude('029072171W')
    '-29.120285'
    """
    dd_lon = int(lon[:3])
    mm_lon = lon[3:5]
    sep = '.'
    ssss_lon = lon[5:8]
    mm = round(float(sep.join((mm_lon, ssss_lon)))/60, 6)
    if lon[-1:] == "E":
        sign = ''
    else:
        sign = '-'
    return ''.join((sign, str(dd_lon + mm)))

def track_looker(y, maxdif, kern_size=3):
    """Go through 2-d array and eliminate highly-deviated points.
    maxdif - maximum allowed difference between point and smoothed point.
    Return tuple (list of bad points (int), lastitem (int)).
    If last point of y is bad point, then lastitem will be previous good point
    in kern_size region from the end of y, or y[-kern_size] if no good points
    in that region.

    """
    kern_size = int(kern_size)
    y = np.array(y, dtype=float)
    filtered = y.copy()
    filtered[0] = np.mean(filtered[:kern_size])
    filtered = signal.medfilt(filtered, kern_size)
    filtered[len(filtered) - 1] = np.mean(filtered[kern_size:])
    result = y - signal.medfilt(filtered, kern_size)
    bads = []
    for i, item in enumerate(result):
        if abs(item) > maxdif:
            bads.append(i)
    return bads

def smoother(y, x, exclude=[]):
    """Smooth y(x). exclude - list of points to exclude while smoothing.

    """
    exclude.sort()
    exclude.reverse()
    if not isinstance(y, np.ndarray):
        y = np.array(y, dtype=float)
    if not isinstance(x, np.ndarray):
        x = np.array(x, dtype=int)
    _x = np.delete(x, exclude)
    _y = np.delete(y, exclude)
    tck = interpolate.splrep(_x, _y, s=0)
    ynew = interpolate.splev(x, tck, der=0)
    return ynew


class Race(object):
    '''
    Base class for implementing race logic.
    '''

    type = 'race'
    wp_error = 30
    earth_radius = 6371000

    def __init__(self, task):
        '''
        task is a dict with information about waypoints:
        {date: str, p_amount: int, lat1: string, lon1: string, rad1: int,
        dist1: int, start: timestamp, end: timestamp, ...}
        Waypoint numeration starts from 1.
        '''
        self.task = task

    def process_point(self, point, last_wp):
        '''Do processing work.'''
        raise NotImplementedError("Process function hasn't been implemented.")

    def _in_next_wp(self, point, last_wp):
        if last_wp == self.task['p_amount']:
            return False
        if self._dist_to_wp(point, last_wp + 1) - self.task[
            ''.join(('rad', str(
                        last_wp + 1)))] < self.wp_error:
            return True
        return False

    def _dist_to_wp(self, point, wp_num):
        return self._dist_between(point,
                                  (self.task['lat' + str(wp_num)],
                                   self.task['lon' + str(wp_num)]))

    def _dist_between(self, point1, point2):
        """Return distance between two points in float."""
        lat1, lat2, lon1, lon2 = map(math.radians,
                                     map(float, [point1[0], point2[0], point1[1], point2[1]]))

        d_lat = lat2 - lat1
        d_lon = lon2 - lon1
        df = 2 * math.asin(math.sqrt(math.sin(d_lat / 2) ** 2 + math.cos(lat1
        ) * math.cos(lat2) * math.sin(d_lon / 2) ** 2))
        return int(df * self.earth_radius)

    def is_finished(self, state, point):
        raise NotImplementedError("Process function hasn't been implemented.")

    def get_ss_time(self,*args):
        """
        Return track start time for offline (trfltfs)
        @param args:
        @type args:
        @return:
        @rtype:
        """
        return self.task['start']

    def get_finish_time(self, times, lat, lon, ld):
        """
        For offline track processing
        @param times:
        @type times:
        @param lat:
        @type lat:
        @param lon:
        @type lon:
        @param ld: array with left_distances
        @type ld: list
        @return:
        @rtype:
        """
        times = list(times)
        result = None
        es_times, real_times_f, ks = intersect(times, lat, lon,
                                               self.task['es_lat'], self.task['es_lon'], self.task['es_rad'])
        es_goal_dist = self.task['dist' + str(self.task['p_amount'] - 1)]
        if real_times_f:
            for j, k in enumerate(es_times):
                if ld[times.index(k)] - es_goal_dist < self.task['es_rad']:
                    result = real_times_f[j]
                    break
        return result

class RaceToGoal(Race):
    '''
    Pilot must to collect all waypoints and finish first. Start time fixed,
    end of speed section point fixed.
    '''
    type = 'racetogoal'

    def process_point(self, point, last_wp):
        """
        @type point: (lat, lon)
        @param point: new point in a track for which parameters will be
        calculated.
        @param last_wp: last taken waypoint
        @type last_wp: int
        @return: left distance in meters and last visited waypoint.
        @rtype: (distance, last taken waypoint)
        """
        if last_wp >= self.task['p_amount']:
            return (0, last_wp)
        if self._in_next_wp(point, last_wp):
            return (self._left_distance(point, last_wp), last_wp + 1)
        return (self._left_distance(point, last_wp), last_wp)

    def _left_distance(self, point, last_wp):
        '''
        @param point:
        @type point: (lat, lon)
        '''
        next_point = (self.task[''.join(('lat', str(last_wp + 1)))],
                      self.task[''.join(('lon', str(last_wp + 1)))])
        return self._dist_between(point, next_point) + self.task[
            ''.join(('dist', str(
                last_wp + 1)))]

    def is_finished(self, state, point):
        """
        TODO: This function is buggy when goal and es don't coincide.
        @param state: current pilot state
        @type state: str
        @param point:
        @type point: (lat, lon)
        @return: is pilot finished or not
        @rtype: boolean
        """
        if state != 'flying':
            return False
        dist_to_es = self._dist_between(point, (self.task['es_lat'],
                                                self.task['es_lon']))
        if dist_to_es <= self.task['es_rad']:
            return True

class SpeedRun(Race):
    '''
    Winner is a pilot who collected all waypoints and was the fastest.
    Pilot has a choice of start time in given time interval.
    '''
    type = 'speedrun'

    def get_ss_time(self, times, lat, lon):
        """
        TODO: early I've thinked that this behaviour is buggy, check it.
        TODO: this if for offline processing only.
        @param times: array with times
        @type times: np.array(dtype=int)
        @param lat: array with latitudes
        @type lat:
        @param lon:
        @type lon:
        """
        ss_times, real_times, ks  = intersect(times, lat, lon,
                                              self.task['ss_lat'], self.task['ss_lon'], self.task['ss_rad'])
        if len(real_times) == 1:
            return real_times[0]
        if len(real_times) > 1:
            # check this, why -2?
            return real_times[len(real_times) - 2]

class XC(Race):
    '''
    "Vector run". No concrete start time, task can be without waypoints. Pilots
    has a bearing or a vector of flight direction. This vector can begin from
    last point, sometimes start can be last point. Winner is the man with
    longest projection on a vector.
    Return tuple(distance from start:int, last taken waypoint number).
    '''

    type = 'xc'

    def process_point(self, point, last_wp):
        """
        @type point: (lat, lon)
        @param point: new point in a track for which parameters will be
        calculated.
        @param last_wp: last taken waypoint
        @type last_wp: int
        @return: taken distance in meters and last visited waypoint.
        @rtype: (distance, last taken waypoint)
        """
        DIMA_IS_DOLBAEB = False
        BUT_DIMA_IS_DOLBAEB = True
        if last_wp >= self.task['p_amount'] and DIMA_IS_DOLBAEB:
            return (self._get_projection(point) + (self.task['dist1'] - self.task['dist' + str(self.task['p_amount'])]),
                    self.task['p_amount'])
        if last_wp >= self.task['p_amount'] and not DIMA_IS_DOLBAEB:
            return (self._get_projection(point) + self.task['dist1'],
                    self.task['p_amount'])
        if self._in_next_wp(point, last_wp):
            return (self.task['dist1'] - self.task[
                ''.join(('dist', str(last_wp + 1)))],
                    last_wp + 1)
        return (self._passed_distance(point, last_wp), last_wp)

    def _get_projection(self, point):
        start = (self.task[''.join(('lat', str(self.task['p_amount'])))],
                 self.task[''.join(('lon', str(self.task['p_amount'])))])
        distance = self._dist_between(point, start)
        if self.task.get('bearing'):
            cos = math.cos(math.radians(self._bearing(start, point) -
                                        self.task['bearing']))
            result = int(distance * cos)
        else:
            result = distance
        if result < 0:
            result = 0
        return result

    def _bearing(self, points, pointe):
        '''Return an initial bearing between points.'''
        point1 = (float(points[0]), float(points[1]))
        point2 = (float(pointe[0]), float(pointe[1]))
        if point1 == point2:
            return 0
        lat1 = point1[0] * math.pi / 180
        lat2 = point2[0] * math.pi / 180
        lon1 = point1[1] * math.pi / 180
        lon2 = point2[1] * math.pi / 180

        cl1, cl2 = math.cos(lat1), math.cos(lat2)
        sl1, sl2 = math.sin(lat1), math.sin(lat2)
        cdelta = math.cos(lon2 - lon1)
        sdelta = math.sin(lon2 - lon1)

        # bearing calculation
        x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
        #        print "x ", x
        y = sdelta * cl2
        #        print "y ", y
        try:
            z = math.degrees(math.atan(y / x))
        except ZeroDivisionError:
            return 0
            #        print "z ", z
        if x < 0:
            z = z + 180
        return (z + 360.) % 360.

    def _passed_distance(self, point, last_wp):
        next_point = (self.task[''.join(('lat', str(last_wp + 1)))],
                      self.task[''.join(('lon', str(last_wp + 1)))])

        passed_wps_dist = self.task['dist1'] - self.task['dist' + str(last_wp)]
        dist_btw_wps = self.task['dist' + str(last_wp)] - self.task[
            'dist' + str(
                last_wp + 1)]

        dist_to_next_wp = dist_btw_wps - self._dist_between(point, next_point)

        result = passed_wps_dist + dist_to_next_wp
        if result < 0:
            result = 0
        return result

    def get_finish_time(self, *args):
        """
        For offline track processing.
        @param args:
        @type args:
        @return:
        @rtype:
        """
        return None

    def is_finished(self, state, point):
        """
        TODO: This function is buggy when goal and es don't coincide.
        @param state: current pilot state
        @type state: str
        @param point:
        @type point: (lat, lon)
        @return: is pilot finished or not
        @rtype: boolean
        """
        return False


class BatchProcessor(object):

    racetypes = dict(racetogoal=RaceToGoal, OpenDistance=XC, speedrun=SpeedRun)
    dic_lists = ['lat', 'lon', 'alt', 'times', 'v_speed', 'left_distance']

    def __init__(self, task, race_id):
        self.task = task
        self.race_id = race_id
        self.race = self.racetypes[self.task.get('race_type',
                                                 'racetogoal')](self.task)

    def calculate(self, data):
        result = []
        for i, dic in enumerate(data):
            result.append(self._make_clean(self._calculate_values(dic)))
        return result

    def _calculate_values(self, dic):
        log.msg("got %s", dic['_id'])

        dic['times'] = np.array(dic['times'], dtype=int)
        dic['v_speed'] = self._calc_vspeed(dic['alt'], dic['times'])
        dic['h_speed'] = self._calc_hspeed(dic['lat'], dic['lon'],
                                           dic['times'])

        # new calculation
        dic['left_distance'] = []
        last_wp = 1
        for i, item in enumerate(dic['times']):
            ld, last_wp = self.race.process_point((dic['lat'][i],
                                                   dic['lon'][i]), last_wp)
            dic['left_distance'].append(ld)
        log.msg("last from left_distance for %s: %s",
              dic['_id'], dic['left_distance'][len(dic['left_distance']) - 1])

        # new intersection time calculation
        dic['ss_time'] = self.race.get_ss_time(dic['times'], dic['lat'],
                                               dic['lon'])
        finish_time = self.race.get_finish_time(dic['times'], dic['lat'],
                                            dic['lon'], dic['left_distance'])
        if finish_time:
            dic['finish_time'] = finish_time
            # intersection time calculation

        log.msg("start and finish times for: %s, %s",
                  dic.get('ss_time'), dic.get('finish_time'))
        log.msg("Pilot %s processed", dic['_id'])
        return dic

    def _make_clean(self, dic):
        """
        Clean received dictionary to make it insertable in CouchDB
        @param dic:
        @type dic:
        """
        log.msg("cleaning...")
        types = {'alt': int, 'times': int, 'left_distance': int,
                 'lat': str, 'lon': str, 'v_speed': float, 'h_speed': float}
        dic['_id'] = '_'.join((dic['_id'], str(self.race_id)))

        for i in ['lat', 'lon', 'alt', 'times', 'left_distance', 'v_speed', 'h_speed']:
            dic[i] = list(dic[i])

        for key in ['finish_time', 'ss_time']:
            if dic.has_key(key):
                dic[key] = int(dic[key])

        for key in types.keys():
            for i, elem in enumerate(dic[key]):
                dic[key][i] = types[key](elem)

        log.msg("cleaned")
        return dic

    def _calc_hspeed(self, lat, lon, times):
        """
        Calculate horizontal speed for tracks parsing.
        @param lat: latitudes
        @type lat: list
        @param lon: longitudes
        @type lon: list
        @param times: times
        @type times: C{np.ndarray}, dtype=int
        @return horizontal speeds
        @rtype list
        """
        result = [1]
        for i in xrange(len(times) - 1):
            result.append(point_dist(lat[i], lon[i], lat[i+1],
                                        lon[i+1]))
        result = np.array(result) / np.ediff1d(times, to_begin=1)
        np.around(result, decimals=1, out=result)

        if max(result) > MAX_VERT_SPEED:
            log.err("max and min of v_speed: %s %s" %
                    (max(result), min(result)))
        return  result

    def _calc_vspeed(self, alt, times):
        """

        @param alt:
        @type alt:
        @param times:
        @type times:
        """
        result = np.ediff1d(alt, to_begin=1) / np.ediff1d(times,
                                                          to_begin=1)
        np.around(result, decimals=2, out=result)

        if max(result) > MAX_VERT_SPEED:
            log.err("max and min of v_speed: %s %s" %
                    (max(result), min(result)))
        return result

def intersect(times, lat, lon, wp_lat, wp_lon, wp_rad):
    """Find intersection of a track with waypoint.  Return list of times."""
    # TODO: use numpy and correct algoritms for intersection finding. Fix this porn.

    times = list(times)
    lat = list(lat)
    lon = list(lon)
    intersection_times = []
    real_times = []
    ranges = []
    ss_times_temp = []
    ks = []
    for i, item in enumerate(times):
        dist = point_dist(lat[i], lon[i], wp_lat, wp_lon)
        if -1 * (WP_ERROR + 170) < wp_rad - dist< (WP_ERROR + 170):
            ranges.append(wp_rad - dist)
            ss_times_temp.append(item)
        else:
            if len(ranges) > 1:
                mult = 1
                points = []
                closest_point = min(map(abs, ranges))
                last_point = 0
                try:
                    last_point = ranges.index(closest_point)
                except ValueError:
                    # closest_point is negative
                    last_point = ranges.index(-closest_point)
                    if last_point < (len(ranges) - 1):
                        last_point += 1
                    # All we need is a index of first point in a circle.
                if last_point:
                    p_index = times.index(ss_times_temp[last_point])
                    intersection_times.append(times[p_index])
                    #l_range = me.point_dist(lat[p_index], lon[p_index], wp_lat, wp_lon)
                    #f_range = me.point_dist(lat[p_index - 1], lon[p_index - 1], wp_lat, wp_lon)
                    l_range = ranges[last_point]
                    f_range = ranges[last_point - 1]
                    l_time = times[p_index]
                    f_time = times[p_index - 1]
                    if l_range == f_range:
                        log.err("l_range is equal f_range and is %s for time %s"
                        % (l_range, l_time))
                        try:
                            f_range = ranges[last_point - 2]
                            log.msg("will use f_range = %s instead", f_range)
                        except IndexError:
                            log.err("Can't do anything, continue")
                            continue
                    k = abs(f_range / (l_range - f_range) )
                    ks.append(k)
                    real_times.append(int((l_time - f_time) * k) + f_time)
                ranges = []
                ss_times_temp = []
            else:
                ranges = []
                ss_times_temp = []
    # log.msg("intersection times, real_times, ks: %s %s %s", intersection_times, real_times, ks)
    return (intersection_times, real_times, ks)
