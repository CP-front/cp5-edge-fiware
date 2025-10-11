# --- IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ---
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go  # Usado para criar os elementos do gráfico (linhas, layout)
import requests                 # Para fazer chamadas HTTP para as APIs do FIWARE
from datetime import datetime     # Para manipular datas e horas
import json                     # Para formatar os dados para as requisições HTTP
import pytz                     # Para lidar com fusos horários (Timezones)

# --- CONFIGURAÇÃO GLOBAL DO AMBIENTE ---
# Endereços IP e portas dos serviços FIWARE e do próprio dashboard.
IP_ADDRESS = "20.81.162.205"  # IP do servidor onde os serviços FIWARE estão a correr
PORT_STH = 8666               # Porta do STH-Comet, o serviço que armazena o histórico
PORT_ORION = 1026             # Porta do Orion Context Broker, o cérebro do FIWARE
DASH_HOST = "0.0.0.0"         # Faz com que o dashboard seja acessível de fora da VM

# --- CONFIGURAÇÃO DO DISPOSITIVO E REGRAS DE ALERTA ---
DEVICE_ID = "urn:ngsi-ld:Lamp:EDGE4"  # Identificador único do nosso dispositivo no FIWARE
TRIGGERS = {
    # Define os limites (mínimo e máximo) para cada sensor.
    # Se um valor estiver fora destes limites, um alerta é gerado.
    'temperature': {'min': 10.0, 'max': 18.0},
    'humidity':    {'min': 50.0, 'max': 80.0},
    'luminosity':  {'min': -1,   'max': 10}
}
# Variável global para guardar o último comando enviado, evitando spam de comandos repetidos.
estado_alerta_anterior = ""

def convert_to_sao_paulo_time(timestamps_utc_str):
    """
    Converte uma lista de timestamps em formato string (UTC) para objetos datetime
    no fuso horário de São Paulo, para exibição correta no gráfico.
    """
    utc_zone = pytz.utc
    sp_zone = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for ts_str in timestamps_utc_str:
        # Converte a string de data/hora para um objeto datetime ciente do fuso horário
        dt_utc = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        # Converte o objeto para o fuso horário de São Paulo
        dt_sp = dt_utc.astimezone(sp_zone)
        converted_timestamps.append(dt_sp)
    return converted_timestamps

def get_data_from_sth(attribute, params):
    """
    Busca dados históricos de um atributo específico do STH-Comet.
    'attribute': nome do sensor (ex: 'temperature').
    'params': parâmetros da consulta (ex: {'lastN': 10} para os últimos 10 valores).
    """
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/{DEVICE_ID}/attributes/{attribute}"
    headers = {'fiware-service': 'smart', 'fiware-servicepath': '/'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Extrai a lista de valores do JSON de resposta
            return data['contextResponses'][0]['contextElement']['attributes'][0]['values']
        return []
    except (requests.exceptions.RequestException, KeyError, IndexError):
        # Captura erros de rede ou de formato de dados e retorna uma lista vazia
        return []

def enviar_comando_fiware(led_cmd):
    """
    Envia um comando para o dispositivo físico (ESP32) através do Orion Context Broker.
    O Orion reencaminha o comando para o IoT Agent, que o traduz para MQTT.
    """
    global estado_alerta_anterior
    # Verifica se o estado de alerta mudou para evitar enviar comandos repetidos
    if led_cmd != estado_alerta_anterior:
        url_comando = f"http://{IP_ADDRESS}:{PORT_ORION}/v2/entities/{DEVICE_ID}/attrs"
        # O payload (carga útil) define o comando e o seu valor
        payload = {"led": {"type": "command", "value": led_cmd}}
        headers = {'Content-Type': 'application/json', 'fiware-service': 'smart', 'fiware-servicepath': '/'}
        try:
            # Envia a requisição PATCH para atualizar o atributo de comando
            requests.patch(url_comando, headers=headers, data=json.dumps(payload), timeout=5)
            print(f"Comando '{led_cmd}' enviado com sucesso.")
            # Atualiza o estado global para o novo comando enviado
            estado_alerta_anterior = led_cmd
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão ao enviar comando: {e}")

# --- INICIALIZAÇÃO DA APLICAÇÃO DASH ---
# O Dash procura por uma pasta 'assets' no mesmo diretório para carregar ficheiros CSS/JS.
app = dash.Dash(__name__, external_stylesheets=['/assets/custom.css'])
app.title = "Dashboard da Vinheria"

# --- LAYOUT DA PÁGINA WEB ---
# Define a estrutura HTML da página.
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#DDDDDD', 'fontFamily': 'sans-serif'}, children=[
    # Título principal
    html.H1('Dashboard da Vinheria', style={'textAlign': 'center', 'padding': '20px'}),
    
    # Div que irá conter as mensagens de alerta (ex: "Condições ideais." ou os alertas de erro)
    html.Div(id='alert-message', style={'textAlign': 'center', 'fontSize': '20px', 'fontWeight': 'bold', 'padding': '10px'}),
    
    # Componente do gráfico
    dcc.Graph(id='sensor-graph'),
    
    # Componente invisível que dispara a atualização da página a cada 3 segundos
    dcc.Interval(id='interval-component', interval=3*1000, n_intervals=0)
])

# --- LÓGICA DE ATUALIZAÇÃO (CALLBACK) ---
# Este decorador liga a função 'update_dashboard' aos componentes da página.
# 'Input': A função será executada sempre que o 'interval-component' disparar.
# 'Output': O que a função retornar irá atualizar o gráfico e a mensagem de alerta.
@app.callback(
    [Output('sensor-graph', 'figure'),
     Output('alert-message', 'children'),
     Output('alert-message', 'style')],
    Input('interval-component', 'n_intervals')
)
def update_dashboard(n):
    # --- 1. LÓGICA DE VERIFICAÇÃO DE ALERTAS ---
    # Busca o último valor de cada sensor.
    temp_data = get_data_from_sth('temperature', {'lastN': 1})
    hum_data = get_data_from_sth('humidity', {'lastN': 1})
    lum_data = get_data_from_sth('luminosity', {'lastN': 1})

    alert_messages = []
    alert_style = {'textAlign': 'center', 'fontSize': '20px', 'fontWeight': 'bold', 'color': '#4CAF50'} # Estilo padrão (verde)
    comando_prioritario = "desligar" # Comando padrão (sem anomalias)

    if temp_data and hum_data and lum_data:
        temp = float(temp_data[0]['attrValue'])
        umid = float(hum_data[0]['attrValue'])
        lum = int(lum_data[0]['attrValue'])

        # Verifica cada condição independentemente
        if not (TRIGGERS['temperature']['min'] < temp < TRIGGERS['temperature']['max']):
            alert_messages.append(f"ALERTA: Temperatura fora do padrão! ({temp}°C)")
            if comando_prioritario == "desligar": comando_prioritario = "piscar_temp"
        
        if not (TRIGGERS['humidity']['min'] < umid < TRIGGERS['humidity']['max']):
            alert_messages.append(f"ALERTA: Umidade fora do padrão! ({umid}%)")
            # Define o comando apenas se não houver um comando de prioridade maior já definido
            if comando_prioritario == "desligar": comando_prioritario = "piscar_umid"

        if not (TRIGGERS['luminosity']['min'] < lum < TRIGGERS['luminosity']['max']):
            alert_messages.append(f"ALERTA: Luminosidade fora do padrão! ({lum}%)")
            if comando_prioritario == "desligar": comando_prioritario = "piscar_lum"
        
        # Envia o comando de maior prioridade para o hardware
        enviar_comando_fiware(comando_prioritario)

    # --- 2. FORMATAÇÃO DA MENSAGEM DE ALERTA PARA O DASHBOARD ---
    final_alert_children = []
    if alert_messages:
        # Se houver anomalias, constrói uma lista de componentes para exibir com quebras de linha
        for i, msg in enumerate(alert_messages):
            final_alert_children.append(msg)
            if i < len(alert_messages) - 1:
                final_alert_children.append(html.Br()) # Adiciona uma quebra de linha
        alert_style['color'] = '#F44336' # Muda a cor do texto para vermelho
    else:
        final_alert_children = "Condições ideais."

    # --- 3. LÓGICA DE ATUALIZAÇÃO DO GRÁFICO ---
    history_size = 50
    temp_history = get_data_from_sth('temperature', {'lastN': history_size})
    hum_history = get_data_from_sth('humidity', {'lastN': history_size})
    lum_history = get_data_from_sth('luminosity', {'lastN': history_size})
    
    # Função interna para processar os dados históricos
    def prepare_trace_data(history_data):
        if not history_data: return [], []
        # Ordena os dados por tempo para ajudar a reduzir o efeito "teia de aranha"
        sorted_data = sorted(history_data, key=lambda x: x['recvTime'])
        timestamps_utc = [v['recvTime'] for v in sorted_data]
        timestamps_sp = convert_to_sao_paulo_time(timestamps_utc) # Converte para o fuso de SP
        values = [float(v['attrValue']) for v in sorted_data]
        return timestamps_sp, values

    temp_ts, temp_vals = prepare_trace_data(temp_history)
    hum_ts, hum_vals = prepare_trace_data(hum_history)
    lum_ts, lum_vals = prepare_trace_data(lum_history)

    # Cria as linhas (traços) para o gráfico
    traces = [
        go.Scatter(x=temp_ts, y=temp_vals, mode='lines+markers', name='Temperatura (°C)', line={'color': '#FF5733'}),
        go.Scatter(x=hum_ts, y=hum_vals, mode='lines+markers', name='Umidade (%)', line={'color': '#33CFFF'}),
        go.Scatter(x=lum_ts, y=lum_vals, mode='lines+markers', name='Luminosidade (%)', line={'color': '#F1C40F'})
    ]
    
    # Define o layout e a aparência do gráfico
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
    # Retorna todos os elementos que precisam de ser atualizados no dashboard
    return figure, final_alert_children, alert_style

# --- PONTO DE ENTRADA DA APLICAÇÃO ---
# O código dentro deste 'if' só é executado quando o script é chamado diretamente.
if __name__ == '__main__':
    # Inicia o servidor web do Dash na porta 5000
    app.run(debug=True, host=DASH_HOST, port=5000)

