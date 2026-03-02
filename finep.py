import time
import os
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class BotFinepExclusivo:
    def __init__(self):
        # Configuração de pastas específicas para a FINEP
        self.PASTA_EVIDENCIAS = "debug_evidencias_FINEP"
        if not os.path.exists(self.PASTA_EVIDENCIAS):
            os.makedirs(self.PASTA_EVIDENCIAS)
        
        # Arquivos de log com final "finep"
        self.arquivo_saida = "editais_filtrados_FINEP.txt"
        self.historico_path = "historico_links_FINEP.log"
        self.historico = self._carregar_historico()
        
        # Pesos ajustados para os editais das imagens (Agro, Defesa, Inovação)
        self.PESOS_POSITIVOS = {
            "inovação": 10, "tecnologia": 10, "agroindustriais": 20, 
            "defesa": 20, "sustentáveis": 15, "fndct": 10, "software": 15,
            "digital": 10, "startup": 15, "bioeconomia": 15
        }
        
        # Filtro pesado para ignorar editais encerrados das fotos
        self.PESOS_NEGATIVOS = {
            "encerrada": -100, "concluído": -100, "finalizado": -100,
            "teatro": -50, "música": -50, "cultura": -50, "pnab": -80
        }

    def _carregar_historico(self):
        if os.path.exists(self.historico_path):
            with open(self.historico_path, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f)
        return set()

    def configurar_driver(self):
        opts = Options()
        # Removido headless para você acompanhar o clique nas páginas
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--start-maximized")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    def calcular_score(self, texto):
        texto_low = texto.lower()
        score = 0
        
        # Busca por 2025 ou 2026 conforme identificado nas imagens
        if any(ano in texto_low for ano in ["2025", "2026"]):
            score += 15
        else:
            score -= 10 # Penaliza se for antigo ou sem data clara

        for p, v in self.PESOS_POSITIVOS.items():
            if p in texto_low: score += v
        for p, v in self.PESOS_NEGATIVOS.items():
            if p in texto_low: score += v
        return score

    def minerar_finep(self):
        driver = self.configurar_driver()
        url_base = "http://www.finep.gov.br/chamadas-publicas"
        total_novos = 0
        
        try:
            driver.get(url_base)
            time.sleep(6) # Tempo para o JavaScript carregar a lista
            
            # Percorre as páginas (1 a 3) para pegar os editais que estão passando batido
            for num_pagina in range(1, 4):
                print(f"[*] Analisando FINEP - Página {num_pagina}")
                
                # Screenshot de auditoria por página
                driver.save_screenshot(os.path.join(self.PASTA_EVIDENCIAS, f"captura_pag_{num_pagina}.png"))
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Localiza os containers de editais (divs que agrupam título e links)
                blocos = soup.find_all(['div', 'li'], class_=lambda x: x and any(t in x.lower() for t in ['item', 'chamada', 'row']))
                
                for bloco in blocos:
                    link_tag = bloco.find('a', href=True)
                    if not link_tag: continue
                    
                    url_completa = urljoin(url_base, link_tag['href'])
                    if url_completa in self.historico: continue
                    
                    # Captura o texto do bloco inteiro (Título + Datas + Público-alvo)
                    texto_contexto = bloco.get_text(" ", strip=True)
                    score = self.calcular_score(texto_contexto)
                    
                    if score > 15: # Filtro de relevância
                        print(f"    [OK] Edital Relevante: {link_tag.get_text(strip=True)[:50]}")
                        self.salvar_edital(texto_contexto, url_completa)
                        self.historico.add(url_completa)
                        total_novos += 1
                
                # Lógica de Paginação: tenta clicar no próximo número
                try:
                    proxima = driver.find_element(By.LINK_TEXT, str(num_pagina + 1))
                    driver.execute_script("arguments[0].click();", proxima)
                    time.sleep(5)
                except:
                    print("    [!] Fim das páginas disponíveis.")
                    break
                    
        except Exception as e:
            print(f"    [!] Erro durante a execução: {e}")
        finally:
            driver.quit()
        return total_novos

    def salvar_edital(self, texto, url):
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        titulo_limpo = " ".join(texto.split()).replace("\n", "")
        linha = f"[{data_hoje}] {titulo_limpo[:250]} -> {url}\n"
        
        with open(self.arquivo_saida, "a", encoding="utf-8") as f:
            f.write(linha)
        with open(self.historico_path, "a", encoding="utf-8") as f:
            f.write(f"{url}\n")

if __name__ == "__main__":
    bot = BotFinepExclusivo()
    resultado = bot.minerar_finep()
    print(f"\n[FIM] Processo FINEP concluído. {resultado} novos editais encontrados.")