from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import base64
import json
import time
import os
from datetime import datetime, timedelta


def autenticar_com_selenium(IP, PORTA, USUARIO, SENHA, NOME, CLIENTE):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280,1024")

    prefs = {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "download.default_directory": os.path.abspath("")  # pasta local
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        url = f"http://{IP}:{PORTA}/"
        driver.get(url)
        time.sleep(5)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))

        driver.execute_script(f"""
            const inputUser = document.querySelector("#portal > div > div > div.login.default-login > div.middle > div > form > div.login-user.el-form-item.is-required-right > div > div > input");
            const inputPass = document.querySelector("input[type='password']");
            if (inputUser && inputPass) {{
                inputUser.value = "{USUARIO}";
                inputUser.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inputUser.dispatchEvent(new Event('change', {{ bubbles: true }}));
                inputPass.value = "{SENHA}";
                inputPass.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inputPass.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)

        time.sleep(5)

        driver.execute_script('''
            document.querySelector("#portal > div > div > div.login.default-login > div.middle > div > form > div:nth-child(3) > div > button").click();
        ''')
        time.sleep(5)

        driver.execute_script('''
            document.querySelector("#app > div.main-content > div.header > div.nav > ul > li:nth-child(3)")?.click();
        ''')
        time.sleep(3)

        driver.execute_script('''
            fetch('/ISAPI/Streaming/channels/1/SearchVideoCodeMealParams', {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            }).then(res => console.log("✅ Requisição manual disparada:", res.status));
        ''')
        time.sleep(3)

        for _ in range(15):
            auth_info_raw = driver.execute_script("return sessionStorage.getItem('authInfo');")
            if auth_info_raw:
                try:
                    decoded = base64.b64decode(auth_info_raw).decode()
                    parsed = json.loads(decoded)
                    session_tag = parsed.get("sessionTag")
                    if session_tag:
                        break
                except:
                    pass
            time.sleep(1)

        cookie_session = None
        for _ in range(15):
            cookies = driver.get_cookies()
            for cookie in cookies:
                if cookie["name"].startswith("WebSession_"):
                    cookie_session = f"{cookie['name']}={cookie['value']}"
                    break
            if cookie_session:
                break
            time.sleep(1)

        if session_tag and cookie_session:
            nome_arquivo = f"sessao_camera_{IP}_{NOME.replace(' ', '_')}_{CLIENTE.replace(' ', '_')}_.json"
            with open(nome_arquivo, "w") as f:
                json.dump({
                    "SessionTag": session_tag,
                    "CookieSession": cookie_session
                }, f, indent=2)
            print(f"📂 Sessão salva em '{nome_arquivo}'!")

        return driver

    except Exception as e:
        print(f"❌ Erro na autenticação: {e}")
        driver.quit()
        return None



def executar_rotina_logs(driver, IP, CLIENTE,NOME):
    try:
        while True:
            print("🔁 Iniciando rotina completa...")

            # Acessa 'Maintenance and Security'
            print("🛠️ Acessando 'Maintenance and Security'...")
            driver.execute_script('''
                document.querySelector("#app > div.main-content > div.header > div.nav > ul > li:nth-child(4) > p").click();
            ''')
            time.sleep(2)

            # Clica em 'Maintenance'
            print("🔧 Clicando em 'Maintenance'...")
            driver.execute_script('''
                document.querySelector("#operations > div > div.left.config-layout-menu > div > div.config-menu.el-scrollbar__wrap > div > div > div > div > ul > div:nth-child(1) > li").click();
            ''')
            time.sleep(2)

            # Clica em 'Log'
            print("📄 Clicando na aba 'Log'...")
            driver.execute_script('''
                document.querySelector("#tab-maintainLog").click();
            ''')
            time.sleep(2)

            # Dropdown para 'Alarm'
            print("📂 Clicando no dropdown de tipo de log...")
            dropdown_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "#operations > div > div.view > div > div > div.base-layout-content > div > div > div > div:nth-child(1) > div > form > div:nth-child(1) > div > div > div.el-input.el-input--suffix > input"))
            )
            dropdown_input.click()
            time.sleep(1)

            print("🚨 Esperando item 'Alarm' aparecer...")
            alarm_item = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//li[contains(., 'Alarm')]"))
            )
            ActionChains(driver).move_to_element(alarm_item).click().perform()
            time.sleep(2)

            # Clica em 'Search'
            print("🔍 Clicando em 'Search'...")
            driver.execute_script('''
                document.querySelector("#operations > div > div.view > div > div > div.base-layout-content > div > div > div > div:nth-child(1) > div > div > button").click();
            ''')
            time.sleep(3)

            # Clica em 'Export TXT File'
            print("⬇️ Clicando em 'Export TXT File'...")
            driver.execute_script('''
                document.querySelector("#operations > div > div.view > div > div > div.base-layout-content > div > div > div > div.filter-items.filter-btn > div > button:nth-child(1)").click();
            ''')

            print("💾 Verificando se o download ocorreu com sucesso...")
            download_dir = os.path.abspath("")
            os.makedirs(download_dir, exist_ok=True)
            download_ok = False
            start_time = time.time()
            arquivo_baixado = None

            while time.time() - start_time < 15:
                arquivos = sorted(os.listdir(download_dir), key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                txts = [f for f in arquivos if f.lower().endswith(".txt")]
                if txts:
                    arquivo_baixado = txts[0]
                    download_ok = True
                    break
                time.sleep(1)

            if download_ok:
                print(f"✅ Download detectado: {arquivo_baixado}")

                caminho_original = os.path.join(download_dir, arquivo_baixado)

                nome_formatado = NOME.replace(" ", "_")
                cliente_formatado = CLIENTE.replace(" ", "_")
                nome_novo = f"videos_{IP}_{nome_formatado}_{cliente_formatado}.txt"
                caminho_novo = os.path.join(download_dir, nome_novo)

                # Substitui se já existir
                if os.path.exists(caminho_novo):
                    os.remove(caminho_novo)

                os.rename(caminho_original, caminho_novo)

                print(f"📁 Arquivo renomeado para: {nome_novo}")
            else:
                print("❌ Nenhum .txt detectado após 15 segundos.")

            print("⏳ Aguardando 45 segundos para nova execução...")
            time.sleep(45)

    except Exception as e:
        print(f"❌ Erro na rotina de logs: {e}")

def iniciar_rotina_get_event():
    with open("config_cameras.json", "r", encoding="utf-8") as f:
        camera = json.load(f)["cameras"][0]

    IP = camera["ip"]
    PORTA = 8080  # ou camera["porta"]
    USUARIO = camera["usuario"]
    SENHA = camera["senha"]
    NOME = camera["nome"]
    CLIENTE = camera["cliente"]

    while True:
        print(f"🔄 Reiniciando sessão às {datetime.now().strftime('%H:%M:%S')}")
        driver = autenticar_com_selenium(IP, PORTA, USUARIO, SENHA, NOME, CLIENTE)
        if driver:
            t0 = datetime.now()
            try:
                while (datetime.now() - t0) < timedelta(minutes=15):
                    executar_rotina_logs(driver, IP, CLIENTE, NOME)
            finally:
                print("🧹 Finalizando driver e limpando sessão...")
                driver.quit()
        time.sleep(5)