import os
import subprocess

from hashlib import sha256
from tool import config
from tool.pipeline.steps.step import pipeline_step


@pipeline_step(name='make')
class MakeStep:
    def step(self, context, log_file):
        with open(log_file, 'w') as logf:
            build_dir = os.path.join(context.base_dir, 'build/cherry')
            flash = os.path.join(build_dir, 'app.flash')
            elf = os.path.join(build_dir, 'app.nobl.elf')

            logf.write("Running make...\n")
            res = subprocess.run(["make", "-B", "-C", build_dir, "PLATFORM_CC26XX_BOOTLOADER_DIO=11"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logf.write(res.stdout.decode("utf-8"))
            if res.returncode != 0:
                return False

            logf.write("Make finished!\n")

            # calculate sha256 of flash
            with open(flash, 'rb') as f:
                flash_bytes = f.read()
            hasher = sha256()
            hasher.update(flash_bytes)
            logf.write("Flash sha256 is {}!\n".format(hasher.hexdigest()))
            context.dump.flash_sha256 = hasher.digest()

            logf.write("Getting emulator_main and emulator_exit addresses from elf...\n")
            res = subprocess.run([config.ARM_NM_EXEC, '--print-size', elf], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            res = res.stdout.decode('utf-8')
            res = [x.strip().split(' ') for x in res.split('\n')]
            for symbol_info in res:
                if symbol_info[-1] == 'emulator_main':
                    context.dump.emulator_main_addr = int(symbol_info[0], 16)
                elif symbol_info[-1] == 'emulator_cdl_start':
                    context.dump.emulator_cdl_start_addr = int(symbol_info[0], 16)
                elif symbol_info[-1] == 'emulator_exit':
                    context.dump.emulator_exit_addr = int(symbol_info[0], 16)

            return True
