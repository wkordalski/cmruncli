# usable registers
userRegs = ["r" + str(i) for i in range(16)] + ["sl", "fp", "ip", "lr"]

# remembered registers
rememberedRegs = dict()

dwtCntToOffset = {
    'CYCCNT': 4,
    'CPICNT': 8,
    'EXCCNT': 12,
    'SLEEPCNT': 16,
    'LSUCNT': 20,
    'FOLDCNT': 24,
}
dwtCntNames = list(dwtCntToOffset.keys())

def checkArgRegs(regs):
    # checking if registers are valid
    for reg in regs:
        assert reg in userRegs, reg + " is not a valid register"

    # checking if any two registers from args are the same
    regs = sorted([(reg, i + 1) for (i, reg) in enumerate(regs)])
    for i in range(len(regs) - 1):
        assert regs[i][0] != regs[i + 1][0], "Cannot pass same registers as args (arg {} and {})".format(regs[i][1], regs[i + 1][1])

    # checking if any reg collides with remembered registers
    rememberedRegsVals = list(rememberedRegs.values())
    for reg in regs:
        assert reg not in rememberedRegsVals, "Cannot pass {} - it's already in use".format(reg)
