from . import utils

def registerBuiltin():
    registry = {}
    def registrar(func):
        registry[func.__name__] = func
        return func

    registrar.all = registry
    return registrar


# Decorator for builtin function
builtin = registerBuiltin()

##
# Save time to times array
# @param reg1 Register holding time to be saved
# @param reg2 Register to store times array address
# @param reg3 Temporary register for operations

@builtin
def saveTime(context, reg1, reg2, reg3):
    utils.checkArgRegs([reg1, reg2])
    assert 'counter' in utils.rememberedRegs, "Counter not initialized - run {{initCounter(reg1)}} before saving any result"

    return '\n'.join([
        'ldr.w\t{}, =times'.format(reg2),
        'lsr.w\t{}, {}, #16'.format(reg3, utils.rememberedRegs['counter']),
        'str.w\t{}, [{}, {}, LSL #2]'.format(reg1, reg2, reg3),
        'mov.w\t{}, #1'.format(reg3),
        'add.w\t{}, {}, {}, LSL #16'.format(utils.rememberedRegs['counter'], utils.rememberedRegs['counter'], reg3),
    ])

##
# Save result to results array
# @param reg1 Register holding value to be saved
# @param reg2 Register to store results array address
# @param reg3 Temporary register for operations

@builtin
def saveResult(context, reg1, reg2, reg3):
    utils.checkArgRegs([reg1, reg2])
    assert 'counter' in utils.rememberedRegs, "Counter not initialized - run {{initCounter(reg1)}} before saving any result"

    return '\n'.join([
        'mov.w\t{}, #0'.format(reg2),
        'ldr.w\t{}, =results_mask'.format(reg3),
        'ldr.w\t{}, [{}, {}]'.format(reg3, reg3, reg2),
        'ldr.w\t{}, =results'.format(reg2),
        'and.w\t{}, {}, {}'.format(reg3, utils.rememberedRegs['counter'], reg3),
        'str.w\t{}, [{}, {}, LSL #2]'.format(reg1, reg2, reg3),
        'mov.w\t{}, #1'.format(reg3),
        'add.w\t{}, {}'.format(utils.rememberedRegs['counter'], reg3),
    ])

##
# Declares section of memory
# @param memory Type of memory to declare (one of 'flash', 'sram', 'gpram')

@builtin
def section(context, memory):
    assert memory in ['flash', 'sram', 'gpram'], "Memory type {} not recognized".format(memory)
    return {
        'flash': '.section .text.benchmark, "xa" @progbits',
        'sram': '.section .data.benchmark, "wxa" @progbits',
        'gpram': '.section .gpram.benchmark, "wxa" @progbits'
    }[memory]

##
# Initializes counter that keeps track of number of elements in results and times arrays
# @param reg1 Register for counter (high half - times element count, lower half - results element count)

@builtin
def initCounter(context, reg1):
    utils.checkArgRegs([reg1])

    utils.rememberedRegs['counter'] = reg1

    return '\n'.join([
        'mov.w\t{}, #0'.format(reg1),
    ])

##
# Saves counter value to r0 (return register)

@builtin
def saveCounterToResReg(context):
    if utils.rememberedRegs['counter'] == 'r0':
        return ''

    return '\n'.join([
        'mov.n\tr0, {}'.format(utils.rememberedRegs['counter']),
    ])
