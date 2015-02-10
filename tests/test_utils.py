import unittest2

import bugwarrior.utils


class UtilsTest(unittest2.TestCase):
    def setUp(self):
        self.d = bugwarrior.utils.DeferredImportingDict({
            'chain': 'itertools:chain',
        })

    def test_importing_dict_access_success(self):
        item = self.d['chain']
        import itertools
        self.assertEquals(item, itertools.chain)

    def test_importing_dict_contains_success(self):
        self.assertEquals('chain' in self.d, True)

    def test_importing_dict_contains_failure(self):
        self.assertEquals('nothing' in self.d, False)

    def test_importing_dict_keys(self):
        self.assertEquals(set(self.d.keys()), set(['chain']))
