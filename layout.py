from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from dash import html, dcc

def create_filters(positions):
    return dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='position-filter',
                options=[{'label': pos, 'value': pos} for pos in positions] + [{'label': 'All', 'value': 'All'}],
                value='All',
                placeholder="Select Position"
            )
        ], width=3),
        dbc.Col([
            dcc.Input(id='search-input', type='text', placeholder='Search players...', className="form-control")
        ], width=3)
    ], className="mb-4")

def create_draft_input(players, teams):
    return dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='draft-name',
                options=[{'label': player, 'value': player} for player in players],
                placeholder="Select Player"
            )
        ], width=3),
        dbc.Col([
            dcc.Dropdown(
                id='draft-team',
                options=[{'label': f'Team {i}', 'value': f'Team {i}'} for i in range(1, teams + 1)],
                placeholder="Select Team"
            )
        ], width=3),
        dbc.Col([
            dcc.Input(id='draft-price', type='number', placeholder='Price Paid', className="form-control")
        ], width=2),
        dbc.Col([
            dbc.Button('Draft Player', id='draft-button', color="primary", className="mr-2"),
            dbc.Button('Undo Last Pick', id='undo-button', color="secondary")
        ], width=4)
    ], className="mb-4")

def create_player_table():
    return AgGrid(
        id='player-table',
        columnDefs=[
            {"headerName": "Name", "field": "Name", "filter": True, "sortable": True},
            {"headerName": "Position", "field": "Position", "filter": True, "sortable": True},
            {"headerName": "Team", "field": "Team", "filter": True, "sortable": True},
            {"headerName": "Auction Value", "field": "AuctionValue", "filter": True, "sortable": True},
            {"headerName": "Drafted", "field": "Drafted", "filter": True, "sortable": True},
            {"headerName": "Drafted By", "field": "DraftedBy", "filter": True, "sortable": True},
            {"headerName": "Price Paid", "field": "PricePaid", "filter": True, "sortable": True}
        ],
        rowData=[],
        defaultColDef={"resizable": True, "filter": True, "sortable": True},
        dashGridOptions={"pagination": True, "paginationAutoPageSize": True},
        className="ag-theme-alpine",
        style={"height": 1600}
    )

def create_draft_summary():
    return html.Div([
        html.H3("Overall Draft Summary"),
        html.Div(id='draft-summary')
    ])

def create_team_summaries(teams):
    return html.Div([
        html.H3("Team Summaries"),
        dbc.Row([
            dbc.Card([
                dbc.CardHeader(f"Team {i}"),
                dbc.CardBody([
                    html.Div(id=f'team-{i}-summary'),
                    html.Div(id=f'team-{i}-remaining-budget', className="mt-2 font-weight-bold"),
                    dcc.Graph(id=f'team-{i}-composition-chart')
                ])
            ], className="mb-3", style={'width':'100%'}) for i in range(1, teams + 1)
        ])
    ])

def create_graphs():
    return html.Div([
        dcc.Graph(id='value-distribution-graph'),
        dcc.Graph(id='top-players-graph')
    ])

def create_layout(players, positions, teams):
    return dbc.Container([
        html.H1("Fantasy Football Draft Dashboard", className="my-4"),
        create_filters(positions),
        create_draft_input(players, teams),
        dbc.Row([
            dbc.Col(create_player_table(), width=12),
        ]),
        dbc.Row([
            create_team_summaries(teams)
        ]),
        dbc.Row([
            dbc.Col([create_draft_summary()], width=12)
        ]),
        html.Div(id='draft-message', className="mt-3"),
        create_graphs()
    ], fluid=True)