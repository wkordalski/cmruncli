from jinja2 import nodes, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError
from jinja2.environment import Environment
from jinja2.ext import Extension

from tool.builtin.builtins import get_builtins
from tool.builtin.context import BuiltinContext
from tool.pipeline.steps.step import pipeline_step

import os



@pipeline_step(name='render_asm')
class RenderAsmStep:
    def _create_jinja2_env(self, context):
        env = Environment(
            line_comment_prefix='@',
            loader=FileSystemLoader(context.templates_dir),
            extensions=[DeviceConfigurationExtension]
        )
        builtin_context = BuiltinContext()
        env.globals.update(get_builtins(builtin_context))
        env.globals.update(context.env)
        return env

    def _render(self, tpl, outfile, logf):
        with open(outfile, 'w') as outf:
            logf.write("Rendering {} file\n".format(outfile))
            out = tpl.render()
            logf.write("File {} rendered. Contents:\n\n".format(outfile))

            logf.write(out + '\n')
            outf.write(out)

    def _render_benchmark_code_asm(self, context, tpl, logf):
        outfile = os.path.join(context.base_dir, 'benchmarkCode.s')
        self._render(tpl, outfile, logf)

    def _render_emulator_asm(self, context, env, logf):
        tpl = env.get_template('emulator.s.tpl')
        outfile = os.path.join(context.base_dir, 'emulator.s')
        self._render(tpl, outfile, logf)

    def step(self, context, log_file):
        with open(log_file, 'w') as logf:
            env = self._create_jinja2_env(context)
            tpl = env.from_string(context.child_template_code)

            # here env.device_configuration is parsed
            self._render_benchmark_code_asm(context, tpl, logf)
            env.globals.update({
                'line_buffer_enabled': env.device_configuration.line_buffer_enabled,
                'write_buffer_enabled': env.device_configuration.write_buffer_enabled,
            })

            self._render_emulator_asm(context, env, logf)

            logf.write("\nDevice configuration:\n")
            logf.write("-----------------------------\n")
            for key, val in env.device_configuration.get_defines().items():
                logf.write("{}: {}\n".format(key, val))

            build_spec_template = '''
app name: BenchmarkApp
boards:
 - cherry-v5
 - cherry
build dir: $(SPEC_DIR)/build/$(BOARD)
define:
 - CC26XX_VIMS_GPRAM_MODE=1
{}
'''

            logf.write("Writing build.spec\n")
            defines = env.device_configuration.get_defines()
            defines["BENCHMARK_ID"] = '"' + context.benchmark_id + '"'
            with open(os.path.join(context.base_dir, "build.spec"), 'w') as f:
                f.write(build_spec_template.format(
                    '\n'.join(' - ' + k + '=' + str(v) for k, v in defines.items())
                ))

            return True
