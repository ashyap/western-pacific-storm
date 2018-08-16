import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from csv import DictReader
from datetime import datetime
from dash.dependencies import Input, Output
from toolz import compose, pluck, groupby, valmap, first, unique, get, countby

app = dash.Dash()
# For Heroku deployment.
server = app.server
# Don't understand this one bit, but apparently it's needed.
# server.secret_key = os.environ.get("SECRET_KEY", "secret")

# # Boostrap CSS.
# app.css.append_css({
#     "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"
# })
#
# # Extra Dash styling.
# app.css.append_css({
#     "external_url": 'https://codepen.io/chriddyp/pen/bWLwgP.css'
# })
#
# # JQuery is required for Bootstrap.
# app.scripts.append_script({
#     "external_url": "https://code.jquery.com/jquery-3.2.1.min.js"
# })
#
# # Bootstrap Javascript.
# app.scripts.append_script({
#     "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"
# })


with open('storms_scraped_cleaned.csv','r') as f:
    reader = DictReader(f)
    STORM_DATA = [line for line in reader]

listfilter = compose(list, filter)
listpluck = compose(list, pluck)

pacific_df = pd.read_csv('storms_scraped_cleaned.csv')
pacific_df['datetime'] = pd.to_datetime(pacific_df['datetime'])
pacific_df['storm_name'] = [name.strip() for name in pacific_df['storm_name']]

def get_storms(year):
    return pacific_df[(pacific_df['datetime'].dt.year == year)]

def filter_storms_by_year(year):
    return listfilter(
        lambda x: year == datetime.strptime(x['datetime'], '%m/%d/%Y %H:%M').year,
        STORM_DATA)

def storm_type_month(storm):
    return datetime.strptime(storm['datetime'], '%m/%d/%Y %H:%M').month

def get_years():
    year_dic_list = []
    years = listpluck("datetime", STORM_DATA)
    years = set(datetime.strptime(year, '%m/%d/%Y %H:%M').year for year in years)
    for year in years:
        year_dic_list.append({'label': str(year), 'value': str(year)})
    return year_dic_list

years = get_years()
storm_list = []

layout = dict(
        title = 'Most trafficked US airports<br>(Hover for airport names)',
        colorbar = True,
        geo = dict(
            scope='usa',
            projection=dict( type='albers usa' ),
            showland = True,
            landcolor = "rgb(250, 250, 250)",
            subunitcolor = "rgb(217, 217, 217)",
            countrycolor = "rgb(217, 217, 217)",
            countrywidth = 0.5,
            subunitwidth = 0.5
        ),
    )

app.layout = html.Div([
    # Row: Title
    html.Div([
        # Column: Title
        html.Div([
            html.H1("Western Pacific Storms", className="text-center")
        ], className="col-md-12")
    ], className="row"),
    # Row: Filter + References
    html.Div([
        # Column: Filter
        html.Div([
            html.P([
                html.B("Years:  "),
                dcc.Dropdown(
                    id='years',
                    options=years,
                    value=years[0]['value'],
                    multi=False
                ),
            ]),
        ], className="col-md-6"),
        # Column: References.
        html.Div([
            html.P([
                "Data from ",
                html.A("wunderground.com", href="https://www.wunderground.com")
            ], style={"text-align": "right"})
        ], className="col-md-6")
    ], className="row"),
    # Row: Map + Bar Chart
    html.Div([
        # Column: Map
        html.Div([
            dcc.Graph(id="storm-map")
        ], className="col-md-8"),
        #Column: Donut Chart
        html.Div([
            dcc.Graph(id="storm-class")
        ], className="col-md-4")
    ], className="row"),
    # Row: Line Chart + Donut Chart
    html.Div([
        # Column: Line Chart
        html.Div([
            dcc.Graph(id="storm-type-month")
        ], className="col-md-8"),
        # Column: Bar Chart
        html.Div([
            dcc.Graph(id="storm-pressure-class")
        ], className="col-md-4")
    ], className="row"),
], className="container-fluid")

@app.callback(
    dash.dependencies.Output('storm-map', 'figure'),
    [Input(component_id='years', component_property='value')]
)
def get_storm_map(value):
    storms = filter_storms_by_year(int(value))
    return {
        'data': [
            {
                'lat': listpluck("latitude", storm_details),
                'lon': listpluck("longitude", storm_details),
                "text": storm_name,
                'marker': {
                    'size': 8,
                    'opacity': 0.6
                },
                'type': 'scattermapbox',
                'showlegend': False
            }
            for storm_name, storm_details in groupby('storm_name', storms).items()
        ],
        'layout': {
            'mapbox': {
                'accesstoken': 'pk.eyJ1IjoiY2hyaWRkeXAiLCJhIjoiY2ozcGI1MTZ3MDBpcTJ3cXR4b3owdDQwaCJ9.8jpMunbKjdq1anXwU5gxIw'
            },
            'hovermode': 'closest',
            'margin': {'l': 0, 'r': 0, 'b': 0, 't': 0}
        }
    }

@app.callback(
    dash.dependencies.Output('storm-class', 'figure'),
    [Input(component_id='years', component_property='value')]
)
def get_storm_class(value):
    storms = filter_storms_by_year(int(value))
    storms_by_class = countby("storm_type", storms)
    return {
        "data": [
            {
                "type": "pie",
                "labels": list(storms_by_class.keys()),
                "values": list(storms_by_class.values()),
                "hole": 0.4,
                'showlegend': False
            }
        ],
        "layout": {
            "title": "Storm by Class"
        }
    }

@app.callback(
    dash.dependencies.Output('storm-type-month', 'figure'),
    [Input(component_id='years', component_property='value')]
)
def get_storm_type_count_per_month(value):
    storms = filter_storms_by_year(int(value))

    storm_type_per_month = {
        storm_type:
            sorted(
                list(
                    # Group by month -> count.
                    countby(storm_type_month, storms_details).items()
                ),
                # Sort by month.
                key=first
            )
        for storm_type, storms_details
        in groupby('storm_type', storms).items()
    }

    months = range(1,13)
    month_names=[
        'January', 'February', 'March',
        'April', 'May', 'June',
        'July', 'August', 'September',
        'October', 'November', 'December'
    ]

    for storm_type, details in storm_type_per_month.items():
        month_details = listpluck(0, details)
        missing_months = set(months) - set(month_details)
        empty_months = [(month,0) for month in missing_months]
        storm_type_per_month[storm_type] = empty_months + details
        storm_type_per_month[storm_type] = \
            sorted(storm_type_per_month[storm_type], key=lambda tup: tup[0])

    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": storm_type,
                "x": month_names,
                "y": listpluck(1, storms_details)
            }
            for storm_type, storms_details
            in storm_type_per_month.items()
        ],
        "layout": {
            "title": "Storm Count by Type per Month"
        }
    }

@app.callback(
    dash.dependencies.Output('storm-pressure-class', 'figure'),
    [Input(component_id='years', component_property='value')]
)
def get_storm_pressure_class(value):
    storms = filter_storms_by_year(int(value))
    traces = []
    for storm_type, storm_details in groupby('storm_type', storms).items():
        traces.append(
            go.Box(
                y=listpluck('pressure', storm_details),
                name=storm_type,
                showlegend=False
            )
        )

    layout = go.Layout(
        title = "Storm Pressure per Class"
    )
    fig = go.Figure(data=traces,layout=layout)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
