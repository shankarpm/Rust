import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from flask import Flask, request
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# Initialize the Flask server
server = Flask(__name__)

# Initialize the main Dash app
dash_app = dash.Dash(__name__, server=server, url_base_pathname='/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# summarizer_app_url = '/webapp1'
app_urls = {
    'App 1': 'http://10.195.176.87:8000/documentsummarizer',
    'App 2': '/webapp2'
}

# Define the layout of the home page
dash_app.layout = html.Div([
    html.Div(id='welcome-message', style={'textAlign': 'right', 'padding': '10px', 'fontSize': '20px'}),
    
    dbc.Row([
        dbc.Col(
            html.Img(src='./assets/nyl.png', style={'height': '80px'}),
            width="auto"
        ),
        dbc.Col([
            html.H1("Data Science Platform App Gallery", style={'fontSize': '36px'}),
            html.H2("New York Life Investments", style={'fontSize': '24px'})
        ])
    ], align="center"),
    html.Div([
        dbc.Card(
            dbc.CardBody([
                html.H5("Document Summarizer", className="card-title"),
                html.P("AI-powered service to summarize pdf documents, ask questions"),
                html.A("Go", id='app1-link', href=app_urls['App 1'], className="btn btn-primary_home disabled", **{"data-app-id": "1340"})
            ]),
            id="app1-card",
            className="m-3",
            style={'backgroundColor': '#f8f9fa'}
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5("Email Subjectline Optimizer", className="card-title"),
                html.P("Predictive analysis to determine the best email subject line"),
                html.A("Go", id='app2-link', href=app_urls['App 2'], className="btn btn-primary_home disabled", **{"data-app-id": "1450"})
            ]),
            id="app2-card",
            className="m-3",
            style={'backgroundColor': '#f8f9fa'}
        ),
    ], style={'display': 'flex', 'flex-direction': 'row'}),
    
    html.Div(id='header-info'),
    dcc.Interval(id='interval-component', interval=1*10000, n_intervals=1),
])

@dash_app.callback(
    [Output('welcome-message', 'children'),
     Output('header-info', 'children'),
     Output('app1-link', 'className'),
     Output('app2-link', 'className')],
    [Input('interval-component', 'n_intervals')]
)
def update_metrics(n):
    headers_data = {key: value for key, value in request.headers.items()}
    print(f"headers - data 2 - {headers_data}")
    username = ''  # Adjust this to extract the correct username if available
    aws_role = 'App1'  # Adjust this to extract the correct role if available

    app1_status = app2_status = 0
    if aws_role == "App1":
        app1_status = 1
        app2_status = 0
    elif aws_role == "App2":
        app1_status = 1
        app2_status = 1

    app1_class = "btn btn-primary_home"  # if app1_status == 1 else "btn btn-primary_home disabled"
    app2_class = "btn btn-primary_home" if app2_status == 1 else "btn btn-primary_home disabled"

    welcome_message = f"Welcome {username}"

    children = []

    return welcome_message, children, app1_class, app2_class

# Import the additional Dash apps

from documentsummarizer import docsapp

# Create the dispatcher middleware to route requests to the respective Dash app
app = DispatcherMiddleware(server, {
    '/documentsummarizer': docsapp.server,
})

# Ensure Gunicorn uses the correct app
if __name__ == '__main__':
    dash_app.run_server(debug=True)
