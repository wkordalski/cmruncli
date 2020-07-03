from tool.pipeline.dump import Dump
from hashlib import sha256
from uuid import uuid4

import os

class PipelineContext:
    def __init__(self, child_template_code, symbols, smake_path, asm_sha256,
                 env, env_index, base_dir, logs_path, results_path, bar,
                 input_pipe, device=None):


        self.bar = bar
        self.input_pipe = input_pipe
        self.benchmark_id = str(uuid4())

        self.smake_path = smake_path
        self.symbols = symbols
        self.child_template_code = child_template_code
        self.device = device
        self.env = env
        self.env_index = env_index
        self.logs_dir = os.path.realpath(logs_path)
        self.results_dir = os.path.realpath(results_path)

        self.base_dir = base_dir
        self.templates_dir = os.path.join(base_dir, 'templates')

        self.dump = Dump()
        self.dump.asm_sha256 = asm_sha256
        self.dump.configuration_name = str(env)

        self.symbol_sizes = None
