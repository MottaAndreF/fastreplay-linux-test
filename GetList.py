import os
import json
import requests
import urllib3
import re
from urllib.parse import unquote
import subprocess
from datetime import datetime, timedelta

urllib3.disable_warnings()

def carregar_dados_camera(nome_camera):
    with open("config_cameras.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    camera = next((c for c in config["cameras"] if c["nome"] == nome_camera), None)
    if not camera:
        raise Exception(f"❌ Câmera '{nome_camera}' não encontrada no config_cameras.json")

    ip = camera["ip"]
    porta_http = 8080
    porta_digest = 8000
    usuario = camera["usuario"]
    senha = camera["senha"]
    cliente = camera["cliente"]

    sessao_path = f"sessao_camera_{ip}_{nome_camera.replace(' ', '_')}_{cliente.replace(' ', '_')}_.json"
    if not os.path.exists(sessao_path):
        raise Exception(f"❌ Sessão não encontrada: {sessao_path}")

    with open(sessao_path, "r") as f:
        sessao = json.load(f)

    return camera, sessao


def carregar_configuracao_camera(index=0, caminho_config="config_cameras.json"):
    with open(caminho_config, "r", encoding="utf-8") as f:
        return json.load(f)["cameras"][index]

def extrair_nome_video_da_url(rtsp_url):
    match = re.search(r"name=([^&]+)", rtsp_url)
    if match:
        return match.group(1) + ".mp4"
    return "video_desconhecido.mp4"

def carregar_dados(ip, nome, cliente):
    nome_formatado = nome.replace(" ", "_")
    cliente_formatado = cliente.replace(" ", "_")

    json_videos = f"list_videos_download_{ip}_{nome_formatado}_{cliente_formatado}.json"
    json_sessao = f"sessao_camera_{ip}_{nome_formatado}_{cliente_formatado}_.json"

    if not os.path.exists(json_videos) or not os.path.exists(json_sessao):
        raise FileNotFoundError("⚠️ Arquivo de sessão ou lista de vídeos não encontrado.")

    with open(json_videos, "r", encoding="utf-8") as f:
        lista = json.load(f)

    with open(json_sessao, "r", encoding="utf-8") as f:
        sessao = json.load(f)

    return lista, sessao

def obter_token(ip, porta, session_tag, cookie_session):
    print("🔐 Solicitando token...")
    headers = {
        "SessionTag": session_tag,
        "Cookie": cookie_session,
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest"
    }

    r = requests.get(
        f"http://{ip}:{porta}/ISAPI/Security/token?format=json",
        headers=headers,
        verify=False
    )

    if r.status_code != 200:
        print(f"❌ Falha ao obter token. Código: {r.status_code}")
        print(r.text)
        return None

    token = r.json()["Token"]["value"]
    print(f"✅ Token obtido: {token}")
    return token

def baixar_video(ip, porta, session_tag, cookie_session, token, url_rtsp, nome_arquivo):
    print(f"\n⬇️ Iniciando download: {nome_arquivo}")

    url_rtsp_escaped = unquote(url_rtsp).replace("&", "&amp;")

    xml_payload = f'''<?xml version="1.0" encoding="UTF-8"?>
    <CMDownloadRequest xmlns="http://www.hikvision.com/ver20/XMLSchema">
      <playbackURI>{url_rtsp_escaped}</playbackURI>
    </CMDownloadRequest>'''

    headers = {
        "Content-Type": "application/xml; charset=UTF-8",
        "SessionTag": session_tag,
        "Cookie": cookie_session,
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }

    caminho_saida = os.path.abspath(nome_arquivo)

    if os.path.exists(caminho_saida):
        print(f"🟡 Já existe, ignorando download: {nome_arquivo}")
        return True

    try:
        with requests.post(
            f"http://{ip}:{porta}/ISAPI/ContentMgmt/download",
            headers=headers,
            data=xml_payload.encode("utf-8"),
            verify=False,
            stream=True,
            timeout=180
        ) as r:

            if r.status_code == 200:
                with open(caminho_saida, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"✅ Download finalizado: {caminho_saida}")
                return True
            else:
                print(f"❌ Erro {r.status_code} ao baixar: {r.text}")
                return False

    except Exception as e:
        print(f"❌ Erro no download: {e}")
        return False

import subprocess
import os
from datetime import datetime, timedelta
import cv2

def cortar_video(evento_str, video_info, ip=None, nome=None, cliente=None, logos=[]):
    nome_arquivo = video_info["nome"]
    caminho_original = os.path.abspath(nome_arquivo)

    if not os.path.exists(caminho_original):
        print(f"❌ Vídeo não encontrado para corte: {nome_arquivo}")
        return

    # Conversões de tempo
    evento_local = datetime.strptime(evento_str, "%Y-%m-%d %H:%M:%S")
    evento_utc = evento_local + timedelta(hours=3)  # Ajuste fuso da câmera
    inicio_video_utc = datetime.strptime(video_info["inicio"], "%Y-%m-%dT%H:%M:%SZ")
    tempo_corte = (evento_utc - inicio_video_utc).total_seconds() - 45


    # Offset relativo ao vídeo (em segundos)
    # offset_inicio = (evento_utc - timedelta(seconds=45)) - inicio_video
    duracao = 55  # segundos

    segundos_inicio = max(0, int(tempo_corte))  # garante que não fique negativo
    if segundos_inicio < 0:
        segundos_inicio = 0  # O corte não pode começar antes do início do vídeo

    nome_base = f"{ip}_{nome}_{cliente}_{evento_str.replace(' ', '_').replace(':', '-')}".replace(" ", "_")
    nome_saida = f"{nome_base}_CORTADO.mp4"
    caminho_saida = os.path.abspath(nome_saida)

    print(f"✂️ Cortando vídeo: {nome_arquivo}")
    print(f"📍 Início relativo: {segundos_inicio}s | Duração: {duracao}s")
    print(f"📼 Saída: {nome_saida}")

    comando = [
        "ffmpeg",
        "-ss", str(segundos_inicio),
        "-i", caminho_original,
        "-t", str(duracao),
        "-c:v", "copy",
        "-c:a", "aac",  # Garante compatibilidade de áudio
        "-y",  # Sobrescreve se já existir
        caminho_saida
    ]

    try:
        subprocess.run(comando, check=True)
        print(f"✅ Corte finalizado: {nome_saida}")
        # ➕ Adicionar logos após o corte
        adicionar_logos(caminho_saida, logos)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao cortar: {e}")


def baixar_e_cortar_videos():
    camera = carregar_configuracao_camera(index=0)
    IP = camera["ip"]
    PORTA = camera.get("porta", 8080)
    NOME = camera["nome"]
    CLIENTE = camera["cliente"]

    lista, sessao = carregar_dados(IP, NOME, CLIENTE)
    SESSION_TAG = sessao["SessionTag"]
    COOKIE_SESSION = sessao["CookieSession"]

    token = obter_token(IP, PORTA, SESSION_TAG, COOKIE_SESSION)
    if not token:
        return

    for item in lista:
        if not item["video"]:
            continue

        evento_str = item["evento"]
        video_info = item["video"]
        url = video_info["url"]
        nome_video = extrair_nome_video_da_url(url)
        video_info["nome"] = nome_video

        sucesso = baixar_video(IP, PORTA, SESSION_TAG, COOKIE_SESSION, token, url, nome_video)
        if sucesso:
            cortar_video(evento_str, video_info, IP, NOME, CLIENTE, camera.get("logos", []))


def processar_eventos_para_camera(nome_camera):
    from urllib.parse import unquote
    import re

    # 1. Carregar dados e sessão
    camera, sessao = carregar_dados_camera(nome_camera)
    ip = camera["ip"]
    porta_http = 8080
    porta_digest = 8000
    usuario = camera["usuario"]
    senha = camera["senha"]
    cliente = camera["cliente"]

    # 2. Listar vídeos disponíveis da câmera
    videos_disponiveis = listar_videos_disponiveis(ip, porta_digest, usuario, senha)

    # 3. Ler eventos do arquivo .txt
    eventos = extrair_eventos_txt(nome_camera, ip, cliente)

    # 4. Para cada evento, identificar vídeo correspondente e processar
    for i, horario_evento in enumerate(eventos):
        print(f"\n🔎 [{i+1}/{len(eventos)}] Processando evento em {horario_evento}...")

        # Achar vídeo que cobre esse evento
        video = encontrar_video_para_evento(horario_evento, videos_disponiveis)
        if not video:
            print("⚠ Nenhum vídeo encontrado para este evento.")
            continue

        playback_uri = video["playbackURI"]
        inicio_utc = video["startTime"]

        nome_base = f"{nome_camera.replace(' ', '_')}_{horario_evento.replace(' ', '_').replace(':', '-')}"
        nome_video_original = f"{nome_base}_original.mp4"
        nome_video_corte = f"{nome_base}_corte.mp4"

        # Baixar vídeo, se ainda não existir
        if not os.path.exists(nome_video_original):
            sucesso = baixar_video_hikvision(ip, porta_http, playback_uri, nome_video_original, sessao)
            if not sucesso:
                continue
        else:
            print(f"📁 Vídeo original já existe: {nome_video_original}")

        # Cortar vídeo
        try:
            cortar_video(nome_video_original, nome_video_corte, horario_evento, inicio_utc)
        except Exception as e:
            print(f"❌ Erro ao cortar vídeo: {e}")
            continue

        print(f"🎬 Corte salvo: {nome_video_corte}")

############################################

def buscar_url_logo(nome_arquivo):
    """Busca a URL do arquivo diretamente da listagem da API."""
    API_LISTAR_URL = "hhttp://34.58.6.78:8000/listavideos"

    try:
        response = requests.get(API_LISTAR_URL)
        if response.status_code == 200:
            arquivos = response.json()
            for item in arquivos:
                if "video_url" in item and item["video_url"].endswith(nome_arquivo):
                    return item["video_url"]
        else:
            print(f"❌ Erro ao consultar API. Código: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao consultar API: {e}")
    
    return None

def baixar_logo(nome_arquivo):
    """Baixa a logo usando a URL correta da listagem da API."""
    logo_path = f"/{nome_arquivo}"
    if os.path.exists(logo_path):
        return logo_path  # Já existe localmente

    url_logo = buscar_url_logo(nome_arquivo)
    if not url_logo:
        print(f"⚠ Logo '{nome_arquivo}' não encontrada na listagem da API.")
        return None

    print(f"🌐 Baixando logo via: {url_logo}")
    response = requests.get(url_logo, stream=True)
    if response.status_code == 200:
        os.makedirs("", exist_ok=True)
        with open(logo_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"✅ Logo '{nome_arquivo}' baixada com sucesso!")
        return logo_path
    else:
        print(f"❌ Falha ao baixar logo '{nome_arquivo}'. Código: {response.status_code}")
        return None




def adicionar_logos(video_path, logos):
    """
    Adiciona logos ao vídeo.
    - FastPlay.png deve ficar exatamente sobre a logo HIKVISION no canto superior direito.
    - Até 6 logos adicionais, posicionadas dinamicamente.
    """
    if not os.path.exists(video_path):
        print(f"❌ Erro: O vídeo {video_path} não foi encontrado.")
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Erro ao abrir vídeo para adicionar logos.")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_output = video_path.replace(".mp4", "_temp.mp4")  # Arquivo temporário
    out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

    logos_para_adicionar = []

    # 🔹 Ajuste para posicionar FastPlay exatamente sobre Hikvision
    fastplay_path = baixar_logo("FastPlay.png")
    if fastplay_path:
        logo = cv2.imread(fastplay_path, cv2.IMREAD_UNCHANGED)
        
        # 🔹 Aumentar a largura (esticar horizontalmente)
        logo = cv2.resize(logo, (270, 60), interpolation=cv2.INTER_LINEAR)  # Esticando mais
        
        fastplay_x = max(10, width - 570)  # Move mais para a esquerda
        fastplay_y = 50  # Pequeno ajuste para baixo

        print(f"FastPlay X final: {fastplay_x} (largura total do vídeo: {width})")  # Debug

        logos_para_adicionar.append((logo, (fastplay_x, fastplay_y)))

    else:
        print("⚠ FastPlay.png não encontrada.")

    # 🔹 Baixar e posicionar outras logos dinamicamente
    posicoes = [
        ("top_left", (10, 10)),
        ("top_center", (width // 2 - 75, 10)),
        ("bottom_left", (10, height - 80)),
        ("bottom_center", (width // 2 - 75, height - 80)),
        ("bottom_right", (width - 150, height - 80)),
        ("center", (width // 2 - 75, height // 2 - 40)),
    ]

    for idx, logo_nome in enumerate(logos[:6]):  # Máximo 6 logos
        logo_path = baixar_logo(logo_nome)
        if logo_path:
            logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
            logo = cv2.resize(logo, (200, 100), interpolation=cv2.INTER_AREA)  # Redimensiona
            _, pos = posicoes[idx]
            logos_para_adicionar.append((logo, pos))

    # 🔹 Processar os frames do vídeo e adicionar as logos
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        for logo, (x, y) in logos_para_adicionar:
            if logo is None:
                continue

            h, w = logo.shape[:2]
            if y + h > frame.shape[0] or x + w > frame.shape[1]:
                continue  # Evita erro de sobreposição fora da imagem

            if logo.shape[2] == 4:  # PNG com transparência
                overlay = frame[y:y+h, x:x+w]
                alpha = logo[:, :, 3] / 255.0
                for c in range(3):
                    overlay[:, :, c] = overlay[:, :, c] * (1 - alpha) + logo[:, :, c] * alpha
                frame[y:y+h, x:x+w] = overlay
            else:
                frame[y:y+h, x:x+w] = logo

        out.write(frame)

    cap.release()
    out.release()

    # Substituir o vídeo original pelo novo processado
    # ➕ Recupera áudio do vídeo original
    video_com_audio = video_path.replace(".mp4", "_com_audio.mp4")

    comando_ffmpeg = [
        "ffmpeg",
        "-i", temp_output,        # vídeo com logo (sem áudio)
        "-i", video_path,         # vídeo original com áudio
        "-map", "0:v:0",          # usa vídeo do primeiro
        "-map", "1:a:0",          # usa áudio do segundo
        "-c:v", "copy",           # sem reencodar vídeo
        "-c:a", "aac",            # reencoda áudio para compatível
        "-y",                     # sobrescreve
        video_com_audio
    ]

    subprocess.run(comando_ffmpeg, check=True)

    # Substitui o vídeo final com áudio restaurado
    os.replace(video_com_audio, video_path)
    os.remove(temp_output)

    print(f"✅ Vídeo com logos e áudio restaurado: {video_path}")

    return True