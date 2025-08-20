import dash
from dash import html, dcc, Input, Output, callback
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from copy import deepcopy

from layout import create_scoring_controls
from utility.helpers import get_offense_data, clean_offense_data
from modeling.predict import predict_position
from utility.scoring import SCORING_CONFIG_DEFAULT, calculate_prop_points

# Register page

dash.register_page(__name__, path="/modeling")

# Load and clean offensive data
_base_df = get_offense_data()
_base_df = clean_offense_data(_base_df)
_positions = sorted(_base_df["Position"].dropna().unique())
_teams = sorted(_base_df["Team"].dropna().unique())


def _compute_projections(
    df,
    pass_yds_pt=25,
    pass_td_pts=6,
    int_pen=-3,
    rush_yds_pt=10,
    rush_td_pts=6,
    fum_pen=-3,
    rec_yds_pt=10,
    rec_per=5,
    rec_td_pts=6,
):
    df = df.copy()

    # Add model projections for each position
    for pos in df["Position"].unique():
        pos_df = df[df["Position"] == pos]
        try:
            proj = predict_position(pos_df, pos)
            df.loc[pos_df.index, "Projection"] = proj
        except Exception:
            df.loc[pos_df.index, "Projection"] = 0.0

    # Build scoring configuration
    config = deepcopy(SCORING_CONFIG_DEFAULT)
    if pass_yds_pt is not None:
        config["QB"]["PassYds"]["points_per"] = pass_yds_pt
    if pass_td_pts is not None:
        config["QB"]["PassTD"]["points"] = pass_td_pts
    if int_pen is not None:
        config["QB"]["Int"]["points"] = int_pen
    if rush_yds_pt is not None:
        for pos in ("QB", "RB", "WR"):
            if "RushYds" in config.get(pos, {}):
                config[pos]["RushYds"]["points_per"] = rush_yds_pt
    if rush_td_pts is not None:
        for pos in ("QB", "RB", "WR"):
            if "RushTD" in config.get(pos, {}):
                config[pos]["RushTD"]["points"] = rush_td_pts
    if fum_pen is not None:
        for pos in ("QB", "RB", "WR", "TE"):
            if "Fum" in config.get(pos, {}):
                config[pos]["Fum"]["points"] = fum_pen
    if rec_yds_pt is not None:
        for pos in ("RB", "WR", "TE"):
            if "RecYds" in config.get(pos, {}):
                config[pos]["RecYds"]["points_per"] = rec_yds_pt
    if rec_per is not None:
        for pos in ("RB", "WR", "TE"):
            if "Rec" in config.get(pos, {}):
                config[pos]["Rec"]["points_per"] = rec_per
    if rec_td_pts is not None:
        for pos in ("RB", "WR", "TE"):
            if "RecTD" in config.get(pos, {}):
                config[pos]["RecTD"]["points"] = rec_td_pts

    scoring_df = df.rename(columns={"Position": "Pos"})
    scoring_df = calculate_prop_points(scoring_df, config=config)
    df["FantasyPoints"] = scoring_df["ModelPoints"]

    return df


def layout():
    scoring_controls = create_scoring_controls()
    initial_df = _compute_projections(_base_df)

    return dbc.Container(
        [
            html.H1("Modeling Dashboard"),
            scoring_controls,
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
    [
        Input("model-pos-filter", "value"),
        Input("model-team-filter", "value"),
        Input("pass-yds-pt", "value"),
        Input("pass-td-pts", "value"),
        Input("int-pen", "value"),
        Input("rush-yds-pt", "value"),
        Input("rush-td-pts", "value"),
        Input("fum-pen", "value"),
        Input("rec-yds-pt", "value"),
        Input("rec-per", "value"),
        Input("rec-td-pts", "value"),
    ],
)
def update_grid(
    pos_filter,
    team_filter,
    pass_yds_pt,
    pass_td_pts,
    int_pen,
    rush_yds_pt,
    rush_td_pts,
    fum_pen,
    rec_yds_pt,
    rec_per,
    rec_td_pts,
):
    df = _compute_projections(
        _base_df,
        pass_yds_pt,
        pass_td_pts,
        int_pen,
        rush_yds_pt,
        rush_td_pts,
        fum_pen,
        rec_yds_pt,
        rec_per,
        rec_td_pts,
    )

    if pos_filter:
        df = df[df["Position"].isin(pos_filter)]
    if team_filter:
        df = df[df["Team"].isin(team_filter)]

    return df.to_dict("records")
