# 💡 Projeto de Monitoramento para Vinheria com FIWARE, MQTT e ESP32
Este projeto implementa um sistema de monitoramento em tempo real para as condições ambientais de uma vinheria (temperatura, umidade e luminosidade). Os dados são coletados por um ESP32, enviados para a plataforma FIWARE e visualizados num dashboard web. O sistema também inclui alertas ativos (LED e buzzer) que são acionados quando as condições saem dos padrões ideais.

# Arquitetura 
O fluxo de dados segue o seguinte caminho:

ESP32 com Sensores -> MQTT Broker -> FIWARE IoT Agent -> Orion Context Broker -> STH Comet (Histórico) & Dashboard Web (Visualização/Comandos)

# Pré-requisitos
Para replicar este ambiente num novo servidor (Ubuntu 22.04+ recomendado), é necessário ter o seguinte software instalado:

-Git

-Docker

-Docker Compose

-Python 3 e Venv

```bash
sudo apt update

sudo apt install docker.io

sudo apt install docker-compose

sudo apt install python3 python3-pip
```

# Guia de Instalação Passo a Passo
Siga estes passos na ordem para configurar todo o ambiente.

## 1. Clonar o Repositório
Clone este repositório para o seu servidor:

```bash
git clone [https://github.com/CP-front/cp5-edge-fiware](https://github.com/CP-front/cp5-edge-fiware)
cd cp5-edge-fiware
```

# 2. Iniciar a Plataforma FIWARE
Todos os componentes do backend (Orion, IoT Agent, Mosquitto, Comet) estão definidos no ficheiro `docker-compose.yml`.

```bash
# Navegue para a pasta VM
cd VM

# Suba os containers em background
sudo docker-compose up -d
```

# 3. Configurar os Serviços FIWARE com Postman
A plataforma precisa de ser configurada para entender o nosso dispositivo.

1. Importe a Collection: Importe o ficheiro Fiware-Collection.postman_collection.json para a sua aplicação Postman.

2. Configure a Variável de Ambiente: No Postman, crie ou edite uma variável de ambiente {{url}} para o endereço IP do seu servidor.

3. Execute as Requisições (Nesta Ordem):
    -Na pasta IOT Agent MQTT -> 2. Provisioning a Service Group for MQTT (cria o serviço).

    -Na pasta IOT Agent MQTT -> 3. Provisioning a Smart Lamp (regista o nosso ESP32).

    -Na pasta STH-Comet -> 2. Subscribe Attributes (diz ao Orion para guardar o histórico de dados).

# 4. Montar e Programar o Hardware (ESP32)
1. Circuito: Monte o circuito conectando os sensores e atuadores ao ESP32 ou use a simulação no [Wokwi](https://wokwi.com/projects/443483204612469761):
    -DHT22 (Dados): GPIO 15

    -LDR/Potenciômetro (Dados): GPIO 34

    -LED Azul (Saída): GPIO 2

    -Buzzer (Saída): GPIO 4

2. Arduino IDE:
    -Abra o ficheiro .ino do projeto na Arduino IDE.

    -Instale as bibliotecas necessárias: PubSubClient, DHTesp, ArduinoJson.

    -Altere as constantes SSID e PASSWORD com as credenciais da sua rede Wi-Fi.

    -Carregue (upload) o código para a sua placa ESP32.

# 5. Configurar e Iniciar o Dashboard
O dashboard é uma aplicação Python que precisa de ser configurada como um serviço para rodar continuamente.

## a) Instalar as Dependências
```bash
# Navegue para a pasta VM
cd /home/NOME_DO_USUARIO/cp5-edge-fiware/VM

# Crie o ambiente virtual
python3 -m venv venv

# Ative o ambiente virtual
source venv/bin/activate
# (Não é necessário ativar para o próximo passo)

# Instale as bibliotecas a partir do requirements.txt
./venv/bin/pip install -r requirements.txt
```

## b) Configurar o Serviço (`systemd`)
1. Crie o ficheiro de serviço com um editor de texto:
```bash
sudo nano /etc/systemd/system/dash.service
```

2. Copie e cole o seguinte conteúdo no ficheiro. Lembre-se de substituir `NOME_DO_USUARIO` pelo seu nome de utilizador real no servidor.
```bash
[Unit]
Description=FIWARE Dashboard Service
After=network.target

[Service]
User=NOME_DO_USUARIO
WorkingDirectory=/home/NOME_DO_USUARIO/cp5-edge-fiware/VM/dashboard
ExecStart=/home/NOME_DO_USUARIO/cp5-edge-fiware/VM/venv/bin/python3 /home/NOME_DO_USUARIO/cp5-edge-fiware/VM/dashboard/api-sth.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Salve o ficheiro e saia (`Ctrl + X`, `Y`, `Enter`).
## c) Iniciar o Serviço do Dashboard
```bash
# Recarregue o systemd para que ele leia o novo ficheiro
sudo systemctl daemon-reload

# Habilite o serviço para iniciar com o sistema
sudo systemctl enable dash.service

# Inicie o serviço imediatamente
sudo systemctl start dash.service

# Verifique se está a funcionar
sudo systemctl status dash.service
```

# 6. Aceder ao Dashboard
Abra o seu navegador e aceda ao seguinte endereço:
```bash
http://<IP_DO_SEU_SERVIDOR>:8050
```
O dashboard deverá carregar e começar a exibir os dados dos sensores em tempo real.