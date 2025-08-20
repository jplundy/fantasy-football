"""Interactive sportsbook projection page.

This page loads prop projections from the local assets directory and lets
users tweak high level scoring settings.  The projections are recalculated on
each change and the grid below updates with the recomputed ``ModelPoints``.

Missing statistical categories in the underlying data are treated as zeros so
players without, for example, receiving stats will still appear with a score.
"""

import dash
from dash import html, dcc, Input, Output, callback
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc

from layout import create_scoring_controls
from utility.helpers import get_sportsbook_props
from utility.scoring import calculate_prop_points, SCORING_CONFIG_DEFAULT
from copy import deepcopy

# Register the projections page

dash.register_page(__name__, path='/projections')

# Load prop projection data
proj_df = get_sportsbook_props()
proj_df = calculate_prop_points(proj_df)


def layout():
    """Layout for the prop based projections page.

    The default scoring mirrors a common fantasy format (25 pass yards per
    point, six points per touchdown, etc.).  Any categories missing from the
    prop data are scored as zero.
    """

    positions = sorted(proj_df['Pos'].dropna().unique())
    scoring_controls = create_scoring_controls()

    info = dbc.Alert(
        [
            html.P(
                "Adjust the scoring settings below to see how prop-based "
                "projections change."
            ),
            html.P(
                "Defaults follow standard fantasy scoring. Players missing a "
                "stat category (e.g., no rushing data) are treated as having "
                "zero for that stat."
            ),
        ],
        color="info",
        className="mb-3",
    )

    return dbc.Container(
        [
            html.H1("Sportsbook Prop Projections"),
            scoring_controls,
            info,
            dcc.Dropdown(
                id="proj-position-filter",
                options=[{"label": pos, "value": pos} for pos in positions],
                multi=True,
                placeholder="Filter by position",
            ),
            AgGrid(
                id="proj-grid",
                columnDefs=[
                    {"headerName": "Name", "field": "Name", "sortable": True, "filter": True},
                    {"headerName": "Position", "field": "Pos", "sortable": True, "filter": True},
                    {
                        "headerName": "Model Points",
                        "field": "ModelPoints",
                        "sortable": True,
                        "filter": True,
                        "sort": "desc",
                    },
                ],
                rowData=proj_df.to_dict("records"),
                defaultColDef={"resizable": True, "filter": True, "sortable": True},
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True, "rowBuffer": 0},
                className="ag-theme-alpine",
                style={"height": "70vh"},
            ),
        ],
        fluid=True,
    )


@callback(
    Output("proj-grid", "rowData"),
    [
        Input("proj-position-filter", "value"),
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
    selected_positions,
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
    """Recalculate scores and filter grid based on user selections."""

    config = deepcopy(SCORING_CONFIG_DEFAULT)

    if pass_yds_pt is not None:
        config["QB"]["PassYds"]["points_per"] = pass_yds_pt
    if pass_td_pts is not None:
        config["QB"]["PassTD"]["points"] = pass_td_pts
    if int_pen is not None:
        config["QB"]["Int"]["points"] = int_pen

    if rush_yds_pt is not None:
        for pos in ("QB", "RB", "WR"):
            if "RushYds" in config[pos]:
                config[pos]["RushYds"]["points_per"] = rush_yds_pt
    if rush_td_pts is not None:
        for pos in ("QB", "RB", "WR"):
            if "RushTD" in config[pos]:
                config[pos]["RushTD"]["points"] = rush_td_pts
    if fum_pen is not None:
        for pos in ("QB", "RB", "WR", "TE"):
            if "Fum" in config[pos]:
                config[pos]["Fum"]["points"] = fum_pen

    if rec_yds_pt is not None:
        for pos in ("RB", "WR", "TE"):
            if "RecYds" in config[pos]:
                config[pos]["RecYds"]["points_per"] = rec_yds_pt
    if rec_per is not None:
        for pos in ("RB", "WR", "TE"):
            if "Rec" in config[pos]:
                config[pos]["Rec"]["points_per"] = rec_per
    if rec_td_pts is not None:
        for pos in ("RB", "WR", "TE"):
            if "RecTD" in config[pos]:
                config[pos]["RecTD"]["points"] = rec_td_pts

    df = calculate_prop_points(proj_df, config=config)

    if selected_positions:
        df = df[df["Pos"].isin(selected_positions)]

    return df.to_dict("records")
