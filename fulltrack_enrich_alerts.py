import requests
import json
import datetime
import time
import os

# --- Configurações da API ---
# Em um ambiente serverless, é melhor usar variáveis de ambiente
# para as chaves de API por questões de segurança.
# Se as variáveis de ambiente não estiverem definidas, ele usará as chaves padrão.
API_KEY = os.environ.get("FULLTRACK_API_KEY", "84c8dfe7fd5045dad5816baeb9809608e70a38c7")
SECRET_KEY = os.environ.get("FULLTRACK_SECRET_KEY", "4f17a2fd1646d0c42324c2248d6aaca5896b0246")
BASE_URL = "https://ws.fulltrack2.com"

HEADERS = {
    "Content-Type": "application/json",
    "ApiKey": API_KEY,
    "SecretKey": SECRET_KEY,
    "User-Agent": "Serverless Function (WhatsApp Alert)"
}

# --- Funções Auxiliares ---

def get_yesterday_period():
    """Calcula o Unixtime para o período de 00:00:00 a 23:59:59 do dia anterior."""
    # Nota: Em ambientes serverless, o fuso horário pode ser UTC.
    # Para garantir que o "dia anterior" seja o dia anterior no Brasil,
    # pode ser necessário ajustar o fuso horário. Para simplicidade,
    # vamos usar o fuso horário padrão do ambiente (geralmente UTC).
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)
    
    start_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.min)
    end_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.max)
    
    # Converte para Unixtime (timestamp)
    unixtime_start = int(time.mktime(start_of_yesterday.timetuple()))
    unixtime_end = int(time.mktime(end_of_yesterday.timetuple()))
    
    return unixtime_start, unixtime_end, yesterday.strftime("%d/%m/%Y")

def get_alert_data(unixtime_start, unixtime_end):
    """Busca os alertas do período especificado."""
    url = f"{BASE_URL}/alerts/period/initial/{unixtime_start}/final/{unixtime_end}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": False, "message": f"Erro ao buscar alertas: {e}"}

def get_driver_name(vehicle_id, cache):
    """Busca o nome do motorista para um veículo, usando cache."""
    if vehicle_id in cache:
        return cache[vehicle_id]

    url = f"{BASE_URL}/events/single/id/{vehicle_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # O nome do motorista está no primeiro (e único) item do array 'data'
        driver_name = data.get("data", [{}])[0].get("ras_mot_nome", "Motorista Não Identificado")
        
        cache[vehicle_id] = driver_name
        return driver_name
        
    except requests.exceptions.RequestException:
        return "Motorista Não Identificado (Erro API)"

def format_whatsapp_message(alert, driver_name):
    """Formata um alerta em uma mensagem detalhada para o WhatsApp."""
    
    # Extrai os dados relevantes
    placa = alert.get("ras_vei_placa", "N/D")
    data_alerta = alert.get("ras_eal_data_alerta", "N/D")
    descricao = alert.get("ras_eal_descricao_extra", alert.get("ras_eal_descricao", "Alerta Desconhecido"))
    latitude = alert.get("ras_eal_latitude", "N/D")
    longitude = alert.get("ras_eal_longitude", "N/D")
    
    # Cria o link do Google Maps
    map_link = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    
    message = (
        f"🚨 *ALERTA DE IGNIÇÃO FORA DE HORA* 🚨\n\n"
        f"🚗 *Veículo:* {placa}\n"
        f"👤 *Motorista:* {driver_name}\n"
        f"⚠️ *Alerta:* {descricao}\n"
        f"⏰ *Data/Hora:* {data_alerta}\n"
        f"📍 *Localização:* {map_link}\n"
        f"----------------------------------------"
    )
    return message

# --- Função Serverless Principal ---

def handler(event, context):
    """
    Ponto de entrada da função serverless.
    Busca alertas, filtra e retorna o relatório formatado.
    """
    
    unixtime_start, unixtime_end, date_str = get_yesterday_period()
    
    # 1. Buscar todos os alertas do dia anterior
    alerts_response = get_alert_data(unixtime_start, unixtime_end)
    
    if not alerts_response.get("status"):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": alerts_response.get('message')})
        }

    all_alerts = alerts_response.get("data", [])
    
    if not all_alerts:
        return {
            "statusCode": 200,
            "body": json.dumps({"report": f"✅ Nenhum alerta encontrado para o dia {date_str}."})
        }

    # 2. Filtrar e processar
    filtered_alerts = []
    driver_cache = {}
    
    for alert in all_alerts:
        # Filtro: "IGNIÇÃO LIGADA APÓS AS 20H"
        if "IGNIÇÃO LIGADA APÓS AS 20H" in alert.get("ras_eal_descricao_extra", ""):
            
            # 3. Enriquecer com o nome do motorista
            vehicle_id = alert.get("ras_eal_id_veiculo")
            driver_name = get_driver_name(vehicle_id, driver_cache)
            
            # 4. Formatar a mensagem
            message = format_whatsapp_message(alert, driver_name)
            filtered_alerts.append(message)

    # 5. Montar o relatório final
    if not filtered_alerts:
        final_report = f"✅ Nenhum alerta de 'IGNIÇÃO LIGADA APÓS AS 20H' encontrado para o dia {date_str}."
    else:
        header = f"🔔 *RELATÓRIO DE ALERTA DIÁRIO* 🔔\nPeríodo: {date_str}\n\n"
        final_report = header + "\n\n".join(filtered_alerts)
    
    # 6. Retornar a resposta HTTP
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"report": final_report})
    }

# Para Netlify Functions, o arquivo deve ser nomeado como [nome_da_funcao].py
# e o handler deve ser o ponto de entrada.
# O nome do arquivo deve ser "whatsapp_report_function.py" e o handler é a função "handler".
# Para testes locais, você pode chamar a função handler diretamente.
if __name__ == "__main__":
    print("--- Teste Local da Função Serverless ---")
    result = handler(None, None)
    print(json.dumps(result, indent=4, ensure_ascii=False))
