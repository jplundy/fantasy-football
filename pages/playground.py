import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_table
import plotly.express as px
from utility import helpers


dash.register_page(__name__, path='/playground')

# Load data used in this playground
# Transform the schedule into a grid where each team occupies a row and each
# week is a column.  Cells show the opponent and are prefixed with '@' when the
# game is on the road.
_sched_long = helpers.clean_schedule(helpers.get_schedule())
_sched_long['Opponent_Display'] = _sched_long.apply(
    lambda r: (
        'BYE'
        if r['Game_Type'] == 'BYE'
        else ('@' + r['Opponent'] if r['Location'] == 'Away' else r['Opponent'])
    ),
    axis=1,
)
sched_data = (
    _sched_long
    .pivot(index='TEAM', columns='Week', values='Opponent_Display')
    .reset_index()
    .rename_axis(None, axis=1)
)
sched_data.columns = sched_data.columns.map(str)

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
