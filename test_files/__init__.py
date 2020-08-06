import os
from chr.compiler import chr_compile

module_path = os.path.dirname(__file__)

CHR_SUFFIX = ".chr"
PY_SUFFIX = ".py"


for file in os.listdir(module_path):
    if file.endswith(CHR_SUFFIX):
        python_file_path = os.path.join(module_path, file[:-len(CHR_SUFFIX)] + PY_SUFFIX)
        chr_file_path = os.path.join(module_path, file)
        if not os.path.isfile(python_file_path) or os.path.getmtime(python_file_path) < os.path.getmtime(chr_file_path):
            print("compiling", chr_file_path, "into", python_file_path)
            with open(chr_file_path, "r") as chr_file:
                chr_compile(chr_file.read(), python_file_path)


