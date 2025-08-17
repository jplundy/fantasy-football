from dash import html
import dash

dash.register_page(__name__, path='/')

layout = html.Div([
    html.H1("Welcome to the Fantasy Football Auction Draft"),
    html.P("Use the navigation bar to access different sections of the app.")
])
