###############################################################################
#   Copyright 2006 to the present, Orbitz Worldwide, LLC.
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
 
"""This module implements DroneD's logging facilities."""
import sys, os, time, glob
from twisted.python.failure import Failure
from twisted.python.log import FileLogObserver, StdioOnnaStick
from twisted.python.logfile import DailyLogFile
 
class DailyPurgingLogFile(DailyLogFile):
    """A log file that is rotated daily (at or after midnight localtime).
 
       A maxRotatedFiles of None disables purging.
    """
    def __init__(self, *args, **kwargs):
        """
        Create a log file rotating on length.
 
        @param name: file name.
        @type name: C{str}
        @param directory: path of the log file.
        @type directory: C{str}
        @param defaultMode: mode used to create the file.
        @type defaultMode: C{int}
        @param maxRotatedFiles: if not None, max number of log files the class
            creates. Warning: it removes all log files above this number.
        @type maxRotatedFiles: C{int}
        """
        self.maxRotatedFiles = kwargs.pop('maxRotatedFiles', None)
        DailyLogFile.__init__(self, *args, **kwargs)
        self._logger = logWithContext(type='console')
 
    def notification(self, message):
        """
        only used when logs are deleted
        """
        self._logger(message)
 
    def listLogs(self):
        """
        Return sorted list of logfile names.
        """
        logs = glob.glob("%s.*" % self.path)
 
        def sort_algorithm(name):
            timeobj = time.strptime(name, self.path + '.%Y_%m_%d')
            return time.mktime(timeobj)
 
        return sorted(logs, key=sort_algoritm)
 
    def rotate(self):
        """
        Rotate the file and create a new one.
 
        If it's not possible to open new logfile, this will fail silently,
        and continue logging to old logfile.
 
        Old log files will be automatically purged.
        """
        #daily rotation first
        DailyLogFile.rotate(self)
        if not self.maxRotatedFiles:
            return
        if not (os.access(self.directory, os.W_OK) and os.access(self.path, os.W_OK)):
            return
        logs = self.listLogs()
        while len(logs) >= self.maxRotatedFiles:
            l = logs.pop(0)
            #this should never match, but just make sure
            if l.endswith('log'): continue
            self.notification('deleting %s' % l)
            os.remove(l)
 
 
class MyLogObserver(FileLogObserver):
    timeFormat = "[%Y-%m-%d %H:%M:%S]"
 
 
class StdioKabob(StdioOnnaStick):
    def write(self, data):
        data = (self.buf + data).split('\n')
        self.buf = data[-1]
        for message in data[:-1]:
            log(message)
 
    def writelines(self, lines):
        for line in lines:
            self.write(line)
 
#Initialization API
logs = {}
 
def logToStdout(timestamp=False):
    """Call this to cause all log messages to go to stdout"""
    logs['console'] = MyLogObserver(sys.stdout)
    if not timestamp:
        logs['console'].timeFormat = "" #get rid of that
    sys.stdout = StdioKabob(0)
    sys.stderr = StdioKabob(1)
 
 
def logToDir(directory='logs', LOG_TYPE=('console',), OBSERVER=MyLogObserver):
    """Call this to write logs to the specified directory,
       optionally override the FileLogObserver.
    """
    args = ()
    kwargs = {'maxRotatedFiles': 7} #seven days of logs by default
    try: import config #fix for early logging
    except: config = None #also works around daemon wrappers
    if config and config.RETAINED_LOGS:
        kwargs.update({'maxRotatedFiles': config.RETAINED_LOGS})
    for name in LOG_TYPE:
        path = os.path.join(directory, name + '.log')
        logfile = DailyPurgingLogFile.fromFullPath(path, *args, **kwargs)
        logs[name] = OBSERVER(logfile)
 
 
#Logging API
def log(message="", **context):
    """Log a message, with some optional context parameters"""
    event = create_log_event(message, context)
    if event.get('discard'):
        return
    destination = get_destination(event)
    if destination:
        destination.emit(event)
    else:
        print "<<<UNHANDLED LOG EVENT>>> %s" % str(event)
 
 
def logWithContext(**context):
    """Create a log() function that assumes the given context parameters by default"""
    destination = get_destination(context)
    def _log(message="", **kwargs):
        myContext = {}
        myContext.update(context)
        myContext.update(kwargs)
        log(message, **myContext)
    return _log
 
 
#Internal functions
def create_log_event(message, context):
    """Internal function used to convert droned log events to Twisted log events"""
    try: import config #fix for early logging
    except: config = None #also works around daemon wrappers
    event = {}
    event.update(context)
    event['message'] = message
    event['time'] = time.time()
    event['system'] = context.get('system') or context.get('type') or 'console'
 
    if event.get('error'):
        event['isError'] = True
 
    if event.get('warning'):
        event['message'] = '[WARNING] %s' % event['message']
 
    if event.get('excessive') and config and not config.EXCESSIVE_LOGGING:
        event['discard'] = True
 
    event['message'] = (event['message'],) #stupid hack for twisted...
    return event
 
 
def get_destination(event):
    """Internal function used to route a log event to a particular LogObserver (log file)"""
    if 'type' in event and event['type'] in logs:
        return logs[ event['type'] ]
 
    elif 'route' in event and event['route'] in logs:
        return logs[ event['route'] ]
 
    return logs.get('console')
 
 
#Conveniences
debug = logWithContext(type='debug')
 
def err(message="", **context):
    failure = Failure()
    if message:
        message += '\n'
    message += failure.getTraceback()
    log(message, **context)
    return failure
