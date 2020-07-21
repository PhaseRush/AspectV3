import sys
import time
from functools import wraps
from gc import get_referents
from types import ModuleType, FunctionType


# https://stackoverflow.com/a/30316760/10583298
def sizeof(obj):
    """sum size of object & members."""
    BLACKLIST = type, ModuleType, FunctionType
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: ' + str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size


def timeit(f):
    @wraps(f)
    async def timer(*args, **kwargs):
        start = time.time()
        result = await f(*args, **kwargs)
        print(f'Execution time for: {f.name}: {time.time() - start}s')
        return result

    return timer
