import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from copy import deepcopy
from pathlib import Path

from layout import create_scoring_controls
from utility.scoring import (
    SCORING_CONFIG_DEFAULT,
    save_config,
    load_config,
)

# Register page

dash.register_page(__name__, path="/settings")

SETTINGS_PATH = Path("assets/settings.json")


def layout():
    return dbc.Container(
        [
            html.H1("League Settings"),
            create_scoring_controls(),
            dbc.Button("Save", id="save-config", color="primary", className="me-2"),
            dbc.Button("Load", id="load-config", color="secondary"),
        ],
        fluid=True,
    )


@callback(
    Output("scoring-config", "data"),
    Input("save-config", "n_clicks"),
    State("pass-yds-pt", "value"),
    State("pass-td-pts", "value"),
    State("int-pen", "value"),
    State("rush-yds-pt", "value"),
    State("rush-td-pts", "value"),
    State("fum-pen", "value"),
    State("rec-yds-pt", "value"),
    State("rec-per", "value"),
    State("rec-td-pts", "value"),
    prevent_initial_call=True,
)
def save_settings(n_clicks, pass_yds_pt, pass_td_pts, int_pen, rush_yds_pt, rush_td_pts,
                  fum_pen, rec_yds_pt, rec_per, rec_td_pts):
    """Persist scoring settings and update the store."""

    config = deepcopy(SCORING_CONFIG_DEFAULT)
    config["QB"]["PassYds"]["points_per"] = pass_yds_pt
    config["QB"]["PassTD"]["points"] = pass_td_pts
    config["QB"]["Int"]["points"] = int_pen
    for pos in ("QB", "RB", "WR"):
        if "RushYds" in config.get(pos, {}):
            config[pos]["RushYds"]["points_per"] = rush_yds_pt
        if "RushTD" in config.get(pos, {}):
            config[pos]["RushTD"]["points"] = rush_td_pts
    for pos in ("QB", "RB", "WR", "TE"):
        if "Fum" in config.get(pos, {}):
            config[pos]["Fum"]["points"] = fum_pen
    for pos in ("RB", "WR", "TE"):
        if "RecYds" in config.get(pos, {}):
            config[pos]["RecYds"]["points_per"] = rec_yds_pt
        if "Rec" in config.get(pos, {}):
            config[pos]["Rec"]["points_per"] = rec_per
        if "RecTD" in config.get(pos, {}):
            config[pos]["RecTD"]["points"] = rec_td_pts

    save_config(SETTINGS_PATH, config)
    return config


@callback(
    Output("scoring-config", "data"),
    Input("load-config", "n_clicks"),
    prevent_initial_call=True,
)
def load_settings(n_clicks):
    """Load scoring settings from disk into the store."""

    return load_config(SETTINGS_PATH)


@callback(
    Output("pass-yds-pt", "value"),
    Output("pass-td-pts", "value"),
    Output("int-pen", "value"),
    Output("rush-yds-pt", "value"),
    Output("rush-td-pts", "value"),
    Output("fum-pen", "value"),
    Output("rec-yds-pt", "value"),
    Output("rec-per", "value"),
    Output("rec-td-pts", "value"),
    Input("scoring-config", "data"),
)
def display_settings(config):
    """Reflect current config values in the UI controls."""

    cfg = config or SCORING_CONFIG_DEFAULT
    return (
        cfg["QB"]["PassYds"]["points_per"],
        cfg["QB"]["PassTD"]["points"],
        cfg["QB"]["Int"]["points"],
        cfg["RB"]["RushYds"]["points_per"],
        cfg["RB"]["RushTD"]["points"],
        cfg["RB"]["Fum"]["points"],
        cfg["RB"]["RecYds"]["points_per"],
        cfg["RB"]["Rec"]["points_per"],
        cfg["RB"]["RecTD"]["points"],
    )
