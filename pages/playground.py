import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_table
import plotly.express as px
from utility import helpers


dash.register_page(__name__, path='/playground')

# Load data used in this playground
sched_data = helpers.clean_schedule(helpers.get_schedule())
qb_data = helpers.clean_offense_data(helpers.get_position_data('QB'), pos='QB')


def layout():
    return dbc.Container(
        [
            html.H1("Playground"),
            html.H2("2025 Schedule"),
            dash_table.DataTable(
                id='schedule-table',
                columns=[{'name': c, 'id': c} for c in sched_data.columns],
                data=sched_data.to_dict('records'),
                page_size=20,
            ),
            html.H2("QB Passing Yards Distribution"),
            dcc.Dropdown(
                id='qb-playground-dropdown',
                options=[{'label': n, 'value': n} for n in qb_data['Name'].unique()],
                value=qb_data['Name'].iloc[0],
            ),
            dcc.Graph(id='qb-passing-hist'),
        ],
        fluid=True,
    )


@callback(Output('qb-passing-hist', 'figure'), Input('qb-playground-dropdown', 'value'))
def update_qb_hist(name):
    filtered = qb_data[qb_data['Name'] == name]
    fig = px.histogram(filtered, x='PassYds', nbins=20, title=f'Passing Yards for {name}')
    return fig
