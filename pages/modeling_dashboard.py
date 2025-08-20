import dash
from dash import html, dcc, Input, Output, callback, State
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from copy import deepcopy

from utility.helpers import get_offense_data, clean_offense_data
from modeling.predict import predict_position
from utility.scoring import SCORING_CONFIG_DEFAULT, calculate_prop_points, load_config
from pathlib import Path

# Register page

dash.register_page(__name__, path="/modeling")

# Load and clean offensive data
_base_df = get_offense_data()
_base_df = clean_offense_data(_base_df)
_positions = sorted(_base_df["Position"].dropna().unique())
_teams = sorted(_base_df["Team"].dropna().unique())


def _compute_projections(df, config=None):
    df = df.copy()

    # Add model projections for each position
    for pos in df["Position"].unique():
        pos_df = df[df["Position"] == pos]
        try:
            proj = predict_position(pos_df, pos)
            df.loc[pos_df.index, "Projection"] = proj
        except Exception:
            df.loc[pos_df.index, "Projection"] = 0.0

    cfg = config or deepcopy(SCORING_CONFIG_DEFAULT)
    scoring_df = df.rename(columns={"Position": "Pos"})
    scoring_df = calculate_prop_points(scoring_df, config=cfg)
    df["FantasyPoints"] = scoring_df["ModelPoints"]

    return df


def layout():
    initial_cfg = load_config(Path("assets/settings.json"))
    initial_df = _compute_projections(_base_df, config=initial_cfg)

    return dbc.Container(
        [
            html.H1("Modeling Dashboard"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="model-pos-filter",
                            options=[{"label": p, "value": p} for p in _positions],
                            multi=True,
                            placeholder="Filter by position",
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="model-team-filter",
                            options=[{"label": t, "value": t} for t in _teams],
                            multi=True,
                            placeholder="Filter by team",
                        ),
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            AgGrid(
                id="model-grid",
                columnDefs=[
                    {"headerName": "Name", "field": "Name", "sortable": True, "filter": True},
                    {"headerName": "Position", "field": "Position", "sortable": True, "filter": True},
                    {"headerName": "Team", "field": "Team", "sortable": True, "filter": True},
                    {
                        "headerName": "Model Projection",
                        "field": "Projection",
                        "sortable": True,
                        "filter": True,
                        "sort": "desc",
                    },
                    {
                        "headerName": "Fantasy Points",
                        "field": "FantasyPoints",
                        "sortable": True,
                        "filter": True,
                    },
                ],
                rowData=initial_df.to_dict("records"),
                defaultColDef={"resizable": True, "filter": True, "sortable": True},
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True, "rowBuffer": 0},
                className="ag-theme-alpine",
                style={"height": "70vh"},
            ),
        ],
        fluid=True,
    )


@callback(
    Output("model-grid", "rowData"),
    [Input("model-pos-filter", "value"), Input("model-team-filter", "value")],
    State("scoring-config", "data"),
)
def update_grid(pos_filter, team_filter, config):
    df = _compute_projections(_base_df, config=config)

    if pos_filter:
        df = df[df["Position"].isin(pos_filter)]
    if team_filter:
        df = df[df["Team"].isin(team_filter)]

    return df.to_dict("records")
