import os
import subprocess

from tool import config
from tool.pipeline.steps.step import pipeline_step

@pipeline_step(name='precompile')
class PrecompileStep:
    def step(self, context, log_file):
        with open(log_file, 'w') as logf:
            # normalize path - no slash at the end
            smake = os.path.join(context.smake_path, 'smake')
            if context.smake_path[-1] == '/':
                smake = os.path.join(context.smake_path[:-1], 'smake')

            build_dir = os.path.join(context.base_dir, 'build', 'cherry')
            src = os.path.join(context.base_dir, 'benchmarkCode.s')
            obj = os.path.join(build_dir, 'benchmarkCode.o')
            emulator_src = os.path.join(context.base_dir, 'emulator.s')
            emulator_obj = os.path.join(build_dir, 'emulator.o')
            makefile_path = os.path.join(build_dir, "Makefile")

            # run smake just to generate build/cherry with Makefile in it
            logf.write("Generating build/cherry with Makefile using smake\n")
            res = subprocess.run([config.SMAKE_PYTHON_EXEC, smake, "cherry"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=context.base_dir)

            # if compilation fails, it will fail here though and generated build/cherry will be empty,
            # therefore to recognize whether it's compilation fail or linking fail, we check if Makefile
            if not os.path.exists(makefile_path):
                logf.write(res.stdout.decode("utf-8"))
                return False

            logf.write("Compiling benchmarkCode.s with arm-none-eabi-as\n")
            res = subprocess.run([config.ARM_AS_EXEC, src, "-o", obj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logf.write(res.stdout.decode("utf-8"))
            if res.returncode != 0:
                return False

            logf.write("Compiling emulator.s with arm-none-eabi-as\n")
            res = subprocess.run([config.ARM_AS_EXEC, emulator_src, "-o", emulator_obj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logf.write(res.stdout.decode("utf-8"))
            if res.returncode != 0:
                return False

            logf.write("Moving ASM src files to build/cherry\n")
            res = subprocess.run(["mv", src, emulator_src, build_dir], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            logf.write(res.stdout.decode("utf-8"))
            if res.returncode != 0:
                return False

            with open(makefile_path, "r") as f:
                makefile_content = f.read()

            logf.write("Adding ASM object file to OBJS in Makefile\n")

            # add compiled ASM as a target to Makefile
            lines = makefile_content.split("\n")
            for i, l in enumerate(lines):
                if l.startswith("OBJS"):
                    lines[i] += " benchmarkCode.o dump_mem.o emulator.o"

            lines.append('')
            lines.append('dump_mem.o: dump_mem.c')
            lines.append('\t$(CC) $(CFLAGS) -c $< -o $@')

            with open(makefile_path, "w") as f:
                f.write('\n'.join(lines))

            return True
