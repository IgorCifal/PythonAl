# alerta.py

import json
import os
import sys

# Adicione o caminho do projeto para importar as funções
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# IMPORTAÇÃO DO SEU SCRIPT ORIGINAL
# Supondo que seu script original tenha uma função principal chamada run_automation()
from fulltrack_enrich_alerts import run_automation

def handler(event, context):
    """
    Função principal que o Netlify Functions irá executar.
    """
    try:
        # AQUI VOCÊ CHAMA SUA FUNÇÃO PRINCIPAL
        # NOTA: O 'run_automation' retorna o relatório como uma lista.
        report_list = run_automation()
        final_report_text = report_list[0]

        # Retorna a resposta no formato JSON esperado pelo HTTP
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                "status": "success",
                "message": "Relatório gerado com sucesso.",
                "data": final_report_text
            })
        }
    except Exception as e:
        # Em caso de erro
        return {
            'statusCode': 500,
            'body': json.dumps({
                "status": "error",
                "message": f"Ocorreu um erro na execução: {e}"
            })
        }