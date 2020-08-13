import os

from chr.core import chr_compile_module

chr_compile_module(os.path.dirname(__file__), verbose=False, overwrite=True)
