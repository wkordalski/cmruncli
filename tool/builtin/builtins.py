import functools
from . import functions, utils

def get_builtins(context):
    res = dict()
    for fname, f in functions.builtin.all.items():
        res[fname] = functools.partial(f, context)

    for reg in utils.userRegs:
        res[reg] = reg

    for counter_type, offset in utils.dwtCntToOffset.items():
        res[counter_type] = '#' + str(offset)
    return res
