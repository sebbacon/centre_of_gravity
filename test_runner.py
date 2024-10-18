import pytest
from unittest.mock import patch, mock_open
import json
from runner import BestDestinationFinder


@pytest.fixture
def mock_config():
    return {
        "origins": [
            {"name": "New York City", "lat": 40.7128, "lon": -74.0060},
            {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
        ],
        "destinations": [
            {"name": "Philadelphia", "lat": 39.9526, "lon": -75.1652},
            {"name": "Boston", "lat": 42.3601, "lon": -71.0589},
        ],
    }


def test_load_config(mock_config):
    with patch.object(BestDestinationFinder, "load_config", return_value=mock_config):
        finder = BestDestinationFinder("AIzaDummyKeyForTesting", "mock_config.json")
        assert finder.config == mock_config


def test_get_coordinates(mock_config):
    with patch.object(BestDestinationFinder, "load_config", return_value=mock_config):
        finder = BestDestinationFinder("AIzaDummyKeyForTesting", "mock_config.json")
        coordinates = finder.get_coordinates(finder.config["origins"])
        assert coordinates == [(40.7128, -74.0060), (34.0522, -118.2437)]


def test_calculate_convenience_score(mock_config):
    with patch.object(BestDestinationFinder, "load_config", return_value=mock_config):
        finder = BestDestinationFinder("AIzaDummyKeyForTesting", "mock_config.json")
    travel_times = [1800, 2400, 3000]  # 30 min, 40 min, 50 min
    expected_score = 2400 * 0.7 + 3000 * 0.3  # avg * 0.7 + max * 0.3
    assert (
        pytest.approx(finder.calculate_convenience_score(travel_times))
        == expected_score
    )


@pytest.mark.integration
def test_find_best_destination(mock_config):
    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_MAPS_API_KEY not found in environment variables")

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
        finder = BestDestinationFinder(api_key, "mock_config.json")

    best_destination, best_score = finder.find_best_destination()
    assert best_destination is not None
    assert isinstance(best_score, float)
    assert best_score > 0


@pytest.mark.integration
def test_real_api_call(mock_config):
    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_MAPS_API_KEY not found in environment variables")

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
        finder = BestDestinationFinder(api_key, "mock_config.json")

    best_destination, best_score = finder.find_best_destination()
    assert best_destination is not None
    assert isinstance(best_score, float)
    assert best_score > 0


@pytest.mark.integration
def test_get_address(mock_config):
    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_MAPS_API_KEY not found in environment variables")

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
        finder = BestDestinationFinder(api_key, "mock_config.json")

    address = finder.get_address((39.9526, -75.1652))  # Philadelphia
    assert isinstance(address, str)
    assert address != "Address not found"
