from tool.pipeline.steps.step import pipeline_step
import msgpack
import os
import shutil
import time

@pipeline_step(name='save_files')
class SaveFilesStep:
    def step(self, context, logFile):
        with open(logFile, 'w') as logf:
            if not os.path.exists(context.results_dir):
                os.mkdir(context.results_dir)

            new_flash = os.path.join(context.results_dir, '{}.flash'.format(context.env_index))
            dump = os.path.join(context.results_dir, '{}.dump'.format(context.env_index))
            flash = os.path.join(context.base_dir, 'build', 'cherry', 'app.flash')
            shutil.copy(flash, new_flash)
            context.dump.generation_time = int(time.time() * (10 ** 3))  # milliseconds

            with open(dump, 'wb') as f:
                msgpack.pack(context.dump.as_dict(), f)

            return True
