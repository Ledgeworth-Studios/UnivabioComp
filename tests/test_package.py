"""The one test that exists before there is anything to test.

It keeps `just check` honest: an empty test suite passes for the wrong reason,
because pytest exits non-zero when it collects nothing.
"""

import whynot


def test_package_imports_and_has_a_version():
    assert whynot.__version__
