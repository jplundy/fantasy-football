import dash
from dash import dcc, html
import dash_bootstrap_components as dbc  # Optional for better styling


app = dash.Dash(__name__, 
                use_pages=True,
                title='FF',
                update_title='****',
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Define the main layout with navigation links
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.NavbarSimple(
                    children=
                        [
                            dbc.NavItem(dbc.NavLink("2023 Draft Values", href="/2023draftboard")),
                            dbc.NavItem(dbc.NavLink("Draft Board", href="/draftboard")),
                            dbc.NavItem(dbc.NavLink("Offense Data", href="/offensedata")),
                        ],
                    brand="sigFantasy",
                    brand_href="/",
                    color="grey",
                    fluid=True,
                    style={'width':'100%', 'height':'100%', 'padding':'0px', 'margin':'0px'},
                )
            ],
            style={'width':'100%', 'height':'100%', 'padding':'0px', 'margin':'0px'}
        ),
        dbc.Row(dash.page_container,style={'width':'100%', 'height':'100%', 'padding':'0px', 'margin':'0px'})
    ],
fluid=True,
style={'width':'100%', 'height':'100%', 'padding':'0px', 'margin':'0px'}
)

def run():
    return None

if __name__ == '__main__':
    app.run_server(debug=True,
                   )
    # run()
