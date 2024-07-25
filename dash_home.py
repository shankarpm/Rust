import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from flask import Flask, request,jsonify
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Initialize the Flask server
server = Flask(__name__)

# Initialize the Dash app
dash_app = dash.Dash(__name__, server=server, url_base_pathname='/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the URLs associated with each app
app_urls = {
    'App 1': 'http://10.195.176.87:8000/documentsummarizer/',
    'App 2': 'http://10.195.176.87:8000/'
}

# Define the layout of the home page
dash_app.layout = html.Div([
    # Welcome message placeholder
    html.Div(id='welcome-message', style={'textAlign': 'right', 'padding': '10px','fontSize': '20px'}),
    
   # html.H1("Data Science Platform App Gallery", style={'fontSize': '36px'}),
   # html.H2("New York Life Investments", style={'fontSize': '24px'}),
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
                html.P("AI-powered service to summarize pdf documents,ask questions"),
                html.A("Go", id='app1-link', href=app_urls['App 1'], className="btn btn-primary disabled", **{"data-app-id": "1340"})
            ]),
            id="app1-card",
            className="m-3",
            style={'backgroundColor': '#f8f9fa'} 
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5("Email Subjectline Optimizer", className="card-title"),
                html.P("Predictive analysis to determine the best email subject line"),
                html.A("Go", id='app2-link', href=app_urls['App 2'], className="btn btn-primary disabled", **{"data-app-id": "1450"})
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
    username =  ''# headers_data['Cn'] #+ "-1" #-#'Nylauthid']#.get("User", "Guest")
    #username = 'Guest'
    aws_role = 'App1' #headers_data.get("Awsrole", "")

    app1_status = app2_status = 0
    if aws_role == "App1":
        app1_status = 1
        app2_status = 0
    elif aws_role == "App2":
        app1_status = 1
        app2_status = 1

    app1_class = "btn btn-primary" #if app1_status == 1 else "btn btn-primary disabled"
    app2_class = "btn btn-primary" if app2_status == 1 else "btn btn-primary disabled"

    welcome_message = f"Welcome {username}"

    children = [
        #html.Div(f"Test header data: {username}"),
        #html.Div(f"App 1 button class: {app1_class}"),
        #html.Div(f"App 2 button class: {app2_class}")
    ]

    return welcome_message, children, app1_class, app2_class

# Import the additional Dash apps
from documentsummarizer import docsapp

# Create the dispatcher middleware to route requests to the respective Dash app
app = DispatcherMiddleware(server, {
    '/documentsummarizer': docsapp.server
})

# Run the server
if __name__ == '__main__':
    run_simple('localhost', 8000, app, use_reloader=True, use_debugger=True)
