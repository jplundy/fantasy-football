from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from dash import html, dcc

def create_scoring_controls():
    return dbc.Row([
        dbc.Col([
            html.H4("Scoring Settings"),
            dbc.Label("Pass Yds per Point"),
            dcc.Input(id='pass-yds-pt', type='number', value=25, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Pass TD Points"),
            dcc.Input(id='pass-td-pts', type='number', value=6, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("INT Penalty"),
            dcc.Input(id='int-pen', type='number', value=-3, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Rush Yds per Point"),
            dcc.Input(id='rush-yds-pt', type='number', value=10, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Rush TD Points"),
            dcc.Input(id='rush-td-pts', type='number', value=6, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Fumble Penalty"),
            dcc.Input(id='fum-pen', type='number', value=-3, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Rec Yds per Point"),
            dcc.Input(id='rec-yds-pt', type='number', value=10, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Receptions per Point"),
            dcc.Input(id='rec-per', type='number', value=5, className="form-control"),
        ], width=2),
        dbc.Col([
            dbc.Label("Rec TD Points"),
            dcc.Input(id='rec-td-pts', type='number', value=6, className="form-control"),
        ], width=2),
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
        dashGridOptions={"pagination": True, "paginationAutoPageSize": True, "rowBuffer": 0},
        className="ag-theme-alpine",
        style={"height": "70vh"}
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

def create_layout(players, teams):
    return dbc.Container([
        html.H1("Fantasy Football Draft Dashboard", className="my-4"),
        create_scoring_controls(),
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
