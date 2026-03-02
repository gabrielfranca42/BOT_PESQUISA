import time
import os
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- CONFIGURACOES ---
ARQUIVO_SAIDA = "editais_tecnicos_puros.txt"
ARQUIVO_HISTORICO = "historico_links.log"

# 1. BANIMENTO DE URL (Impede links institucionais e menus)
URL_LIXO = [
    "faleconosco", "perguntas-frequentes", "mapa-do-site", "webmail", "acessibilidade", 
    "institucional", "denuncia", "ouvidoria", "a-facepe", "/fomento/", "quem-somos", 
    "missao", "organograma", "legislacao", "acervos", "javascript:;", "#", "visualizador"
]

# 2. BANIMENTO DE TERMOS NO TITULO (Limpa menus e noticias)
TEMA_LIXO = [
    "pnab", "música", "audiovisual", "cinema", "cultura", "museu", "teatro", 
    "missão", "valores", "quem somos", "histórico", "calendário", "documentos",
    "dúvidas", "valores vigentes", "organograma", "plano estratégico"
]

# 3. TEMAS OBRIGATORIOS (Foco Industrial e ESG)
TEMAS_ALVO = ["edital", "chamada", "chamamento", "seleção", "concurso", "fomento"]

def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def validar_real(titulo, url):
    t_lower = titulo.lower()
    u_lower = url.lower()
    
    # Critério 1: Bloqueia links quebrados ou âncoras
    if u_lower.startswith("javascript") or u_lower.startswith("#") or len(u_lower) < 10:
        return False

    # Critério 2: Se estiver na blacklist de URL institucional, descarta
    if any(lixo in u_lower for lixo in URL_LIXO):
        return False
    
    # Critério 3: Se o título for muito longo (provavelmente um menu inteiro capturado)
    if len(t_lower) > 200 or t_lower.count(" ") > 25:
        return False

    # Critério 4: Se for audiovisual/cultura ou institucional, descarta
    if any(lixo in t_lower for lixo in TEMA_LIXO):
        return False
        
    # Critério 5: Tem que parecer um EDITAL ou CHAMADA real
    if any(alvo in t_lower for alvo in TEMAS_ALVO):
        # Garante que tenha o tema técnico desejado
        temas_tecnicos = ["indústria", "esg", "digital", "energia", "transição", "inovação", "hidrogênio"]
        if any(tema in t_lower for tema in temas_tecnicos):
            return True
            
    # Exceção para links diretos da FINEP que já sabemos que são editais
    if "chamadapublica" in u_lower and not any(l in t_lower for l in TEMA_LIXO):
        return True

    return False

def registrar_limpo(titulo, url, fonte):
    data = datetime.now().strftime("%d/%m/%Y")
    titulo_limpo = " ".join(titulo.split()).upper()
    entrada = f"[{data}] {fonte} | {titulo_limpo} | {url}\n"
    with open(ARQUIVO_SAIDA, "a", encoding="utf-8") as f:
        f.write(entrada)
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as h:
        h.write(f"{url}\n")

def minerar(driver, historico, url_alvo, nome_fonte):
    print(f"Varrendo: {nome_fonte}...")
    driver.get(url_alvo)
    time.sleep(7)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    achados = 0
    
    # Busca por links, mas filtra o texto para não pegar o menu inteiro
    for link in soup.find_all('a', href=True):
        url = urljoin(url_alvo, link['href'])
        
        # Tenta pegar apenas o texto do link, se for vazio, tenta o pai imediato
        titulo = link.get_text(" ", strip=True)
        if not titulo or len(titulo) < 5:
            titulo = link.parent.get_text(" ", strip=True)
        
        if url not in historico and validar_real(titulo, url):
            registrar_limpo(titulo[:180], url, nome_fonte)
            historico.add(url)
            achados += 1
            
    return achados

def main():
    driver = configurar_driver()
    historico = carregar_historico()
    
    # Links diretos para as áreas de EDITAIS (evitando homepages institucionais)
    fontes = {
        "FINEP": "http://www.finep.gov.br/chamadas-publicas",
        "FACEPE": "http://www.facepe.br/editais/abertos/",
        "BNDES_INOVACAO": "https://www.bndes.gov.br/wps/portal/site/home/onde-atuamos/inovacao/",
        "SENAI": "https://plataformadeinovacao.senai.br/editais/abertos"
    }

    total = 0
    for nome, url in fontes.items():
        try:
            total += minerar(driver, historico, url, nome)
        except: pass

    # Google focado apenas em resultados de 2026 com filtro de negação de lixo
    q_google = 'site:gov.br "edital" "2026" (industria OR esg OR energia) -institucional -missao -quem-somos'
    driver.get(f"https://www.google.com/search?q={q_google}")
    time.sleep(5)
    total += minerar(driver, historico, "https://google.com", "GOOGLE")

    driver.quit()
    print(f"\nBusca finalizada. {total} editais técnicos reais salvos.")

if __name__ == "__main__":
    main()