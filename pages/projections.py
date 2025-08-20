import dash
from dash import html, dcc, Input, Output, callback
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from utility.helpers import get_season_long_projections

# Register the projections page

dash.register_page(__name__, path='/projections')

# Load projection data
proj_df = get_season_long_projections()


def layout():
    """Layout for the season-long projections page."""
    positions = sorted(proj_df['Pos'].dropna().unique())
    return dbc.Container(
        [
            html.H1("Season-long Projections"),
            dcc.Dropdown(
                id='proj-position-filter',
                options=[{"label": pos, "value": pos} for pos in positions],
                multi=True,
                placeholder="Filter by position",
            ),
            AgGrid(
                id='proj-grid',
                columnDefs=[
                    {"headerName": "Name", "field": "Name", "sortable": True, "filter": True},
                    {"headerName": "Position", "field": "Pos", "sortable": True, "filter": True},
                    {
                        "headerName": "Projections",
                        "field": "Projections",
                        "sortable": True,
                        "filter": True,
                        "sort": "desc",
                    },
                ],
                rowData=proj_df.to_dict('records'),
                defaultColDef={"resizable": True, "filter": True, "sortable": True},
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True, "rowBuffer": 0},
                className="ag-theme-alpine",
                style={"height": "70vh"},
            ),
        ],
        fluid=True,
    )


@callback(Output('proj-grid', 'rowData'), Input('proj-position-filter', 'value'))
def update_grid(selected_positions):
    """Filter grid data based on selected positions."""
    if selected_positions:
        filtered = proj_df[proj_df['Pos'].isin(selected_positions)]
    else:
        filtered = proj_df
    return filtered.to_dict('records')
