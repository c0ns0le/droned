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

try:
    import cPickle as _pickle
except ImportError:
    import pickle as _pickle
_json = None
try:
    import simplejson as _json
except ImportError:
    try:
        import json
    except ImportError: pass
#this try catch is for the test at the bottom
try:
    from romeo.namespace import namespace
except ImportError:
    namespace = {}
#allocate a namespace for entities
namespace.update({'entities': {}})

import weakref

class InValidEntity(Exception): pass

def _weak_decorator(func):
    """Provides a work around for recursive creation of entities in
       an entities constructor. That would otherwise lead to runtime
       exceptions.
    """
    def decorator(cls, *args, **kwargs):
        result = func(cls, *args, **kwargs)
        if isinstance(result, weakref.ref):
            return result()
        instanceID = result._instanceID
        if getattr(result, 'reapable', False):
            namespace['entities'].get(
                result.__class__.__name__, {}
            ).pop(instanceID, None)
        else:
            namespace['entities'][result.__class__.__name__].update(
                {instanceID: result}
            )
        cls._instanceMap[instanceID] = weakref.ref(
            result, #making sure we clean up the map dict
            lambda x: cls._weak_callback(instanceID,x)
        )
        return cls._instanceMap[result._instanceID]()
    return decorator

class ParameterizedSingleton(type):
    """Metaclass that makes class instances uniquely identified by constructor 
       args. Basically it is a convenient way to avoid having to lookup 
       existing instances or duplicating objects.

       All instances are tracked with weak references, but cached by default.
       If you want to enable automatic garbage collection on instances that
       are not strongly referenced you must set a ``reapable`` attribute on 
       your class or in your constructor to the value of logical True.
    """
    def __init__(classObj, name, bases, members):
        super(ParameterizedSingleton, classObj).__init__(name, bases, members)
        classObj._instanceMap = {}
        classObj.objects = ObjectsDescriptor()
        #initialize namespace
        if name not in namespace['entities']:
            namespace['entities'][name] = {}

    @staticmethod
    def _safeID(*args, **kwargs):
        instanceID = (args, tuple( sorted( kwargs.items() ) ))
        try:
            hash(instanceID)
            return instanceID
        except TypeError:
            return hash(_pickle.dumps(instanceID))

    def _weak_callback(classObj, instanceID, obj):
        classObj._instanceMap.pop(instanceID, None)

    @_weak_decorator #we need this decorator for edge cases
    def __call__(classObj, *args, **kwargs):
        """We will construct or look up an instance based on the
           given arguments.

           we return an instance of L{classObj} and track instance
           with a weak reference so that we can manage memory. Note
           by default objects will cache with a reference to self,
           which will prevent gc from collecting the object. You
           must state in the class data or instance constructor
           that this object is ``reapable``.
        """
        instanceID = classObj._safeID(*args, **kwargs)
        if instanceID not in classObj._instanceMap:
            classObj._instanceMap[instanceID] = classObj.__new__(
                classObj,
                *args,
                **kwargs
            )

            #classObj._instanceMap[instanceID].__prevent_gc__ = False
            classObj._instanceMap[instanceID]._instanceID = instanceID
            # This will be converted to a weakref shortly
            # so we need to make sure the instance doesn't
            # gc unless it is suppossed to.  The decorator
            # on this method will take care of breaking the 
            # reference for us.

            try: # properly destroy the instance map allocation on failure
                classObj._instanceMap[instanceID].__init__(*args, **kwargs)
            except:
                if instanceID in classObj._instanceMap:
                    del classObj._instanceMap[instanceID]
                raise #re-raise the original exception

        return classObj._instanceMap[instanceID]

    def exists(classObj, *args, **kwargs):
        """Checks to see if an instance of the class has already been created 
           with the given parameters. Returns a boolean.
        """
        instanceID = classObj._safeID(*args, **kwargs)
        return instanceID in classObj._instanceMap

    def delete(classObj, instance):
        """Deletes the stored reference to an instance of the class."""
        for instanceID, _instance in classObj._instanceMap.items():
            if isinstance(_instance, weakref.ref):
                _instance = _instance()
            if _instance is instance:
                #break the circular reference if it exists
                namespace['entities'].get(
                    _instance.__class__.__name__,
                    {}
                ).pop(instanceID, None)
                classObj._instanceMap.pop(instanceID, None)
                return

    def isValid(classObj, instance):
        """Returns True if the given instance has not been previously deleted, 
           False otherwise
        """
        return classObj._instanceMap.get(
            instance._instanceID,
            lambda: None
        )() is instance

    def isStandard(classObj, instance):
        """Returns True if the given instance's parameters were hashable by 
           at instance creation time
        """
        if not classObj.isValid(instance):
            return False #appear complex if object is no longer referenced
        return isinstance(instance._instanceID, tuple)


class ObjectsDescriptor(object):
    """Descriptors are awesome. For a quick primer see 
       http://users.rcn.com/python/download/Descriptor.htm
    """
    def __get__(self, ownerInstance, ownerClass):
         return self.__safe_itervalues__(ownerClass)

    def __safe_itervalues__(self, ownerClass):
        """Works around RuntimeError Exception whenever an Entity is marked
           for deletion, yet the Entity.objects is still being iterated
           over. This is also safe in the event of automatic gc.
        """
        #sacrifices speed and simplicity for safety
        for clsname in ownerClass._instanceMap.keys():
            #items in the instanceMap are weak references
            val = ownerClass._instanceMap.get(
                clsname, lambda: None
            )() #now we have a real instance
            if not val: continue #could have gc'd
            yield val
        #optimizations welcome provided it passes the test at the bottom

    def __set__(self, ownerInstance, value):
        raise AttributeError("Attempt to write to a read-only data descriptor")


class Entity(object):
    """Abstract base class for models"""
    COMPLEX_CONSTRUCTOR = property(lambda s: not s.__class__.isStandard(s))
    serializable = False
    reapable = False

    def serialize(self, encode='pickle'):
        """This method is used only by the Journal service to persist the state
           of objects as returned by their custom __getstate__() method.

           @param encode (str) <pickle|json>
           @raise NotImplemented
           @return (str) ``encode``.dumps()
        """
#TODO should we mark the entity invalid on failed serialization?
        state = self.__getstate__()
        state['__module__'] = self.__class__.__module__
        state['__class__'] = self.__class__.__name__
        if encode == 'pickle':
            return _pickle.dumps(state, protocol=-1)
        elif encode == 'json' and _json:
            return _json.dumps(state)

    @staticmethod
    def deserialize(buffer, decode='pickle'):
        """This method is used only by the Journal service to reconstruct 
           serialized objects by calling the custom ``construct(state)`` 
           method of their class.

           @param buffer (a ``.read()``-supporting file-like object)
           @param decode (str) <pickle|json> default='pickle'

           @raise AssertionError
           @return Entity instance
        """
        state = None
        if decode == 'pickle':
            state = _pickle.load(buffer)
        elif decode == 'json' and _json:
            state = _json.load(buffer)
        if isinstance(state, type(None)):
            raise AssertionError('state not deserialized') #nothing decoded
        try:
            module = __import__(state['__module__'], fromlist=[state['__class__']])
        except TypeError:
            #python2.4 __import__ implementation doesn't accept **kwargs
            module = __import__(state['__module__'], {}, {}, [state['__class__']])
        myClass = getattr(module, state['__class__'])
        return myClass.construct(state)

    def __getstate__(self):
        """Returns a dict containing the state of the object. The dict *must* 
           consist only of **native types**. This ensures journaled objects 
           will always be future compatible even as their class definitions 
           change. This method must be overriden by subclasses that have the 
           attribute ``serializable = True``.
        """
        raise NotImplemented()

    @staticmethod
    def construct(state):
        """Create or update an instance of this class using the *state* dict 
           that was created by a previous ``serialize`` call. This method must 
           be overriden by subclasses that have the attribute 
           ``serializable = True``.
        """
        raise NotImplemented()

    def __repr__(self):
        """Returns a string of the form ClassName(param, param, ...) to 
           represent the object.
        """
        if not self.COMPLEX_CONSTRUCTOR:
            args, kwargs = self._instanceID
            if kwargs:
                args += tuple(["%s=%s" % kwarg for kwarg in kwargs])
            paramString = ','.join( map(str,args) )
            return "%s(%s)" % (self.__class__.__name__, paramString)
        elif self.__class__.isValid(self):
            return "%s(%d)" % (self.__class__.__name__, self._instanceID)
        else:
            raise InValidEntity("InValid Instance of <%s>" % (self.__class__.__name__,))

    __str__ = __repr__


#we need a metaclass definition that works for python2 and python3
Entity = ParameterizedSingleton('Entity', (Entity,), {})

__all__ = ['Entity', 'InValidEntity']

#sanity test for __safe_itervalues__
if __name__ == '__main__':
    import sys
    def _print(obj):
        'b/c print is evil'
        sys.stdout.write(str(obj)+'\n')

    class Foo(Entity):
        """Test class to demonstrate functionality"""
        @classmethod
        def _weak_callback(classObj, instanceId, obj):
            if instanceId in classObj._instanceMap:
                del classObj._instanceMap[instanceId]
            _print("Reaping unbound object id: Foo%s" % str(instanceId))

        def __init__(self, value):
            self.reapable = bool(value % 2) #odds will automatically reap
            _print('Created Foo(%d)' % (value,))
            if self.reapable:
                _print("Foo(%d) will automatically gc when it leaves scope" % (value,))
            else:
                _print("Foo(%d) will not gc without an explicit delete" % (value,))
            _print("")

    #instantiate some Foo Entities
    a = list(map(Foo, range(10)))
    _print("\nCurrent map:\n%s\n" % str(len(Foo._instanceMap)))
    _print("\nCurrent namespace:\n%s\n" % str(len(namespace['entities']['Foo'])))
    _print("\nGo go gadget GC\n")
    del a #once unbound automatic GC should kick in

    _print("\n\nCurrent map:\n%s\n" % str(len(Foo._instanceMap)))
    _print("\nCurrent namespace:\n%s\n" % str(len(namespace['entities']['Foo'])))
    #make sure runtime errors aren't thrown when the undelying dict is modified
    for obj in Foo.objects: #this is a generator accessing the dict
        _print("Reference Count of %s is %d" % (obj,weakref.getweakrefcount(obj)))
        _print("Preparing to delete Entity %s during Iteration" % obj)
        Foo.delete(obj) #this modifies the dict
        try:
            _print(obj) #this should throw an invalid entity error
        except InValidEntity:
            _print('Foo Entity Successfully Invalidated during Iteration')
            _print("Reference Count is now %d" % (weakref.getweakrefcount(obj),))
        except:
            _print('Unexpected Exception, re-raising')
            raise
        _print("")
    _print("\nCurrent map:\n%s\n" % str(len(Foo._instanceMap)))
    _print("\nCurrent namespace:\n%s\n" % str(len(namespace['entities']['Foo'])))
