

class DeferredImportingDict(object):
    def __init__(self, d):
        self._dict = d
        self._cache = {}

    def keys(self):
        return self._dict.keys()

    def __contains__(self, key):
        return key in self._dict

    def __getitem__(self, key):
        if not key in self:
            raise KeyError(key)

        if not key in self._cache:
            self._cache[key] = self._import(self._dict[key])

        return self._cache[key]

    @classmethod
    def _import(cls, location):
        """ Given the string 'module1.module2:Object', returns Object. """
        mod_name, obj_name = location = location.strip().split(':')
        tokens = mod_name.split('.')

        fromlist = '[]'
        if len(tokens) > 1:
            fromlist = '.'.join(tokens[:-1])

        module = __import__(mod_name, fromlist=fromlist)

        try:
            return getattr(module, obj_name)
        except AttributeError:
            raise ImportError("%r not found in %r" % (obj_name, mod_name))
