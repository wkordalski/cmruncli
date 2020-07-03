import os

def get_from_shell_env(env_var, default):
    if env_var in os.environ:
        return os.environ.get(env_var)
    return default



ARM_AS_EXEC = get_from_shell_env("ARM_AS_EXEC", "arm-none-eabi-as")
ARM_GCC_EXEC = get_from_shell_env("ARM_GCC_EXEC", "arm-none-eabi-gcc")
ARM_NM_EXEC = get_from_shell_env("ARM_NM_EXEC", "arm-none-eabi-nm")

HENI_EXEC = get_from_shell_env("HENI_EXEC", "heni")
SMAKE_PYTHON_EXEC = get_from_shell_env("SMAKE_PYTHON_EXEC", "python2.7")

logs_path = 'logs'
zstd_compression_level = 7
