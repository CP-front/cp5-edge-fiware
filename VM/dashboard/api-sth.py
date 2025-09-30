import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import requests
from datetime import datetime
import json
import pytz

# --- CONFIGURAÇÃO DO AMBIENTE ---
IP_ADDRESS = "20.81.162.205"
PORT_STH = 8666
PORT_ORION = 1026
DASH_HOST = "0.0.0.0"

# --- CONFIGURAÇÃO DO DISPOSITIVO E ALERTAS ---
DEVICE_ID = "urn:ngsi-ld:Lamp:EDGE4"
TRIGGERS = {
    'temperature': {'min': 10.0, 'max': 18.0},
    'humidity':    {'min': 50.0, 'max': 80.0},
    'luminosity':  {'min': -1,   'max': 10}
}
estado_alerta_anterior = ""

def convert_to_sao_paulo_time(timestamps_utc_str):
    utc_zone = pytz.utc
    sp_zone = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for ts_str in timestamps_utc_str:
        dt_utc = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        dt_sp = dt_utc.astimezone(sp_zone)
        converted_timestamps.append(dt_sp)
    return converted_timestamps

def get_data_from_sth(attribute, params):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/{DEVICE_ID}/attributes/{attribute}"
    headers = {'fiware-service': 'smart', 'fiware-servicepath': '/'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['contextResponses'][0]['contextElement']['attributes'][0]['values']
        return []
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return []

def enviar_comando_fiware(led_cmd):
    global estado_alerta_anterior
    if led_cmd != estado_alerta_anterior:
        url_comando = f"http://{IP_ADDRESS}:{PORT_ORION}/v2/entities/{DEVICE_ID}/attrs"
        payload = {"led": {"type": "command", "value": led_cmd}}
        headers = {'Content-Type': 'application/json', 'fiware-service': 'smart', 'fiware-servicepath': '/'}
        try:
            requests.patch(url_comando, headers=headers, data=json.dumps(payload), timeout=5)
            print(f"Comando '{led_cmd}' enviado com sucesso.")
            estado_alerta_anterior = led_cmd
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão ao enviar comando: {e}")

# --- ADICIONA A FOLHA DE ESTILOS EXTERNA ---
app = dash.Dash(__name__, external_stylesheets=['/assets/custom.css'])
app.title = "Dashboard da Vinheria"

# --- O LAYOUT VOLTA A TER A COR DE FUNDO DEFINIDA DIRETAMENTE ---
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#DDDDDD', 'fontFamily': 'sans-serif'}, children=[
    html.H1('Dashboard da Vinheria', style={'textAlign': 'center', 'padding': '20px'}),
    html.Div(id='alert-message', style={'textAlign': 'center', 'fontSize': '20px', 'fontWeight': 'bold', 'padding': '10px'}),
    dcc.Graph(id='sensor-graph'),
    dcc.Interval(id='interval-component', interval=3*1000, n_intervals=0)
])

@app.callback(
    [Output('sensor-graph', 'figure'),
     Output('alert-message', 'children'),
     Output('alert-message', 'style')],
    Input('interval-component', 'n_intervals')
)
def update_dashboard(n):
    temp_data = get_data_from_sth('temperature', {'lastN': 1})
    hum_data = get_data_from_sth('humidity', {'lastN': 1})
    lum_data = get_data_from_sth('luminosity', {'lastN': 1})

    alert_messages = []
    alert_style = {'textAlign': 'center', 'fontSize': '20px', 'fontWeight': 'bold', 'color': '#4CAF50'}
    comando_prioritario = "desligar"

    if temp_data and hum_data and lum_data:
        temp = float(temp_data[0]['attrValue'])
        umid = float(hum_data[0]['attrValue'])
        lum = int(lum_data[0]['attrValue'])

        if not (TRIGGERS['temperature']['min'] < temp < TRIGGERS['temperature']['max']):
            alert_messages.append(f"ALERTA: Temperatura fora do padrão! ({temp}°C)")
            if comando_prioritario == "desligar": comando_prioritario = "piscar_temp"
        
        if not (TRIGGERS['humidity']['min'] < umid < TRIGGERS['humidity']['max']):
            alert_messages.append(f"ALERTA: Umidade fora do padrão! ({umid}%)")
            if comando_prioritario == "desligar": comando_prioritario = "piscar_umid"

        if not (TRIGGERS['luminosity']['min'] < lum < TRIGGERS['luminosity']['max']):
            alert_messages.append(f"ALERTA: Luminosidade fora do padrão! ({lum}%)")
            if comando_prioritario == "desligar": comando_prioritario = "piscar_lum"
        
        enviar_comando_fiware(comando_prioritario)

    final_alert_children = []
    if alert_messages:
        for i, msg in enumerate(alert_messages):
            final_alert_children.append(msg)
            if i < len(alert_messages) - 1:
                final_alert_children.append(html.Br())
        alert_style['color'] = '#F44336'
    else:
        final_alert_children = "Condições ideais."

    history_size = 50
    temp_history = get_data_from_sth('temperature', {'lastN': history_size})
    hum_history = get_data_from_sth('humidity', {'lastN': history_size})
    lum_history = get_data_from_sth('luminosity', {'lastN': history_size})
    
    def prepare_trace_data(history_data):
        if not history_data: return [], []
        sorted_data = sorted(history_data, key=lambda x: x['recvTime'])
        timestamps_utc = [v['recvTime'] for v in sorted_data]
        timestamps_sp = convert_to_sao_paulo_time(timestamps_utc)
        values = [float(v['attrValue']) for v in sorted_data]
        return timestamps_sp, values

    temp_ts, temp_vals = prepare_trace_data(temp_history)
    hum_ts, hum_vals = prepare_trace_data(hum_history)
    lum_ts, lum_vals = prepare_trace_data(lum_history)

    traces = [
        go.Scatter(x=temp_ts, y=temp_vals, mode='lines+markers', name='Temperatura (°C)', line={'color': '#FF5733'}),
        go.Scatter(x=hum_ts, y=hum_vals, mode='lines+markers', name='Umidade (%)', line={'color': '#33CFFF'}),
        go.Scatter(x=lum_ts, y=lum_vals, mode='lines+markers', name='Luminosidade (%)', line={'color': '#F1C40F'})
    ]
    
    layout = go.Layout(
        title='Monitoramento em Tempo Real',
        xaxis_title='Horário (São Paulo)',
        yaxis_title='Valores',
        plot_bgcolor='#222222',
        paper_bgcolor='#111111',
        font={'color': '#DDDDDD'},
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'right', 'x': 1}
    )
    
    figure = {'data': traces, 'layout': layout}
    return figure, final_alert_children, alert_style

if __name__ == '__main__':
    app.run(debug=True, host=DASH_HOST, port=8050)
