import sys
import time
from functools import wraps
from gc import get_referents
from threading import Lock, Timer
from types import ModuleType, FunctionType
from collections import defaultdict
import re

# https://stackoverflow.com/a/30316760/10583298
from typing import List

markdown_pattern = re.compile(r"([*_`~\\])")
triple_backtick_pattern = re.compile(r"(``)`")  # Discord does not support sending triple backticks in a code block.


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
        print(f'Execution time for command {f.__name__}: {"{:10.4f}".format((time.time() - start) * 1000)}ms')
        return result

    return timer


def escape_md(s: str) -> str:
    group1: str = r"\1"
    group2: str = r"\1 `"
    escaped = re.sub(markdown_pattern, group1, s)
    if triple_backtick_pattern.search(escaped):
        escaped = re.sub(triple_backtick_pattern, group2, escaped)
        escaped += "\n\t#Note: a triple backtick was found in the source code. Please refer to the github link for the most accurate source."
    return escaped

def merge_dicts(d1, d2):
    dd = defaultdict(list)
    for d in (d1, d2):
        for k, v in d.items():
            if type(v) is tuple:
                dd[k].append(v[0])
                dd[k].append(float(v[1]))
            else:
                dd[k].append(v)

    return dd


# https://stackoverflow.com/a/18906292/10583298
class Scheduler(object):
    """
    A periodic task running in threading.Timers
    """

    def __init__(self, interval, function, *args, **kwargs):
        self._lock = Lock()
        self._timer = None
        self.function = function
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._stopped = True
        if kwargs.pop('autostart', True):
            self.start()

    def start(self, from_run=False):
        self._lock.acquire()
        if from_run or self._stopped:
            self._stopped = False
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self._lock.release()

    def _run(self):
        # print(f"run called, function = {self.function}")
        self.start(from_run=True)
        self.function(*self.args, **self.kwargs)

    def stop(self):
        self._lock.acquire()
        self._stopped = True
        self._timer.cancel()
        self._lock.release()
