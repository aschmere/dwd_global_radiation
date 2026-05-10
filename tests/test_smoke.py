"""Smoke tests against the live DWD OpenData API.

These tests require network access. If DWD's servers are
unreachable they will fail — that's expected behavior, not
a bug in the package.
"""
import dwd_global_radiation as dgr


def test_fetch_measurements_returns_data():
    obj = dgr.GlobalRadiation()
    obj.add_location(name="Berlin", latitude=52.52, longitude=13.405)
    obj.fetch_measurements()

    assert obj.measurement_health_state == "green"
    assert len(obj.locations) == 1
    assert len(obj.locations[0].measurements) == 1
    assert len(obj.locations[0].measurements[0].measurement_values) > 0


def test_fetch_forecasts_returns_data():
    obj = dgr.GlobalRadiation()
    obj.add_location(name="Berlin", latitude=52.52, longitude=13.405)
    obj.fetch_forecasts()

    assert obj.forecast_health_state == "green"
    assert len(obj.locations[0].forecasts) == 1
    assert len(obj.locations[0].forecasts[0].entries) >= 16


def test_print_data_runs_without_error():
    obj = dgr.GlobalRadiation()
    obj.add_location(name="Berlin", latitude=52.52, longitude=13.405)
    obj.fetch_measurements()
    obj.fetch_forecasts()
    obj.print_data()  # just verify it doesn't raiseuv pip install pytest pytest-cov ruff