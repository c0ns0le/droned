import unittest
import os
import sys
import weakref

DIRECTORY = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(DIRECTORY,'..','lib'))

try: #newer python versions
    from io import BytesIO
except ImportError: #legacy python
    from StringIO import StringIO as BytesIO

from romeo.entity import Entity

class TestEntity(Entity):
    reapable = True #will gc once it is out of scope
    serializable = True
    def __init__(self, name): # you must subclass Entity for parameters
        self.name = name

    def __getstate__(self): #required for serialization
        return {'name': self.name}

    @staticmethod
    def construct(state): #required for deserialization
        return TestEntity(state['name'])


class TestEntities(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(Entity.reapable, False)
        self.assertEqual(Entity.serializable, False)
        # not implemented by default, results in a type error by design
        self.assertRaises(TypeError, Entity.construct, {'name': 'Test'})
        # test invalid buffer
        self.assertRaises(TypeError, Entity.deserialize, None)
        self.assertListEqual(list(Entity.objects), [])

    def test_defaultInstance(self):
        # create an instance so we can test the rest of the interfaces
        inst = Entity() # Note by default no parameters are possible
        # not implemented by default, results in a type error by design
        self.assertRaises(TypeError, inst.serialize)
        self.assertEquals(str(inst), 'Entity()')
        self.assertListEqual(list(Entity.objects), [inst])
        self.assertEqual(weakref.getweakrefcount(inst), 1)
        self.assertEqual(Entity.isValid(inst), True)
        Entity.delete(inst) #you must reap the instance yourself
        self.assertEqual(Entity.isValid(inst), False)

    def test_singleton(self):
        obj1 = TestEntity('test')
        obj2 = TestEntity('test')
        self.assertIs(obj1, obj2)

    def test_serializeAndDeserialize(self):
        obj1 = TestEntity('test')
        buf = BytesIO()
        buf.write(obj1.serialize())
        buf.seek(0)
        obj2 = TestEntity.deserialize(buf)
        self.assertIs(obj1, obj2)
        buf.close()

    def test_reapable(self):
        obj = TestEntity('test')
        self.assertEqual(obj.serializable, True)
        self.assertIsInstance(obj.__weakref__, weakref.ref)
        #this should only ever be equal to 1 otherwise it is a bug
        self.assertEqual(weakref.getweakrefcount(obj), 1)

    def test_lookup(self):
        obj1 = TestEntity('test')
        self.assertIn(obj1, list(TestEntity.objects))
        self.assertEqual(TestEntity.isValid(obj1), True)
        self.assertEqual(TestEntity.exists('test'), True)

    def test_eviction(self):
        obj1 = TestEntity('test')
        TestEntity.delete(obj1) #force eviction from lookup table
        self.assertEqual(TestEntity.exists('test'), False)
        self.assertEqual(TestEntity.isValid(obj1), False)

if __name__ == '__main__':
    unittest.main()
