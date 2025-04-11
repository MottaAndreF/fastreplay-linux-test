# createConfigCamera.py

import json
import requests
from datetime import datetime
 
def criar_configuracao_cameras(arquivo_json="config_cameras.json"):
    cameras = [
        {
            "cliente": "Academia XYZ",
            "nome": "QuadraTenis1",
            "quadra": "Quadra de Tênis",
            "ip": "201.50.200.85",
            "porta": 554,
            "usuario": "admin",
            "senha": "Primos2025",
            "logos": ["Logo-clube-campestre.png"],
            "data_adicao": datetime.now().strftime("%d-%m-%Y")
        },
        {
            "cliente": "Academia XYZ",
            "nome": "QuadraFutebol1",
            "quadra": "Quadra de Futebol",
            "ip": "201.50.200.85",
            "porta": 554,
            "usuario": "admin",
            "senha": "Primos2025",
            "logos": ["Logo-clube-campestre.png"],
            "data_adicao": datetime.now().strftime("%d-%m-%Y")
        }
    ]

    for camera in cameras:
        camera["pasta_destino"] = f"videos/{camera['cliente']}/{camera['nome']}/{camera['ip']}"

    config = {"cameras": cameras}
    
    with open(arquivo_json, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f"✅ Arquivo de configuração '{arquivo_json}' criado com sucesso!")

    try:
        with open(arquivo_json, "rb") as f:
            primeira_camera = cameras[0]
            response = requests.post(
                'http://34.58.6.78:8000/upload',
                files={"file": (arquivo_json, f, "application/json")},
                data={
                    "cliente": primeira_camera["cliente"],
                    "quadra": primeira_camera["quadra"],
                    "cameraIP": primeira_camera["ip"],
                    "dia": datetime.now().strftime("%Y-%m-%d"),
                    "horario": datetime.now().strftime("%H:%M")
                }
            )
        if response.status_code == 200:
            return {"status": "sucesso", "mensagem": "Configuração enviada com sucesso!"}
        else:
            return {"status": "erro", "codigo": response.status_code, "resposta": response.text}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}