from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from threading import Thread
from google.cloud import storage
from google.oauth2 import service_account

from createConfigCamera import criar_configuracao_cameras
from getEvent import iniciar_rotina_get_event
from GetListVideosDownload import carregar_configuracao_camera, buscar_videos_com_eventos
from GetExtractTransformLoad import baixar_e_cortar_videos



app = Flask(__name__)
CORS(app)

GCS_BUCKET = "fastreplay_bucket"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/joaorafaelmotta/path/fastreplay-acc-chave.json"
client = storage.Client()



# Conectar ao banco de dados SQLite e criar tabelas corretamente
def init_db():
    conn = sqlite3.connect("uploads.db")
    cursor = conn.cursor()

    # Tabela de Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cliente TEXT NOT NULL
        )
    ''')

    # Tabela de Salas associada a Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS salas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            nome_sala TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # Tabela de Dias associada a Salas e Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sala_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            dia TEXT NOT NULL,
            FOREIGN KEY (sala_id) REFERENCES salas(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # Tabela de Horários associada a Salas, Clientes e Dias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sala_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            dia_id INTEGER NOT NULL,
            horario TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (sala_id) REFERENCES salas(id),
            FOREIGN KEY (dia_id) REFERENCES dias(id)
        )
    ''')

    # Tabela de Uploads associada a todas as informações anteriores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            sala_id INTEGER NOT NULL,
            dia_id INTEGER NOT NULL,
            horario_id INTEGER NOT NULL,
            cameraip text NOT NULL,
            video_url TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (sala_id) REFERENCES salas(id),
            FOREIGN KEY (dia_id) REFERENCES dias(id),
            FOREIGN KEY (horario_id) REFERENCES horarios(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()


def iniciar_rotina_get_list_videos():
    try:
        camera = carregar_configuracao_camera(index=0)
        buscar_videos_com_eventos(camera)
    except Exception as e:
        print(f" Erro na rotina de listagem de vídeos: {e}")


# createConfigCamera
@app.route("/api/criar-config-camera", methods=["POST"])
def api_criar_config_camera():
    try:
        resultado = criar_configuracao_cameras()
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GetListVideosDownload
@app.route('/api/get-list-videos', methods=['GET'])
def get_list_videos():
    try:
        camera = carregar_configuracao_camera(index=0)
        buscar_videos_com_eventos(camera)
        return jsonify({"status": "ok", "mensagem": "Lista de vídeos gerada com sucesso."})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

# GetExtractTransformLoad
@app.route("/baixar-cortar-videos", methods=["GET"])
def rota_baixar_e_cortar():
    try:
        baixar_e_cortar_videos()
        return jsonify({"status": "sucesso", "mensagem": "Vídeos baixados e cortados com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500



# Rota para listar clientes
@app.route("/api/clientes")
def get_clientes():
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_cliente FROM clientes")
        clientes = cursor.fetchall()
        conn.close()

        result = [{"id": row[0], "nome": row[1]} for row in clientes]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
# Rota para buscar clientes
@app.route("/api/cliente/<int:cliente_id>", methods=["GET"])
def get_videos_by_cliente(cliente_id):
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome_cliente FROM clientes WHERE id = ?
        """, (cliente_id,))
        videos = cursor.fetchall()
        conn.close()

        result = [{"nome_cliente": row[0]} for row in videos]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Rota para listar salas de um cliente específico
@app.route("/api/salas/<int:cliente_id>")
def get_salas(cliente_id):
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_sala FROM salas WHERE cliente_id = ?", (cliente_id,))
        salas = cursor.fetchall()
        conn.close()

        result = [{"id": row[0], "nome": row[1]} for row in salas]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rota para listar dias disponíveis para uma sala específica
@app.route("/api/dias/<int:cliente_id>/<int:sala_id>")
def get_dias(sala_id,cliente_id):
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, dia FROM dias WHERE sala_id = ? AND cliente_id = ?", (sala_id,cliente_id,))
        dias = cursor.fetchall()
        conn.close()

        result = [{"id": row[0], "dia": row[1]} for row in dias]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rota para listar horários disponíveis para um dia específico
@app.route("/api/horarios/<int:cliente_id>/<int:sala_id>/<int:dia_id>")
def get_horarios(dia_id,sala_id,cliente_id):
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, horario FROM horarios WHERE dia_id = ? AND sala_id = ? AND cliente_id = ?", (dia_id,sala_id,cliente_id,))
        horarios = cursor.fetchall()
        conn.close()

        result = [{"id": row[0], "horario": row[1]} for row in horarios]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/videos/<int:cliente_id>/<int:sala_id>/<int:dia_id>/<int:horario_id>")
def get_videos(cliente_id, sala_id, dia_id, horario_id):
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT video_url FROM uploads
            WHERE cliente_id = ? AND sala_id = ? AND dia_id = ? AND horario_id = ?
        """, (cliente_id, sala_id, dia_id, horario_id))
        videos = cursor.fetchall()
        conn.close()

        result = [{"video_url": row[0]} for row in videos]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
# Rota de Upload
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    if "cliente" not in request.form or "quadra" not in request.form or "cameraIP" not in request.form or "dia" not in request.form or "horario" not in request.form:
        return jsonify({"error": "Missing required parameters (cliente, quadra, cameraIP, dia, horario)"}), 400

    file = request.files["file"]
    cliente = request.form["cliente"]
    quadra = request.form["quadra"]
    cameraIP = request.form["cameraIP"]
    dia = request.form["dia"]
    horario = request.form["horario"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        
         # Configuração do cliente GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        
        # Definindo o nome do arquivo no GCS
        blob = bucket.blob(file.filename)
        
        # Enviar o arquivo para o GCS
        blob.upload_from_file(file, content_type="video/mp4", predefined_acl="publicRead")
        
        # Gerar URL pública
        video_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{file.filename}"
        
        
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()

        # Verificar se o cliente já existe
        cursor.execute("SELECT id FROM clientes WHERE nome_cliente = ?", (cliente,))
        cliente_row = cursor.fetchone()
        if cliente_row:
            cliente_id = cliente_row[0]
        else:
            cursor.execute("INSERT INTO clientes (nome_cliente) VALUES (?)", (cliente,))
            cliente_id = cursor.lastrowid

        # Verificar se a quadra já existe para o cliente
        cursor.execute("SELECT id FROM salas WHERE nome_sala = ? AND cliente_id = ?", (quadra, cliente_id))
        sala_row = cursor.fetchone()
        if sala_row:
            sala_id = sala_row[0]
        else:
            cursor.execute("INSERT INTO salas (cliente_id, nome_sala) VALUES (?, ?)", (cliente_id, quadra))
            sala_id = cursor.lastrowid

        # Verificar se o dia já existe
        cursor.execute("SELECT id FROM dias WHERE sala_id = ? AND cliente_id = ? AND dia = ?", (sala_id, cliente_id, dia))
        dia_row = cursor.fetchone()
        if dia_row:
            dia_id = dia_row[0]
        else:
            cursor.execute("INSERT INTO dias (sala_id, cliente_id, dia) VALUES (?, ?, ?)", (sala_id, cliente_id, dia))
            dia_id = cursor.lastrowid

        # Verificar se o horário já existe
        cursor.execute("SELECT id FROM horarios WHERE sala_id = ? AND cliente_id = ? AND dia_id = ? AND horario = ?", (sala_id, cliente_id, dia_id, horario))
        horario_row = cursor.fetchone()
        if horario_row:
            horario_id = horario_row[0]
        else:
            cursor.execute("INSERT INTO horarios (sala_id, cliente_id, dia_id, horario) VALUES (?, ?, ?, ?)", (sala_id, cliente_id, dia_id, horario))
            horario_id = cursor.lastrowid

        # Inserir os dados do upload
        cursor.execute("INSERT INTO uploads (cliente_id, sala_id, dia_id, horario_id, cameraIP, video_url) VALUES (?, ?, ?, ?, ?, ?)",
                       (cliente_id, sala_id, dia_id, horario_id, cameraIP, video_url))
        conn.commit()
        conn.close()

        return jsonify({
            "message": "File uploaded successfully!",
            "url": video_url,
            "cliente": cliente,
            "quadra": quadra,
            "cameraIP": cameraIP,
            "dia": dia,
            "horario": horario
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/listavideos", methods=["GET"])
def get_uploads():
    cliente_nome = request.args.get("cliente")
    quadra_nome = request.args.get("quadra")
    dia_data = request.args.get("dia")
    horario_hora = request.args.get("horario")
    
    try:
        conn = sqlite3.connect("uploads.db")
        cursor = conn.cursor()
        
        query = """
            SELECT uploads.id, clientes.nome_cliente, salas.nome_sala, dias.dia, horarios.horario, uploads.cameraIP, uploads.video_url
            FROM uploads
            JOIN clientes ON uploads.cliente_id = clientes.id
            JOIN salas ON uploads.sala_id = salas.id
            JOIN dias ON uploads.dia_id = dias.id
            JOIN horarios ON uploads.horario_id = horarios.id
            WHERE 1=1
        """
        params = []
        
        if cliente_nome:
            query += " AND clientes.nome_cliente = ?"
            params.append(cliente_nome)
        if quadra_nome:
            query += " AND salas.nome_sala = ?"
            params.append(quadra_nome)
        if dia_data:
            query += " AND dias.dia = ?"
            params.append(dia_data)
        if horario_hora:
            query += " AND horarios.horario = ?"
            params.append(horario_hora)

        cursor.execute(query, params)
        uploads = cursor.fetchall()
        conn.close()
        
        result = [
            {
                "id": row[0],
                "cliente": row[1],
                "quadra": row[2],
                "dia": row[3],
                "horario": row[4],
                "cameraIP": row[5],
                "video_url": row[6]
            }
            for row in uploads
        ]
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Cria o arquivo config_cameras.json e envia para a API
    criar_configuracao_cameras()

    # Inicia a rotina de eventos (getEvent) em background
    thread_event = Thread(target=iniciar_rotina_get_event)
    thread_event.daemon = True
    thread_event.start()

    # Inicia a rotina de listagem de vídeos (em paralelo)
    thread_videos = Thread(target=iniciar_rotina_get_list_videos)
    thread_videos.daemon = True
    thread_videos.start()

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=8000)