import os
import sys
import pytest


# Ensure 'src' is importable when running tests from the backend directory
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(os.path.dirname(BACKEND_ROOT), "src")
if SRC_PATH not in sys.path:
	sys.path.insert(0, SRC_PATH)


def pytest_collection_modifyitems(items):
	"""Automatically categorize tests by folder as markers for convenience."""
	for item in items:
		path = str(item.fspath)
		if os.sep + "unit" + os.sep in path:
			item.add_marker(pytest.mark.unit)
		elif os.sep + "integration" + os.sep in path:
			item.add_marker(pytest.mark.integration)
