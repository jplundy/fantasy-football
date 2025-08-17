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
                placeholder="Select Position",
            ),
            dbc.Tooltip("Filter players by position", target='position-filter'),
        ], xs=12, sm=6, md=3),
        dbc.Col([
            dcc.Input(id='search-input', type='text', placeholder='Search players...', className="form-control"),
            dbc.Tooltip("Search by player name", target='search-input'),
        ], xs=12, sm=6, md=3)
    ], className="mb-4 g-2")


def create_scoring_controls():
    passing = dbc.Row([
        dbc.Col([
            dbc.Label("Pass Yds per Point"),
            dcc.Input(id='pass-yds-pt', type='number', value=25, className="form-control", placeholder='e.g., 25'),
            dbc.Tooltip("Number of passing yards for one point", target='pass-yds-pt'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("Pass TD Points"),
            dcc.Input(id='pass-td-pts', type='number', value=6, className="form-control", placeholder='e.g., 6'),
            dbc.Tooltip("Points awarded per passing TD", target='pass-td-pts'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("INT Penalty"),
            dcc.Input(id='int-pen', type='number', value=-3, className="form-control", placeholder='e.g., -3'),
            dbc.Tooltip("Penalty for throwing an interception", target='int-pen'),
        ], xs=12, sm=6, md=4),
    ], className="g-2")

    rushing = dbc.Row([
        dbc.Col([
            dbc.Label("Rush Yds per Point"),
            dcc.Input(id='rush-yds-pt', type='number', value=10, className="form-control", placeholder='e.g., 10'),
            dbc.Tooltip("Number of rushing yards for one point", target='rush-yds-pt'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("Rush TD Points"),
            dcc.Input(id='rush-td-pts', type='number', value=6, className="form-control", placeholder='e.g., 6'),
            dbc.Tooltip("Points awarded per rushing TD", target='rush-td-pts'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("Fumble Penalty"),
            dcc.Input(id='fum-pen', type='number', value=-3, className="form-control", placeholder='e.g., -3'),
            dbc.Tooltip("Penalty for a lost fumble", target='fum-pen'),
        ], xs=12, sm=6, md=4),
    ], className="g-2")

    receiving = dbc.Row([
        dbc.Col([
            dbc.Label("Rec Yds per Point"),
            dcc.Input(id='rec-yds-pt', type='number', value=10, className="form-control", placeholder='e.g., 10'),
            dbc.Tooltip("Receiving yards for one point", target='rec-yds-pt'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("Receptions per Point"),
            dcc.Input(id='rec-per', type='number', value=5, className="form-control", placeholder='e.g., 5'),
            dbc.Tooltip("Number of receptions for one point", target='rec-per'),
        ], xs=12, sm=6, md=4),
        dbc.Col([
            dbc.Label("Rec TD Points"),
            dcc.Input(id='rec-td-pts', type='number', value=6, className="form-control", placeholder='e.g., 6'),
            dbc.Tooltip("Points awarded per receiving TD", target='rec-td-pts'),
        ], xs=12, sm=6, md=4),
    ], className="g-2")

    return html.Div([
        html.H4("Scoring Settings"),
        dbc.Accordion([
            dbc.AccordionItem(passing, title="Passing"),
            dbc.AccordionItem(rushing, title="Rushing"),
            dbc.AccordionItem(receiving, title="Receiving"),
        ], start_collapsed=True),
    ], className="mb-4")


def create_draft_input(players, teams):
    return dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='draft-name',
                options=[{'label': player, 'value': player} for player in players],
                placeholder="Select Player",
            ),
            dbc.Tooltip("Choose the player being drafted", target='draft-name'),
        ], xs=12, sm=6, md=3),
        dbc.Col([
            dcc.Dropdown(
                id='draft-team',
                options=[{'label': f'Team {i}', 'value': f'Team {i}'} for i in range(1, teams + 1)],
                placeholder="Select Team",
            ),
            dbc.Tooltip("Assign the player to a team", target='draft-team'),
        ], xs=12, sm=6, md=3),
        dbc.Col([
            dcc.Input(id='draft-price', type='number', placeholder='Price Paid', className="form-control"),
            dbc.Tooltip("Amount spent on the player", target='draft-price'),
        ], xs=12, sm=6, md=2),
        dbc.Col([
            dbc.Button('Draft Player', id='draft-button', color="primary", className="me-2"),
            dbc.Button('Undo Last Pick', id='undo-button', color="secondary"),
        ], xs=12, sm=6, md=4),
    ], className="mb-4 g-2")


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
        style={"height": 1600},
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
            ], className="mb-3", style={'width': '100%'}) for i in range(1, teams + 1)
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
        create_scoring_controls(),
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
        create_graphs(),
    ], fluid=True)

