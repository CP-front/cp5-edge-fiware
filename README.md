# 💡 Projeto de Monitoramento para Vinheria com FIWARE e IoT
Este projeto implementa um sistema de monitoramento em tempo real para as condições ambientais de uma vinheria (temperatura, umidade e luminosidade). Os dados são coletados por um ESP32, enviados para a plataforma FIWARE e visualizados num dashboard web. O sistema também inclui alertas ativos (LED e buzzer) que são acionados quando as condições saem dos padrões ideais.

---

# 🍷 Contexto do Projeto
A maturação e conservação de vinhos são processos delicados que dependem de um controlo ambiental rigoroso. Variações em temperatura, umidade e exposição à luz podem degradar irreversivelmente a qualidade do produto, resultando em perdas significativas. Sistemas de monitoramento passivos apenas registam os dados, mas não agem quando ocorrem anomalias.

Este projeto aborda essa lacuna, criando um sistema de vigilância ativo que não só monitoriza os parâmetros em tempo real, mas também toma decisões e aciona alertas físicos imediatos quando as condições saem dos limites ideais.

---

# 📌 Descrição da Solução
A solução implementada é um sistema IoT completo que integra hardware, uma plataforma de backend robusta e uma interface de utilizador web.
- Um dispositivo ESP32 com sensores lê continuamente os dados do ambiente.

- Os dados são enviados via MQTT para uma plataforma FIWARE a correr em Docker numa Máquina Virtual (VM).

- A plataforma processa, armazena o histórico e gere o estado atual do ambiente.

- Um Dashboard Web desenvolvido em Python (Dash) visualiza os dados históricos e em tempo real, aplica a lógica de negócio (regras de alerta) e envia comandos de volta para o dispositivo.

- O dispositivo físico reage aos comandos, acionando alertas visuais (LED) e sonoros (buzzer) com padrões distintos para cada tipo de anomalia.

---

# ⚙️ Funcionalidades Principais
- Monitoramento em Tempo Real: Visualização contínua de temperatura, umidade e luminosidade.

- Gráfico Histórico: Análise do histórico de dados para identificar tendências e eventos passados.

- Alertas Ativos e Remotos: O sistema deteta automaticamente quando os valores saem dos limites pré-definidos e envia um comando para o hardware.

- Alertas Diferenciados: O LED pisca em velocidades diferentes e o buzzer toca sons distintos, permitindo a identificação da natureza da anomalia (Temperatura, Umidade ou Luminosidade) remotamente.

- Exibição de Múltiplas Anomalias: O dashboard é capaz de exibir todos os alertas ativos em simultâneo.

- Prioridade de Alerta Físico: O alerta físico (LED/Buzzer) reflete a anomalia de maior prioridade (Temperatura > Umidade > Luminosidade).

- Serviço Robusto 24/7: O backend e o dashboard são executados como serviços `systemd` no Linux, garantindo que o sistema esteja sempre online e se recupere automaticamente de falhas.

---

# 🏗️ Arquitetura em Camadas
A solução foi projetada em três camadas distintas, cada uma com sua responsabilidade.

## 1. Camada IoT (Dispositivo Físico)
- Responsabilidade: Coletar dados brutos do ambiente e atuar fisicamente com base nos comandos recebidos.

- Componentes: ESP32, Sensores (DHT11, LDR), Atuadores (LED, Buzzer).

- Operação: O firmware lê os sensores a cada 5 segundos, publica os dados via MQTT e fica à escuta por comandos.

## 2. Camada de Backend (Plataforma FIWARE)
- Responsabilidade: Ingestão de dados, gestão de contexto (estado atual), armazenamento de histórico e roteamento de comandos.

- Componentes:

    - Mosquitto: Broker MQTT que recebe os dados do ESP32.

    - IoT Agent for MQTT: Traduz as mensagens MQTT para o protocolo NGSI-v2 do FIWARE e vice-versa.

    - Orion Context Broker: O cérebro da plataforma. Mantém o estado atual de todos os dispositivos ("contexto").

    - STH-Comet: Subscreve o Orion e armazena cada alteração de dados numa base de dados MongoDB para criar o histórico.

- Operação: Corre em Docker numa VM, garantindo portabilidade e isolamento.

## 3. Camada de Aplicação (Dashboard e Lógica)
- Responsabilidade: Apresentar os dados ao utilizador, aplicar as regras de negócio (triggers) e iniciar o fluxo de comandos de alerta.

- Componentes: Aplicação Python com a biblioteca Dash.

- Operação: A cada 3 segundos, a aplicação:

    - Consulta o STH-Comet para obter os dados históricos e desenhar o gráfico.

    - Consulta o Orion Context Broker para obter o último valor de cada sensor.

    - Compara os valores com os `TRIGGERS` definidos.

    - Se uma anomalia for detetada, envia um comando de volta para o Orion Context Broker.

### O fluxo de dados segue o seguinte caminho:
```bash
ESP32 com Sensores -> MQTT Broker -> FIWARE IoT Agent -> Orion Context Broker -> STH Comet (Histórico) & Dashboard Web (Visualização/Comandos)
```

---

# 📂 Estrutura do Projeto
A estrutura de ficheiros do repositório está organizada da seguinte forma:
```bash
/
├── Sketch/
│   ├── libraries.txt           # Bibliotecas Necessárias
│   └── sketch.ino              # Código a ser carregado no ESP32
│
├── VM/
│   ├── .idea/
│   ├── dashboard/
│   │   ├── assets/
│   │   │   └── custom.css      # Ficheiro de estilo para o dashboard
│   │   └── api-sth.py          # O código da aplicação do dashboard
│   │
│   ├── mosquitto/              # Configuração do mosquitto               
│   │
│   ├── venv/                   # Ambiente virtual Python (criado localmente, ignorado pelo Git)
│   ├── docker-compose.yml      # Ficheiro de orquestração dos serviços FIWARE
│   └── requirements.txt        # Lista de dependências Python do dashboard
│
├── Fiware-CollectionCP5.postman_collection.json # Coleção do Postman para configuração
└── README.md                   # Esta documentação
```

---

# 🛠️ Manual de Instalação e Execução
Este guia assume que está a ser executado num servidor **Ubuntu Server 24.04.3 LTS**.

## 1. Recursos e Materiais
Hardware
- Microcontrolador ESP32

- Sensor de Temperatura e Umidade DHT11 (ou DHT22)

- Sensor de Luminosidade LDR

- Buzzer Ativo 5V

- LED Azul 5mm

- Resistor de 220Ω (para o LED)

- Breadboard e Jumpers

Software
- Git, Docker, Docker Compose, Python 3.10+, Venv

- Arduino IDE

- Postman

## 2. Montagem do Hardware
Conecte os componentes ao ESP32 de acordo com o seguinte esquema de pinos:
| Componente          | Pino do Componente | Pino no ESP32 |
|---------------------|------------        |---------------|
| DHT22               | VCC / +            | 3V3           |
| DHT22               | GND / -            | GND           |
| DHT22               | DADOS              | GPIO 15       |
| LDR                 | VCC                | 3V3           |
| LDR                 | GND                | GND           |
| LDR                 | DADOS              | GPIO 34       |
| Buzzer              | Positivo (+)       | GPIO 4        |
| Buzzer              | Negativo (-)       | GND           |

## 3. Configuração do Servidor e Backend
1. ### Instale as Dependências do Servidor:

    ```bash
    sudo apt update
    sudo apt install docker.io
    sudo apt install docker-compose
    sudo apt install python3 python3-pip
    ```

2. ### Clone o Repositório:

    ```bash
    git clone https://github.com/CP-front/cp5-edge-fiware
    cd cp5-edge-fiware
    ```

3. ### Inicie a Plataforma FIWARE:

    ```bash
    cd VM
    sudo docker-compose up -d
    ```

4. ### Configure os Serviços com o Postman:
    - Importe o ficheiro `Fiware-CollectionCP5.postman_collection.json` para o Postman.

    - Configure a variável de ambiente `{{url}}` com o endereço IP do seu servidor.

    - Execute as seguintes requisições nesta ordem exata:

        1. Da pasta `IOT Agent MQTT` -> `2. Provisioning a Service Group for MQTT`

        2. Da pasta `IOT Agent MQTT` -> `3. Provisioning a Smart Lamp`

        3. Da pasta `STH-Comet` -> `2. Subscribe Attributes`

## 4. Configuração do Hardware (ESP32)
1. Abra o Ficheiro: Abra o ficheiro `Sketch/sketch.ino` na Arduino IDE ou use a simulação no [Wokwi](https://wokwi.com/projects/443483204612469761).

2. Instale as Bibliotecas: No gestor de bibliotecas, instale `PubSubClient`, `ArduinoJson` e `DHTesp`.

3. Configure o Wi-Fi: Altere as constantes `SSID` e `PASSWORD` com as credenciais da sua rede Wi-Fi.

4. Carregue o Código: Conecte o ESP32 ao seu computador e carregue o sketch.

## 5. Configuração do Dashboard
1. ### Crie o Ambiente Virtual e Instale as Dependências:

    ```bash
    # Navegue para a pasta VM
    cd /home/NOME_DO_USUARIO/cp5-edge-fiware/VM

    # Crie o ambiente virtual (sem sudo)
    python3 -m venv venv

    # Ative o ambiente virtual
    source venv/bin/activate

    # Instale as bibliotecas (sem sudo)
    venv/bin/python3 -m pip install -r requirements.txt
    ```

2. ### Crie o Serviço do Linux (`systemd`):
    - Crie o ficheiro de serviço: `sudo nano /etc/systemd/system/dash.service`

    - Copie e cole o conteúdo abaixo, substituindo `NOME_DO_USUARIO` pelo seu nome de utilizador real.

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
    
    - Salve e saia (Ctrl + X, Y, Enter).

3. ### Inicie o Serviço:

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

4. ### Encerrar o Serviço e a Plataforma FIWARE(ao terminar):

    ```bash
    # Encerrar o serviço imediatamente
    sudo systemctl stop dash.service

    # Remover os contêineres
    sudo docker-compose down
    ```


## 6. Operação do Sistema
- Aceder ao Dashboard: Abra um navegador e vá para `http://<IP_DO_SEU_SERVIDOR>:5000`.

- Interpretar os Alertas:

    - Mensagem no Ecrã: O dashboard exibirá em vermelho quais os parâmetros que estão fora dos limites.

    - Alerta Físico (LED/Buzzer):

        - Temperatura: Pisca rápido, som agudo.

        - Umidade: Pisca médio, som médio.

        - Luminosidade: Pisca lento, som grave.

---

# ⚠️ Notas de Segurança
- Acesso ao Dashboard: A porta 5000 do seu servidor deve estar acessível. Configure as regras de firewall da sua VM para permitir o tráfego nesta porta.

- Autenticação no Git: Este projeto usa autenticação via HTTPS com Personal Access Tokens (PATs) para interagir com o GitHub. Certifique-se de que os seus tokens têm a scope `repo` selecionada.

- Segurança MQTT: A configuração atual do broker Mosquitto é aberta para facilitar o desenvolvimento. Num ambiente de produção, seria essencial configurar autenticação com nome de utilizador/palavra-passe e encriptação TLS para proteger a comunicação.

---

## ⌨ Simulação no Wokwi

- [Clique aqui para abrir](https://wokwi.com/projects/443483204612469761)

---

## 👨‍💻 Autores

- Projeto desenvolvido por **Visionary Solutions** para a disciplina Edge Computing - FIAP.
- Equipe: Arthur Araujo Tenorio; Breno Gonçalves Báo; Rodrigo Cardoso Tadeo; Vinicius Cavalcanti dos Reis
- Professor: Dr. Fábio H. Cabrini

---

## 📢 Licença

Este projeto é livre para uso educacional. Para uso comercial, consulte os autores.





