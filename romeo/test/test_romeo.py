import unittest
import os
import sys

DIRECTORY = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(DIRECTORY,'..','lib'))

import romeo

MY_SWEET_ENVIRONMENT = "romeo-test"
MY_SWEET_ROMEO_CONFIG = """
- NAME: %(environment)s
- SERVER:
      HOSTNAME: %(hostname)s
      ARTIFACTS: []
- SERVER:
      HOSTNAME: not_here
      ARTIFACTS: []
"""

FAKE_HOST = 'foo.thishostdoesnotexist.net'
FAKE_ENV = 'nosuchenv'

#Note ordering matters
class TestRomeo(unittest.TestCase):
    def setUp(self):
        self.mysweetconfig = os.path.join(DIRECTORY,'sweetenv.yaml')
        if os.path.exists(self.mysweetconfig):
            os.unlink(self.mysweetconfig)
        hostname = romeo.MYHOSTNAME
        environment = MY_SWEET_ENVIRONMENT
        data = MY_SWEET_ROMEO_CONFIG % locals()
        f = open(self.mysweetconfig, 'wb')
        f.write(data)
        f.close()
        #prime romeo data
        romeo.reload(datadir=DIRECTORY)

    def tearDown(self):
        if os.path.exists(self.mysweetconfig):
            os.unlink(self.mysweetconfig)

    def test_crisis(self):
        self.assertRaises(romeo.IdentityCrisis, romeo.whoami, FAKE_HOST)
        self.assertRaises(romeo.EnvironmentalError, romeo.getEnvironment, FAKE_ENV)

    def test_me(self):
        me = romeo.whoami()
        self.assertIsInstance(me, romeo.foundation.RomeoKeyValue)
        env = romeo.getEnvironment(MY_SWEET_ENVIRONMENT)
        self.assertIsInstance(env, romeo.foundation.RomeoKeyValue)
        # this next one may be confusing so i'll spell it out
        # server is related to env and env is related to server
        self.assertEqual(env.isRelated(me), True)
        self.assertEqual(me.isRelated(env), True)
        # server is a child of env and server has ancestor env
        self.assertEqual(env.isChild(me), True)
        self.assertEqual(me.isAncestor(env), True)
        x = list(me.search('NAME'))[0].VALUE
        self.assertIs(romeo.getEnvironment(x), env)
        self.assertEqual(x, MY_SWEET_ENVIRONMENT)
        self.assertListEqual(sorted(me.keys()), ['ARTIFACTS','HOSTNAME','SERVER'])

    def test_hostdb(self):
        env = romeo.getEnvironment(MY_SWEET_ENVIRONMENT)
        hostdb = romeo.hostdb.node_constructor(env)
        self.assertListEqual(sorted(hostdb.keys()), ['ARTIFACTS', 'FILENAME', 'HOSTNAME', 'NAME', 'SERVER'])
        self.assertEqual(hostdb.get('FILENAME'), self.mysweetconfig)
        self.assertEqual(hostdb.get('NAME'), MY_SWEET_ENVIRONMENT)
        envDict = hostdb.copy()
        self.assertIsInstance(envDict, dict)
        self.assertIs(romeo.hostdb.whoami(romeo.MYHOSTNAME).entity, romeo.whoami())

if __name__ == '__main__':
    unittest.main()
