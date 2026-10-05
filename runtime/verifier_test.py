import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path.cwd() / "src" / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

def test_average_multiple_values():
    assert app.average([2, 4, 6]) == 4

def test_average_single_value():
    assert app.average([7]) == 7

def test_average_negative_and_fractional():
    assert app.average([-3, 2]) == -0.5
