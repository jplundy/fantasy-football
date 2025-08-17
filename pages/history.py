import dash
from dash import html, dcc
import plotly.express as px
from utility import helpers


dash.register_page(__name__, path='/history')


def layout():
    df = helpers.get_draft_history()
    if df.empty:
        return html.Div([
            html.H1('Draft History'),
            html.P('No draft picks have been logged yet.')
        ])

    picks_per_owner = df.groupby('owner').size().reset_index(name='picks')
    spend_per_owner = df.groupby('owner')['price'].sum().reset_index(name='spent')

    fig1 = px.bar(picks_per_owner, x='owner', y='picks', title='Draft Picks by Owner')
    fig2 = px.bar(spend_per_owner, x='owner', y='spent', title='Total Spend by Owner')

    return html.Div([
        html.H1('Draft History'),
        dcc.Graph(figure=fig1),
        dcc.Graph(figure=fig2)
    ])
