###############################################################################
#   Copyright 2012 to the present, Orbitz Worldwide, LLC.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
###############################################################################

import os
import sys
import traceback
class _decryptor(object):
    def __init__(self):
        self._storage = {}
        m = self.__class__.__module__
        relpath = sys.modules[m].__file__
        reldir = os.path.split(relpath)[0]
        fulldir = os.path.realpath(reldir)
        for fileobj in os.listdir(fulldir):
            if fileobj == '__init__.py': continue
            if not fileobj.endswith('.py'): continue
            m = fileobj[:-3]
            try: mod = self.load_module(m)
            except:
                traceback.print_exc()
                continue
            try: self.process_module(mod)
            except:
                traceback.print_exc()
                continue

    def load_module(self, modname):
        """load a decryption plugin module by name"""
        return __import__(__name__ + '.' + modname, {}, {}, [modname])

    def process_module(self, module):
        """process the plugin module for methods"""
        assert hasattr(module, '__all__')
        methods = module.__all__
        for method in methods:
            obj = vars(module)[method]
            if not hasattr(obj, '__call__'): continue
            self._storage[method] = obj

    def __call__(self, *args):
        """execute the decryption method now"""
        return self._storage[args[0]](*args[1:])

_decrypt = _decryptor()
from romeo.entity import ParameterizedSingleton

class _Decryption(object):
    """encrypted data bucket, that decrypts the data on the fly."""
    value = property(lambda s: _decrypt(*s._data))
    def __init__(self, directive_string):
        self._data = self.extract_args(directive_string)

    @staticmethod
    def extract_args(match_str):
        match = match_str.strip().replace("}","")
        match = match.split(" ")[1].strip()
        match = match.split(",")
        return tuple(match)

#make this object unique based on the input parameters
_Decryption = ParameterizedSingleton('_Decryption', (_Decryption,), {})

def setup(directive_string):
    """takes a directive string and prepares the value for later extraction."""
    #the following is our only safety check
    assert len(_Decryption.extract_args(directive_string))
    _Decryption(directive_string)

def decrypt(directive_string):
    """takes a directive string and returns the decrypted value."""
    if not _Decryption.exists(directive_string):
        return directive_string
    return _Decryption(directive_string).value

#expose the class as a callable
__all__ = ['decrypt', 'setup']
