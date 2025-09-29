import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz

IP_ADDRESS = "20.81.162.205"
PORT_STH = 8666
DASH_HOST = "0.0.0.0"

def get_data(attribute, lastN):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/urn:ngsi-ld:Lamp:EDGE4/attributes/{attribute}?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as e:
            print(f"Key error: {e}")
            return []
    else:
        print(f"Error accessing {url}: {response.status_code}")
        return []

def convert_to_sao_paulo_time(timestamps):
    utc = pytz.utc
    sao_paulo = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for timestamp in timestamps:
        try:
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')).astimezone(sao_paulo)
        except ValueError:
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')).astimezone(sao_paulo)
        converted_timestamps.append(converted_time)
    return converted_timestamps

def clean_value(value):
    if isinstance(value, str):
        value = value.replace('°C', '').replace('%', '').strip()
    return float(value)

lastN = 10

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1('Sensor Data Viewer'),
    dcc.Graph(id='sensor-graph'),
    dcc.Store(id='sensor-data-store', data={'timestamps': [], 'luminosity_values': [], 'humidity_values': [], 'temperature_values': []}),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,
        n_intervals=0
    )
])

@app.callback(
    Output('sensor-data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('sensor-data-store', 'data')
)
def update_data_store(n, stored_data):
    data_luminosity = get_data('luminosity', lastN)
    data_humidity = get_data('humidity', lastN)
    data_temperature = get_data('temperature', lastN)

    if data_luminosity and data_humidity and data_temperature:
        luminosity_values = [float(entry['attrValue']) for entry in data_luminosity]
        humidity_values = [clean_value(entry['attrValue']) for entry in data_humidity]
        temperature_values = [clean_value(entry['attrValue']) for entry in data_temperature]
        timestamps = [entry['recvTime'] for entry in data_luminosity]

        timestamps = convert_to_sao_paulo_time(timestamps)

        stored_data['timestamps'].extend(timestamps)
        stored_data['luminosity_values'].extend(luminosity_values)
        stored_data['humidity_values'].extend(humidity_values)
        stored_data['temperature_values'].extend(temperature_values)

        return stored_data

    return stored_data

@app.callback(
    Output('sensor-graph', 'figure'),
    Input('sensor-data-store', 'data')
)
def update_graph(stored_data):
    if stored_data['timestamps']:
        trace_luminosity = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data['luminosity_values'],
            mode='lines+markers',
            name='Luminosity',
            line=dict(color='orange')
        )
        trace_humidity = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data['humidity_values'],
            mode='lines+markers',
            name='Humidity',
            line=dict(color='blue')
        )
        trace_temperature = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data['temperature_values'],
            mode='lines+markers',
            name='Temperature',
            line=dict(color='green')
        )

        fig = go.Figure(data=[trace_luminosity, trace_humidity, trace_temperature])

        fig.update_layout(
            title='Sensor Data Over Time',
            xaxis_title='Timestamp',
            yaxis_title='Values',
            hovermode='closest'
        )

        return fig

    return {}

if __name__ == '__main__':
    app.run_server(debug=True, host=DASH_HOST, port=8050)
