from twisted.trial import unittest
from gorynych.processor.services.visualization import parse_result


class TestTrackData(unittest.TestCase):

    def test_parse_result(self):
        raw_data = ['45.385', '23.4318', '1744', '-1.67', '6.2', '4157']
        result = parse_result(raw_data)
        self.assertEquals(
            result, {'crds': [45.385, 23.4318, 1744], 'spds': [6.2, -1.67], 'dist': 4157})
