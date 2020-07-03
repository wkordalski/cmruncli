from .steps.step import pipeline_step

# import to register build steps
from .steps.make import *
from .steps.precompile import *
from .steps.render_asm import *
from .steps.render_dumpmem import *
from .steps.run import *
from .steps.save_files import *

import time


class PipelineException(Exception):
    pass

class Pipeline:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.last_successful_step = None

    def get_steps(self):
        return [
            'render_asm',
            'precompile',
            'render_dumpmem',
            'make',
            'run',
            'save_files',
        ]

    def run(self, context):
        retries = 0

        def run_failed(e=None):
            context.bar.write("Run failed with exception: {}".format(e))

            if not hasattr(run_failed, 'retries'):
                run_failed.retries = 0

            if run_failed.retries == self.max_retries:
                raise PipelineException("Retries limit reached, last exception: {}".format(e))

            run_failed.retries += 1
            context.bar.write("Retrying...")

        while (retries < self.max_retries):
            run_success_status = True

            steps = self.get_steps()
            if self.last_successful_step:
                steps = steps[steps.index(self.last_successful_step)+1:]  # start from step that failed

            for step_name in steps:
                step = pipeline_step.all[step_name]()
                log_file = os.path.join(context.logs_dir, '{}.log'.format(step_name))
                try:
                    context.bar.set_description(step_name)
                    res = step.step(context, log_file)
                    if not res:
                        raise PipelineException("Failed on {} step, check {} file".format(step_name, log_file))
                    self.last_successful_step = step_name
                except Exception as e:
                    run_failed(e)
                    run_success_status = False
                    break

            if run_success_status:
                dump = context.dump
                context.bar.update(1)
                return dump
