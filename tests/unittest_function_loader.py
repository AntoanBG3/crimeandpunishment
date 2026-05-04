import inspect
import tempfile
import unittest
from pathlib import Path


def load_pytest_style_functions(module_globals):
    suite = unittest.TestSuite()
    for name, test_function in sorted(module_globals.items()):
        if name.startswith("test_") and callable(test_function):
            suite.addTest(unittest.FunctionTestCase(_wrap_test_function(test_function)))
    return suite


def _wrap_test_function(test_function):
    def run_test():
        signature = inspect.signature(test_function)
        if "tmp_path" not in signature.parameters:
            test_function()
            return

        with tempfile.TemporaryDirectory() as temporary_directory:
            test_function(tmp_path=Path(temporary_directory))

    run_test.__name__ = test_function.__name__
    return run_test
