import time
import os
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class BotEditais:
    def __init__(self):
        # --- CONFIGURAÇÕES DE DEBUG ---
        self.MODO_VISUAL = True  # Mude para False para rodar escondido
        self.PASTA_EVIDENCIAS = "debug_evidencias"
        if not os.path.exists(self.PASTA_EVIDENCIAS):
            os.makedirs(self.PASTA_EVIDENCIAS)
        
        self.arquivo_saida = "editais_filtrados.txt"
        self.historico_path = "historico_links.log"
        self.historico = self._carregar_historico()
        
        self.PESOS_POSITIVOS = {
            "inovação": 10, "tecnologia": 10, "software": 15, "industrial": 10,
            "esg": 15, "sustentabilidade": 10, "startup": 15, "fomento": 5,
            "desenvolvimento": 5, "energia": 10, "hidrogênio": 15, "digital": 10
        }
        
        self.PESOS_NEGATIVOS = {
            "teatro": -50, "música": -50, "cultura": -50, "esporte": -50,
            "institucional": -30, "quem somos": -30, "licitação": -10,
            "estágio": -40, "concurso público": -40, "pnab": -50
        }

    def _carregar_historico(self):
        if os.path.exists(self.historico_path):
            with open(self.historico_path, "r") as f:
                return set(line.strip() for line in f)
        return set()

    def configurar_driver(self):
        opts = Options()
        if not self.MODO_VISUAL:
            opts.add_argument("--headless")
        
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--start-maximized")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    def calcular_relevancia(self, texto, url):
        texto_low = (texto + " " + url).lower()
        score = 0
        
        # Filtro de Data
        tem_ano = any(ano in texto_low for ano in ["2025", "2026", "26"])
        if not tem_ano:
            score -= 5 

        for palavra, valor in self.PESOS_POSITIVOS.items():
            if palavra in texto_low: score += valor
            
        for palavra, valor in self.PESOS_NEGATIVOS.items():
            if palavra in texto_low: score += valor

        return score, tem_ano

    def minerar_pagina(self, driver, url_fonte, nome_fonte):
        print(f"\n[*] ACESSANDO: {nome_fonte} ({url_fonte})")
        try:
            driver.get(url_fonte)
            time.sleep(6) # Tempo para carregar JS
            
            # Tira print para conferência visual
            foto_path = os.path.join(self.PASTA_EVIDENCIAS, f"{nome_fonte}.png")
            driver.save_screenshot(foto_path)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            all_links = soup.find_all('a', href=True)
            
            print(f"    [x] Total de links brutos encontrados na página: {len(all_links)}")
            
            links_encontrados = 0
            for tag_a in all_links:
                url_completa = urljoin(url_fonte, tag_a['href'])
                
                if url_completa in self.historico:
                    continue

                contexto = tag_a.get_text(strip=True)
                if len(contexto) < 10:
                    contexto = tag_a.parent.get_text(" ", strip=True)[:200]

                score, tem_ano = self.calcular_relevancia(contexto, url_completa)

                # Log de auditoria para links com algum potencial (Score > 0)
                if score > 0:
                    status_ano = "COM DATA" if tem_ano else "SEM DATA"
                    print(f"      - Analisando: '{contexto[:40]}...' | Score: {score} | {status_ano}")

                if score > 10:
                    print(f"      [x] APROVADO: {url_completa}")
                    self.salvar_edital(nome_fonte, contexto, url_completa)
                    self.historico.add(url_completa)
                    links_encontrados += 1
            
            return links_encontrados
        except Exception as e:
            print(f"    [!] ERRO CRÍTICO em {nome_fonte}: {e}")
            return 0

    def salvar_edital(self, fonte, titulo, url):
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        titulo_limpo = " ".join(titulo.split()).replace("\n", "")
        linha = f"[{data_hoje}] [{fonte}] {titulo_limpo[:150]} -> {url}\n"
        with open(self.arquivo_saida, "a", encoding="utf-8") as f:
            f.write(linha)
        with open(self.historico_path, "a") as f:
            f.write(f"{url}\n")

    def executar(self):
        driver = self.configurar_driver()
        fontes = {
           "FINEP": "http://www.finep.gov.br/chamadas-publicas",
           "SENAI_INOVACAO": "https://plataformadeinovacao.senai.br/editais",
           "CONFAP": "https://confap.org.br/news/category/chamadas-publicas/",
           "FAPESP": "https://fapesp.br/chamadas",
           "EMBRAPII": "https://embrapii.org.br/categoria/chamadas-publicas/"
        }

        for nome, url in fontes.items():
            novos = self.minerar_pagina(driver, url, nome)
            print(f"    [=>] Fim de varredura {nome}: {novos} editais úteis salvos.")

        driver.quit()
        print(f"\n[FIM] Processo concluído. Verifique a pasta '{self.PASTA_EVIDENCIAS}' para ver as imagens dos sites.")

if __name__ == "__main__":
    bot = BotEditais()
    bot.executar()