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

import re
from romeo.directives import Directive, DirectiveException
from romeo.decryption import setup
import sys

class Decrypt(Directive):
    name = 'decrypt'
    modes = ['pre']

    def is_valid(self):
        '''for this directive we have no extended validation.
           we leave it up to the outer structured data parser
           to determine if our arguments are valid.
        '''
        return

    def apply(self):
        """decrypt the configuration in memory"""
        out = []
        self.data.seek(0)
        for line in self.get_lines():
            m = self.used_pattern.search(line)
            if not m:
                out.append(line)
                continue
            try:
                #prepares this object for later decryption
                setup(line[m.start():m.end()])
            except:
                msg = "Failed to setup decryption directive matching line\n"
                msg += "%s" % str(line)
                msg += "\n"
                raise DirectiveException(msg)
            out.append(line)
        return "".join(out)
