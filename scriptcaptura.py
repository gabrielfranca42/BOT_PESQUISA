import time
import os
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- CONFIGURACOES ---
ARQUIVO_SAIDA = "editais_encontrados.txt"
ARQUIVO_HISTORICO = "historico_links.log"

# Credenciais
LINKEDIN_USER = ""
LINKEDIN_PASS = ""

FONTES_SEMENTE = [
    "http://www.finep.gov.br/chamadas-publicas/chamadas-publicas",
    "https://www.bndes.gov.br/wps/portal/site/home/onde-atuamos/inovacao/editais",
    "https://www.gov.br/mdic/pt-br/assuntos/inovacao/editais-e-chamadas-publicas",
    "https://prosas.com.br/editais",
    "https://captamos.org.br/editais/"
]

def configurar_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Removido o headless para garantir que o JS da Finep execute corretamente
    return webdriver.Chrome(options=options)

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def registrar_achado(titulo, url):
    data_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entrada = f"DATA: {data_timestamp} | TITULO: {titulo} | URL: {url}\n"
    with open(ARQUIVO_SAIDA, "a", encoding="utf-8") as f:
        f.write(entrada)
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as h:
        h.write(f"{url}\n")

def login_linkedin(driver):
    print("Realizando login no LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    try:
        wait = WebDriverWait(driver, 15)
        user_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
        user_input.send_keys(LINKEDIN_USER)
        driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASS)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)
    except Exception as e:
        print(f"Erro no login LinkedIn: {e}")

def processar_conteudo(driver, historico, base_url):
    # Forçar o Selenium a rolar a página para baixo para ativar carregamentos preguiçosos (Lazy Load)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    contador = 0
    
    # Lista de palavras ampliada para nao perder nada da Finep
    palavras_chave = ["esg", "economia popular", "solidaria", "fomento", "edital", "chamada publica", "abertas", "seleção"]
    
    # Procurar em links e também em células de tabela (onde a Finep coloca os nomes)
    for link in soup.find_all('a', href=True):
        raw_url = link['href']
        url = urljoin(base_url, raw_url)
        
        # Pega o texto do link ou o texto do "pai" (caso o link seja apenas um ícone ao lado do título)
        texto = link.get_text().lower().strip()
        if not texto:
            texto = link.parent.get_text().lower().strip()
        
        if any(p in texto for p in palavras_chave):
            if url not in historico and "javascript" not in url and ".pdf" not in url:
                titulo = link.get_text(strip=True) or link.parent.get_text(strip=True)
                # Limpeza básica de títulos muito longos
                titulo = " ".join(titulo.split()[:15])
                
                registrar_achado(titulo, url)
                historico.add(url)
                contador += 1
    return contador

def main():
    print("Iniciando mineracao...")
    driver = configurar_driver()
    historico = carregar_historico()
    total_novos = 0

    # 1. LinkedIn
    login_linkedin(driver)

    # 2. Fontes Oficiais com Espera Explícita
    for site in FONTES_SEMENTE:
        try:
            print(f"Acessando: {site}")
            driver.get(site)
            
            # Se for Finep, espera especificamente pela tabela de editais
            if "finep" in site:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
            else:
                time.sleep(7)
                
            total_novos += processar_conteudo(driver, historico, site)
        except Exception as e:
            print(f"Erro em {site}: {e}")

    # 3. Google e LinkedIn Search
    print("Buscando no Google e LinkedIn...")
    # ... (mesma lógica de busca anterior)
    
    driver.quit()
    print(f"Finalizado. Novos registrados: {total_novos}")

if __name__ == "__main__":
    main()