import context

__doc__ = """
This package makes it a little bit easier to write higher level objects.

Warning you will still need the lower lever API to figure out complex
relationships.  This package just makes simple things easier.
"""

class HOSTDBNode(context.EntityContext):
    """Special Class to encapsulate lower level ROMEO API"""
    entityAttr = None
    specialKeys = []
    entity = None

    def __init__(self, RomeoKeyValueInstance):
        """overrode the default constructor"""
        setattr(self, self.entityAttr, RomeoKeyValueInstance)
        self.data = {}

    def __getattribute__(self, name):
        if name.startswith('get_'):
            return lambda: _gettr_(self, name.replace('get_',''))
        try: return context.EntityContext.__getattribute__(self, name)
        except AttributeError:
             if name in self.specialKeys: return self.get(name)
             raise #re-raise original exception

    def __repr__(self):
        if self.__class__.__name__ == 'ENVIRONMENT':
            return self.entity.get('NAME').VALUE
        return "HOSTDBNODE(%s)" % (self.__class__.__name__,)


def _gettr_(obj, key_name):
    entity = getattr(obj, obj.entityAttr)
    x = entity.get(key_name)
    if hasattr(x, '__iter__'):
        return _iter_(entity, x)
    if isinstance(x, entity.__class__):
        if x.COMPLEX_CONSTRUCTOR:
            return node_constructor(x)
        return x.VALUE
    return x

def _iter_(entity, objects):
    for x in objects:
        if isinstance(x, entity.__class__):
            if x.COMPLEX_CONSTRUCTOR:
                yield node_constructor(x)
            else: yield x.VALUE
        else: yield x

def node_constructor(RomeoKeyValueInstance):
    from romeo.foundation import RomeoKeyValue
    if not isinstance(RomeoKeyValueInstance, RomeoKeyValue):
        raise TypeError('Cannot adapt <%s> to <HOSTDBNode>' % \
                str(RomeoKeyValueInstance))

    keys = [ i for i in RomeoKeyValueInstance.keys() if i != \
            RomeoKeyValueInstance.KEY ]
    members = {  
        'entityAttr': str(RomeoKeyValueInstance.KEY),
        'specialKeys': list(keys),
        'entity': RomeoKeyValueInstance,
    }

    #create a new class node
    instance = type(
        str(RomeoKeyValueInstance.KEY),
        (HOSTDBNode,),
        members
    )
    #initilialize the instance now
    return instance(RomeoKeyValueInstance)

def getEnvironment(name):
    import romeo
    return node_constructor(romeo.getEnvironment(name))

def listEnvironments():
    import romeo
    return [node_constructor(i) for i in romeo.listEnvironments()]

def whoami(hostname):
    import romeo
    return node_constructor(romeo.whoami(hostname))

def me():
    import romeo
    return node_constructor(romeo.whoami())

def safe_iter(obj):
    if hasattr(obj, '__iter__'):
        return obj
    return (i for i in [obj]) 
