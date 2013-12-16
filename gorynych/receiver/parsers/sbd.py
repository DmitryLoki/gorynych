"""
That's not a tracker protocol parser but a parser to handle
data sent by satellite channel, so it could be used by any tracker.
"""

import struct

IEI_SIZE = struct.Struct('!BH')
IEI_1 = struct.Struct('!I15sBHHI')


def unpack_sbd(data):
    msg = dict()

    def parse_element(data, iei, cursor, size):
        if iei == 1:  # header
            msg['cdr'], msg['imei'], msg['MOStatus'], msg['MOMSN'],\
                msg['MTMSN'], msg['time'] = IEI_1.unpack_from(data, cursor)
        elif iei == 2:  # message
            msg['data'] = data[cursor:cursor + size]

    protocol_revision, total = IEI_SIZE.unpack_from(data)
    total += 3
    cursor = 3
    if len(data) != total:
        raise ValueError('Unexpected end of an SBD frame')
    while cursor < total:
        iei, size = IEI_SIZE.unpack_from(data, cursor)
        cursor += 3
        parse_element(data, iei, cursor, size)
        cursor += size
    return msg
