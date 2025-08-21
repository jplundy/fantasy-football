"""Interactive sportsbook projection page.

This page loads prop projections from the local assets directory and lets
users tweak high level scoring settings.  The projections are recalculated on
each change and the grid below updates with the recomputed ``ModelPoints``.

Missing statistical categories in the underlying data are treated as zeros so
players without, for example, receiving stats will still appear with a score.
"""

import dash
from dash import html, dcc, Input, Output, callback, State
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc

from utility.helpers import get_sportsbook_props
from utility.scoring import calculate_prop_points, SCORING_CONFIG_DEFAULT, load_config
from pathlib import Path

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
                        "valueFormatter": {"function": "Number(params.value).toFixed(2)"},
                    },
                ],
                rowData=calculate_prop_points(proj_df, config=load_config(Path("assets/settings.json"))).to_dict("records"),
                defaultColDef={"resizable": True, "filter": True, "sortable": True},
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True, "rowBuffer": 0},
                columnSize="autoSize",
                className="ag-theme-alpine",
                style={"height": "70vh"},
            ),
        ],
        fluid=True,
    )


@callback(
    Output("proj-grid", "rowData"),
    [Input("proj-position-filter", "value")],
    State("scoring-config", "data"),
)
def update_grid(selected_positions, config):
    """Recalculate scores and filter grid based on user selections."""

    cfg = config or SCORING_CONFIG_DEFAULT
    df = calculate_prop_points(proj_df, config=cfg)

    if selected_positions:
        df = df[df["Pos"].isin(selected_positions)]

    return df.to_dict("records")
