# alerta.py

import json
import os
import sys

# O Netlify Functions é baseado no AWS Lambda. 
# Para importar o 'fulltrack_enrich_alerts.py' (que está na pasta acima, na raiz),
# precisamos adicionar o diretório pai ao PATH do sistema.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa a função principal do seu script. 
# Certifique-se de que a função 'run_automation' existe em fulltrack_enrich_alerts.py.
from fulltrack_enrich_alerts import run_automation

def handler(event, context):
    """
    Função principal (handler) que o Netlify Functions irá executar.
    
    Recebe um evento HTTP (event) e o contexto de execução (context)
    e retorna uma resposta formatada para o API Gateway.
    """
    
    # Executa a lógica do seu script original
    try:
        # A função run_automation retorna uma lista com o relatório
        report_list = run_automation()
        final_report_text = report_list[0]
        
        # Retorna a resposta no formato HTTP/JSON esperado
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "status": "success",
                "message": "Relatório diário de alertas gerado com sucesso.",
                "report": final_report_text
            })
        }
        
    except Exception as e:
        # Em caso de erro, retorna um status 500 (Erro Interno do Servidor)
        print(f"Erro inesperado: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "status": "error",
                "message": f"Ocorreu um erro na execução do script: {str(e)}"
            })
        }