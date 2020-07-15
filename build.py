#!/usr/bin/env python3

import itertools
import subprocess

import socket
import msgpack
import json
from tqdm import tqdm

from tool.pipeline.context import PipelineContext
from tool.pipeline.pipeline import Pipeline
from tool import config

import time

import argparse
from hashlib import sha256
import io
import os
import pty
import tarfile
import yaml
import zstandard as zstd
from uuid import uuid4

from jinja2 import nodes, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError
from jinja2.environment import Environment
from jinja2.ext import Extension

from tool.builtin.builtins import get_builtins
from tool.builtin.context import BuiltinContext

HOST_ADDRESS = '127.0.0.1'

base_dir = os.path.dirname(__file__) or '.'  # in case of no dirname, i.e. "python3 main.py"

class Args:
    _fields = [
        "name",
        "description",
        "dumped_symbols",
        "configurations",
        "template",
    ]

    def __init__(self, d):
        for field in self._fields:
            assert field in d.keys()
            self.__setattr__(field, d[field])


def printBanner(header, bar, msg):
    bar.write("")
    bar.write("{}:".format(header))
    bar.write("-----------------------------")
    bar.write(msg)
    bar.write("")


def dict_product(dicts):
    """
    >>> dict_product(dict(number=[1,2], character='ab'))
    [{'character': 'a', 'number': 1},
     {'character': 'a', 'number': 2},
     {'character': 'b', 'number': 1},
     {'character': 'b', 'number': 2}]
    """
    return [dict(zip(dicts, x)) for x in itertools.product(*dicts.values())]


def product_configurations(product):
    product_configurations = []
    for product_dict in product:
        product_configurations.extend(dict_product(product_dict))
    return product_configurations


def parseArgs():
    # define command line arguments
    argparser = argparse.ArgumentParser(description="Assembler snippets build tool for benchmarking purposes")
    argparser.add_argument(
        "input", metavar="input", type=str,
        help="ASM file"
    )
    args = argparser.parse_args()

    # handle input file
    args.results_path, extension = os.path.splitext(args.input)
    assert extension == '.asm', "bad extension for asm file"
    with open(args.input, 'r') as f:
        input_content = f.read().replace('\r\n', '\n').replace('\r', '\n')

    # calculate sha256 of input file contents
    hasher = sha256()
    hasher.update(bytes(input_content, 'utf-8'))
    args.asm_sha256 = hasher.digest()

    # split contents into YAML configuration and ASM code
    input_content = input_content.split('...')
    assert len(input_content) == 2
    metadata, asm_template = input_content
    asm_template = asm_template.strip()

    # load metadata
    data = dict(yaml.safe_load(metadata))

    # handle product extension
    if "product" in data:
        product = data["product"]
        data.pop("product")

        if "configurations" not in data:
            data["configurations"] = []
        data["configurations"].extend(product_configurations(product))

    # export parsed file contents
    data["template"] = asm_template
    args.input_content = Args(data)
    return args

def connectToBuildServer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST_ADDRESS, 4242))
    return s

def send(s, o):
    data = msgpack.packb(o)
    ol = len(data)
    data = zstd.ZstdCompressor().compress(data)
    cl = len(data)
    len_bytes = bytes([len(data) & 0xFF, (len(data) & 0xFF00) >> 8, (len(data)& 0xFF0000) >> 16, (len(data)& 0xFF000000) >> 24])
    s.send(len_bytes + data)
    

def recv(s):
    len_bytes = b''
    while len(len_bytes) < 4:
        b = s.recv(4 - len(len_bytes))
        if len(b) == 0:
            return None
        len_bytes += b
    len_val = len_bytes[0] | len_bytes[1] << 8 | len_bytes[2] << 16 | len_bytes[3] << 24
    data = b''
    while len(data) < len_val:
        b = s.recv(len_val - len(data))
        if len(b) == 0:
            return None
        data += b
    return msgpack.unpackb(zstd.ZstdDecompressor().decompress(data))
    #return msgpack.unpackb(data)

class DeviceConfiguration:
    def __init__(self):
        self.line_buffer_enabled = False
        self.write_buffer_enabled = False

    def __str__(self):
        def onoff(b):
            return "on" if b else "off"

        return '\n'.join([
            'VIMS :: Line Buffer Enabled\t{}'.format(onoff(self.line_buffer_enabled)),
            'Write Buffer Enabled\t{}'.format(onoff(self.write_buffer_enabled)),
        ])

    def get_defines(self):
        return {
            'BENCHMARK_VIMS_LB_DIS': int(not self.line_buffer_enabled),
            'BENCHMARK_WRITE_BUFFER_DIS': int(not self.write_buffer_enabled),
        }


class DeviceConfigurationExtension(Extension):
    tags = {'device'}

    def __init__(self, environment):
        super(DeviceConfigurationExtension, self).__init__(environment)

        environment.extend(device_configuration=DeviceConfiguration())

    def parse(self, parser):
        tag = next(parser.stream)
        parser.stream.expect("colon")
        field = next(parser.stream)

        if field.value == 'line_buffer_enabled':
            parser.stream.expect("assign")
            value = parser.parse_expression()
            return nodes.CallBlock(
                self.call_method("_set_line_buffer_enabled", [value]), [], [], []
            ).set_lineno(tag.lineno)
        elif field.value == 'write_buffer_enabled':
            parser.stream.expect("assign")
            value = parser.parse_expression()
            return nodes.CallBlock(
                self.call_method("_set_write_buffer_enabled", [value]), [], [], []
            ).set_lineno(tag.lineno)
        else:
            raise TemplateSyntaxError(
                "Unknown device configuration parameter: {}".format(field.value),
                field.lineno, parser.stream.name, parser.stream.filename
            )

    def _set_line_buffer_enabled(self, value, caller):
        self.environment.device_configuration.line_buffer_enabled = bool(value)
        return ''

    def _set_write_buffer_enabled(self, value, caller):
        self.environment.device_configuration.write_buffer_enabled = bool(value)
        return ''

def create_jinja2_env(configuration):
    env = Environment(
        line_comment_prefix='@',
        loader=FileSystemLoader(os.path.join(base_dir, 'templates')),
        extensions=[DeviceConfigurationExtension]
    )
    builtin_context = BuiltinContext()
    env.globals.update(get_builtins(builtin_context))
    env.globals.update(configuration)
    return env

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

def main():
    args = parseArgs()

    results_path = args.results_path

    sock = connectToBuildServer()
    bid2config = {}
    
    for i, configuration in tqdm(enumerate(args.input_content.configurations)):
        env = create_jinja2_env(configuration)
        benchmark_id = str(uuid4())
        bid2config[benchmark_id] = i

        benchmarkCode_s = env.from_string(args.input_content.template).render()
        env.globals.update({
            'line_buffer_enabled': env.device_configuration.line_buffer_enabled,
            'write_buffer_enabled': env.device_configuration.write_buffer_enabled,
        })
        emulator_s = env.get_template('emulator.s.tpl').render()

        defines = env.device_configuration.get_defines()
        defines["BENCHMARK_ID"] = '"' + benchmark_id + '"'
        build_spec = build_spec_template.format('\n'.join(' - ' + k + '=' + str(v) for k, v in defines.items()))

        subprocess.run(['arm-none-eabi-as', '-o', 'tmp.o'], input=benchmarkCode_s, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        res = subprocess.run(['arm-none-eabi-nm', '--print-size', 'tmp.o'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
        res = [x.strip().split(' ') for x in res.split('\n')]
        res = list(filter(lambda x: len(x) == 4, res))
        symbols_dict = dict([(x[3], int(x[1], 16)) for x in res])

        # hardcode results and times arrays, we know their size
        symbols_dict['results'] = 400
        symbols_dict['times'] = 400
        symbols_with_sizes = []
        for symbol in args.input_content.dumped_symbols:
            if symbol in symbols_dict.keys():
                symbols_with_sizes.append((symbol, symbols_dict[symbol]))
            else:
                print("Could not fetch size of symbol {}, skipping it...".format(symbol))

        dump_mem_c = env.get_template('dump_mem.c.tpl').render({'dump_symbols': symbols_with_sizes})

        send(sock, {
            'ident': benchmark_id,
            'build_spec': build_spec.encode('utf-8'),
            'sources': [
                ('emulator.s', emulator_s.encode('utf-8')),
                ('benchmarkCode.s', benchmarkCode_s.encode('utf-8')),
                ('dump_mem.c', dump_mem_c.encode('utf-8'))
            ],
            'symbols': symbols_with_sizes
        })

    if not os.path.exists(results_path):
        os.mkdir(results_path)

    # wait for results
    for i in tqdm(range(len(args.input_content.configurations))):
        o = recv(sock)
        ident = o['ident']
        idx = bid2config[ident]
        flash_path = os.path.join(args.results_path, f'{idx}.flash')
        dump_path = os.path.join(args.results_path, f'{idx}.dump')
        with open(flash_path, 'wb') as f:
            f.write(o['flash'])
        hasher = sha256()
        hasher.update(o['flash']) 
        with open(dump_path, 'wb') as f:
            msgpack.pack({
                'generation_time': round(time.time() * 10**3),
                'emulator_main_addr': o['emulator_main_addr'],
                'emulator_cdl_start_addr': o['emulator_cdl_start_addr'],
                'emulator_exit_addr': o['emulator_exit_addr'],
                'flash_sha256': hasher.digest(),
                'asm_sha256': args.asm_sha256,
                'configuration_name': json.dumps(args.input_content.configurations[idx]),
                'mem_dump': o['mem_dump']
            }, f)
    sock.close()

    result_file = results_path + '.tzst'

    # compress to tar with zstd compression
    # little shenaningans, so we won't have temporary .tar file
    with open(result_file, 'wb') as tzst:
        b = io.BytesIO()
        t = tarfile.open(mode='w', fileobj=b)
        t.add(results_path, arcname=os.path.basename(results_path))
        t.close()
        tar = b.getvalue()
        params = zstd.ZstdCompressionParameters.from_level(config.zstd_compression_level)
        cctx = zstd.ZstdCompressor(compression_params=params)
        compressed = cctx.compress(tar)
        tzst.write(compressed)

    return
    

if __name__ == "__main__":
    main()
