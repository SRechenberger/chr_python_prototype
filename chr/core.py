import os
from typing import Union

from chr.compiler import chr_compile_source

CHR_SUFFIX = ".chr"
PY_SUFFIX = ".py"


def chr_compile(
        input_file_path: str,
        output_file_path: str,
        overwrite: Union[bool, str] = False,
        verbose: bool = False
):
    """
    Reads and compiles a CHR source file, and writes the generated code it
    to a Python source file.

    :param input_file_path: File path of the input file
    :param output_file_path: File path of the output file
    :param overwrite: If set to True, an existing output file is overwritten;
        if set to "timestamp", an existing output file is overwritten,
        if it was last modified before the source file (i.e. if it is outdated)
    :param verbose: If set to True, some additional information is given
    :return: True, if output was written; False otherwise
    """

    if not input_file_path.endswith(CHR_SUFFIX):
        raise ValueError(f"File name {input_file_path} does not seem to be a CHR file.")

    if not os.path.isfile(input_file_path):
        raise FileNotFoundError(f"CHR source file {input_file_path} does not exist.")

    if not overwrite and os.path.isfile(output_file_path):
        return False

    if (
            overwrite == "timestamp" and
            os.path.isfile(output_file_path) and
            not (os.path.getmtime(input_file_path) > os.path.getmtime(output_file_path))
    ):
        return False

    with open(input_file_path, "r") as input_file:
        chr_source = input_file.read()
        python_source = chr_compile_source(chr_source, verbose=verbose)
        with open(output_file_path, "w") as output_file:
            output_file.write(python_source)

    return True


def chr_compile_module(
        module_path: str,
        overwrite: Union[bool, str] = "timestamp",
        verbose: bool = False
):
    """
    Compile all .chr files in a module.

    You may call this in a __init__.py file like this, to automatically compile the
    module on load:

        import os
        from chr.utils import chr_compile_module

        chr_compile_module(os.path.dirname(__file__))

    :param module_path: path of the module
    :param overwrite: If set to True, an existing Python file is overwritten in any case;
        if set to "timestamp", an existing Python file is overwritten, if it is older than
        the CHR source file; if set to False, an existing Python file will not be overwritten.
    :param verbose: set to True to get additional output
    :return: None
    """
    for file in os.listdir(module_path):
        if file.endswith(CHR_SUFFIX):
            python_file_path = os.path.join(module_path, file[:-len(CHR_SUFFIX)] + PY_SUFFIX)
            chr_file_path = os.path.join(module_path, file)

            if verbose:
                print(f"Compiling {chr_file_path} into {python_file_path}")

            result = chr_compile(
                chr_file_path,
                python_file_path,
                overwrite=overwrite,
                verbose=verbose
            )

            if verbose and not result:
                print(
                    f"No output for {chr_file_path}: " +
                    (
                        f"file {python_file_path} is up to date."
                        if overwrite == "timestamp"
                        else f"file {python_file_path} already exists."
                    )
                )