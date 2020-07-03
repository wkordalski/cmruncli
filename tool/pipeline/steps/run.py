from tool.pipeline.steps.step import pipeline_step
from tool.pipeline.dump import Symbol
from tool.timeout import timeout
from tool import config
import os
import string
import subprocess

@pipeline_step(name='run')
class RunStep:
    @timeout(20, "readline timed out")
    def readline(self, bar, pipe):
        line = pipe.readline()
        if len(line) > 0:
            bar.write(line.rstrip())
        return line

    def step(self, context, logFile):
        with open(logFile, 'w') as logf:
            if not context.device:
                logf.write("No device passed, skipping running on mode...")
                return True

            hexFile = os.path.join(context.base_dir, 'build', 'cherry', 'app.hex')

            context.bar.write("Programming node...")
            logf.write("Programming node...\n")
            res = subprocess.run([config.HENI_EXEC, "node", "program", "cherry", "-d", "dev:{}".format(context.device), hexFile],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logf.write(res.stdout.decode("utf-8"))
            logf.write("Waiting for output...\n")
            output = ""

            context.bar.write("Writing UART output from device here\n")

            def strip_non_printable(s):
                return ''.join(filter(lambda x: x in string.printable, s))  # filter weird non-printable chars

            while True:
                line = self.readline(context.bar, context.input_pipe)
                line = strip_non_printable(line)
                if line.startswith("Benchmark ID: {}".format(context.benchmark_id)):
                    break

            for i in range(2):
                output += strip_non_printable(self.readline(context.bar, context.input_pipe))

            for i in range(len(context.symbols)):
                line = strip_non_printable(self.readline(context.bar, context.input_pipe).strip())
                expected_symbol = context.symbols[i]

                def fail_dump(msg):
                    logf.write("Dump of symbol {} is malformed - {}\nReturning step fail status...\n"
                               .format(expected_symbol, msg))

                if not (line.startswith(expected_symbol + ':')
                        and line.endswith("end")
                        and line.count(',') == 1):
                    fail_dump("bad guards on beginning or end or missing comma")
                    return False

                # get rid of symbol name at beginning and "end" guard at the end
                line = line[len(expected_symbol)+2:-4]
                addr, mem = line.split(',')
                addr = addr.strip()
                mem = mem.strip()

                if not addr.startswith("addr "):
                    fail_dump("no addr guard")
                    return False

                if not mem.startswith("mem "):
                    fail_dump("no mem guard")
                    return False

                addr = int(addr[5:])
                mem = [int(x, 16) for x in mem[4:].split(' ')]

                # check sizes
                if not addr < 2 ** 32:
                    fail_dump("bad addr size")
                    return False

                if not all([x < 2 ** 8 for x in mem]):
                    fail_dump("bad byte size in mem dump")
                    return False

                if len(mem) != context.symbol_sizes[expected_symbol]:
                    fail_dump("expected {} bytes, got {}".format(context.symbol_sizes[expected_symbol], len(mem)))
                    return False

                symbol = Symbol(expected_symbol, addr, mem)
                context.dump.mem_dump.append(symbol)

            logf.write("Output:\n\n{}\n".format(output))
            return True
