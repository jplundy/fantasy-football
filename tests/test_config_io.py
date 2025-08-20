from pathlib import Path
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utility.scoring import save_config, load_config, SCORING_CONFIG_DEFAULT


def test_save_load_round_trip(tmp_path):
    path = tmp_path / "config.json"
    config = {"QB": {"PassTD": {"points": 4}}}
    save_config(path, config)
    assert load_config(path) == config


def test_load_config_default(tmp_path):
    path = tmp_path / "missing.json"
    loaded = load_config(path)
    assert loaded == SCORING_CONFIG_DEFAULT
    assert loaded is not SCORING_CONFIG_DEFAULT
