import json
import os
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta
import re

def carregar_configuracao_camera(index=0, caminho_config="config_cameras.json"):
    with open(caminho_config, "r", encoding="utf-8") as f:
        return json.load(f)["cameras"][index]

def ler_eventos_txt(ip, nome, cliente, pasta=""):
    nome_formatado = nome.replace(" ", "_")
    cliente_formatado = cliente.replace(" ", "_")
    nome_arquivo = f"videos_{ip}_{nome_formatado}_{cliente_formatado}.txt"
    caminho = os.path.join(pasta, nome_arquivo)

    eventos = []
    if not os.path.exists(caminho):
        print(f"⚠️ Arquivo de eventos não encontrado: {caminho}")
        return eventos

    try:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except UnicodeDecodeError:
            with open(caminho, "r", encoding="latin-1") as f:
                linhas = f.readlines()

        for linha in linhas:
            if "Alarm Input" in linha:
                match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", linha)
                if match:
                    eventos.append(match.group())

    except Exception as e:
        print(f"❌ Erro ao ler o arquivo de eventos: {e}")

    return eventos

def buscar_videos_com_eventos(camera):
    ip_publico = camera["ip"]
    ip_camera_interno = camera["ip"]
    porta = camera.get("porta", 8000)
    usuario = camera["usuario"]
    senha = camera["senha"]
    nome = camera["nome"]
    cliente = camera["cliente"]

    # Período automático
    agora_utc = datetime.utcnow()
    ontem_utc = agora_utc - timedelta(days=1)

    inicio = ontem_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    fim = agora_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    eventos_txt = ler_eventos_txt(ip_publico, nome, cliente)

    url = f"http://{ip_publico}:{porta}/ISAPI/ContentMgmt/search"

    xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchDescription>
        <searchID>1</searchID>
        <trackList><trackID>101</trackID></trackList>
        <timeSpanList>
            <timeSpan>
                <startTime>{inicio}</startTime>
                <endTime>{fim}</endTime>
            </timeSpan>
        </timeSpanList>
        <maxResults>100</maxResults>
        <searchResultPostion>0</searchResultPostion>
        <metadataList>
            <metadataDescriptor>/recordType.meta.std-cgi.com</metadataDescriptor>
        </metadataList>
    </CMSearchDescription>"""

    headers = {"Content-Type": "application/xml"}

    try:
        response = requests.post(
            url,
            data=xml_payload,
            headers=headers,
            auth=HTTPDigestAuth(usuario, senha),
            timeout=10
        )

        if response.status_code != 200:
            print(f"❌ Erro ao buscar vídeos: {response.status_code}")
            return

        xml = response.text
        items = xml.split("<searchMatchItem>")[1:]

        videos = []
        for item in items:
            start_str = item.split("<startTime>")[1].split("</startTime>")[0]
            end_str = item.split("<endTime>")[1].split("</endTime>")[0]
            uri = item.split("<playbackURI>")[1].split("</playbackURI>")[0]

            start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ")
            end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ")

            rtsp_url = uri.replace(ip_camera_interno, f"{usuario}:{senha}@{ip_publico}:554")

            nome_video = "video_" + start_str.replace("T", "_").replace("Z", "") + ".mp4"

            videos.append({
                "start": start_dt,
                "end": end_dt,
                "nome": nome_video,
                "url": rtsp_url,
                "start_str": start_str,
                "end_str": end_str
            })

        print(f"\n🔔 Eventos de botão encontrados ({len(eventos_txt)}):")
        resultados = []
        for evento_str in eventos_txt:
            evento_local = datetime.strptime(evento_str, "%Y-%m-%d %H:%M:%S")
            evento_utc = evento_local + timedelta(hours=3)

            print(f"📍 {evento_str}")
            evento_info = {
                "evento": evento_str,
                "video": None
            }

            for v in videos:
                if v["start"] <= evento_utc <= v["end"]:
                    print("Video para download:")
                    print(f"📁 {v['nome']}")
                    print(f"⏱️ {v['start_str']} até {v['end_str']}")
                    print(f"🔗 {v['url']}")
                    print("------------------------------------------------------------")
                    evento_info["video"] = {
                        "nome": v["nome"],
                        "inicio": v["start_str"],
                        "fim": v["end_str"],
                        "url": v["url"]
                    }
                    break

            if not evento_info["video"]:
                print("⚠️ Nenhum vídeo correspondente encontrado para este evento.")
                print("------------------------------------------------------------")

            resultados.append(evento_info)

        # 🔽 Salvar em JSON
        nome_formatado = nome.replace(" ", "_")
        cliente_formatado = cliente.replace(" ", "_")
        nome_arquivo = f"list_videos_download_{ip_publico}_{nome_formatado}_{cliente_formatado}.json"
        download_dir = os.path.abspath("")
        caminho_novo = os.path.join(download_dir, nome_arquivo)

        os.makedirs(download_dir, exist_ok=True)
        if os.path.exists(caminho_novo):
            os.remove(caminho_novo)

        with open(caminho_novo, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4)

        print(f"\n✅ Lista de vídeos relacionada aos eventos salva em: {caminho_novo}")

    except Exception as e:
        print(f"❌ Erro: {e}")