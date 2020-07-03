import os
import subprocess

from jinja2 import FileSystemLoader, Environment

from tool import config
from tool.pipeline.steps.step import pipeline_step

@pipeline_step('render_dumpmem')
class RenderDumpmemStep():
    def createJinja2Env(self, context):
        env = Environment(
            line_comment_prefix='@',
            loader=FileSystemLoader(context.templates_dir),
        )
        return env

    def step(self, context, log_file):
        with open(log_file, 'w') as logf:

            env = self.createJinja2Env(context)
            times_results_array_size = 100*4 # Size of array in bytes

            build_dir = os.path.join(context.base_dir, 'build', 'cherry')
            asm_obj = os.path.join(build_dir, 'benchmarkCode.o')
            dump_mem_c = os.path.join(build_dir, 'dump_mem.c')

            logf.write("Getting symbol sizes from benchmarkCode.o...\n")
            res = subprocess.run(['arm-none-eabi-nm', '--print-size', asm_obj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            res = res.stdout.decode('utf-8')
            res = [x.strip().split(' ') for x in res.split('\n')]
            res = list(filter(lambda x: len(x) == 4, res))
            symbols_dict = dict([(x[3], int(x[1], 16)) for x in res])

            # hardcode results and times arrays, we know their size
            symbols_dict['results'] = times_results_array_size
            symbols_dict['times'] = times_results_array_size
            symbols_with_sizes = []
            for symbol in context.symbols:
                if symbol in symbols_dict.keys():
                    symbols_with_sizes.append((symbol, symbols_dict[symbol]))
                else:
                    logf.write("Could not fetch size of symbol {}, skipping it...".format(symbol))

            context.symbol_sizes = dict(symbols_with_sizes)

            tpl = env.get_template('dump_mem.c.tpl')
            out = tpl.render({'dump_symbols': symbols_with_sizes})
            with open(dump_mem_c, 'w') as outf:
                outf.write(out)

            return True
