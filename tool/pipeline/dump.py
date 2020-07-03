class Symbol:
    def __init__(self, name, addr, mem):
        self.symbol_name = name
        self.addr = addr
        self.mem = mem

    def as_dict(self):
        res = dict()
        res['symbol_name'] = self.symbol_name
        res['addr'] = self.addr
        res['content'] = self.mem
        return res

class Dump:
    props = [
        "emulator_main_addr",
        "emulator_cdl_start_addr",
        "emulator_exit_addr",
        "flash_sha256",
        "asm_sha256",
        "configuration_name",
        "generation_time",
        "mem_dump",
    ]

    def __init__(self):
        for prop in self.props:
            self.__setattr__(prop, None)

        self.mem_dump = []

    def as_dict(self):
        res = dict()
        for prop in self.props:
            res[prop] = self.__getattribute__(prop)

        res['mem_dump'] = [x.as_dict() for x in res['mem_dump']]
        return res
