import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner


class TopLevelTestRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if test_labels:
            return super().build_suite(test_labels=test_labels, extra_tests=extra_tests, **kwargs)

        test_root = Path(settings.BASE_DIR) / 'test'
        suite = self.test_suite()

        package_name = 'student_tests'
        package_module = types.ModuleType(package_name)
        package_module.__path__ = [str(test_root)]
        sys.modules.setdefault(package_name, package_module)

        helper_path = test_root / 'helpers.py'
        if helper_path.exists():
            helper_spec = spec_from_file_location(f'{package_name}.helpers', helper_path)
            helper_module = module_from_spec(helper_spec)
            sys.modules[helper_spec.name] = helper_module
            helper_spec.loader.exec_module(helper_module)

        for test_path in sorted(test_root.glob('test_*.py')):
            module_name = f'{package_name}.{test_path.stem}'
            spec = spec_from_file_location(module_name, test_path)
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            suite.addTests(self.test_loader.loadTestsFromModule(module))

        if extra_tests:
            suite.addTests(extra_tests)

        return suite
