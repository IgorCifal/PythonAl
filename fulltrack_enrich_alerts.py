import requests
import json
import datetime
import time
import sys
import os # NOVO: Importa o módulo OS para ler variáveis de ambiente

# --- Configurações da API ---
# ATUALIZADO: As chaves são lidas das Variáveis de Ambiente do Netlify.
API_KEY = os.environ.get("FULLTRACK_API_KEY") 
SECRET_KEY = os.environ.get("FULLTRACK_SECRET_KEY")
BASE_URL = "https://ws.fulltrack2.com"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

HEADERS = {
    "Content-Type": "application/json",
    "ApiKey": API_KEY, # Usa a chave lida do ambiente
    "SecretKey": SECRET_KEY, # Usa a chave lida do ambiente
    "User-Agent": "Automation Script (WhatsApp Alert)"
}

# --- Funções Auxiliares ---

def get_yesterday_period():
    """Calcula o Unixtime para o período de 00:00:00 a 23:59:59 do dia anterior."""
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
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao buscar alertas: {e}")
        return {"status": False, "message": str(e)}
    except requests.exceptions.RequestException as e:
        print(f"Erro de Conexão ao buscar alertas: {e}")
        return {"status": False, "message": str(e)}

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
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar motorista para Veículo {vehicle_id}: {e}")
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

# --- Função Principal ---

def run_automation():
    """Executa o fluxo completo de busca, filtro e formatação."""
    
    unixtime_start, unixtime_end, date_str = get_yesterday_period()
    
    print(f"Iniciando busca de alertas para o dia: {date_str}")
    
    # 1. Buscar todos os alertas do dia anterior
    alerts_response = get_alert_data(unixtime_start, unixtime_end)
    
    if not alerts_response.get("status"):
        return [f"❌ ERRO: Falha ao buscar alertas. {alerts_response.get('message')}"]

    all_alerts = alerts_response.get("data", [])
    
    if not all_alerts:
        return [f"✅ Nenhum alerta encontrado para o dia {date_str}."]

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

    if not filtered_alerts:
        return [f"✅ Nenhum alerta de 'IGNIÇÃO LIGADA APÓS AS 20H' encontrado para o dia {date_str}."]

    # 5. Retornar o resultado final
    header = f"🔔 *RELATÓRIO DE ALERTA DIÁRIO* 🔔\nPeríodo: {date_str}\n\n"
    
    # Junta todas as mensagens em uma única string grande, separadas por duas quebras de linha
    final_report = header + "\n\n".join(filtered_alerts)
    
    # REMOVIDO: Linhas que salvam o arquivo localmente, pois não são necessárias no Netlify.
        
    return [final_report]

# REMOVIDO: O bloco if __name__ == "__main__": não é necessário para o Netlify Functions.