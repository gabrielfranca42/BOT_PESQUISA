import time
import os
import re
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
        # Configuração de pastas e arquivos
        self.PASTA_EVIDENCIAS = "debug_evidencias_FINEP"
        if not os.path.exists(self.PASTA_EVIDENCIAS):
            os.makedirs(self.PASTA_EVIDENCIAS)
        
        self.arquivo_saida = "editais_filtrados_FINEP.txt"
        self.historico_path = "historico_links_FINEP.log"
        self.historico = self._carregar_historico()
        
        # REGRA DE CORTE: Prazo de envio deve ser >= 04/03/2026
        # Como hoje é 03/03/2026, isso pegará tudo de amanhã em diante.
        self.DATA_CORTE = datetime(2026, 3, 4)

    def _carregar_historico(self):
        if os.path.exists(self.historico_path):
            with open(self.historico_path, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f)
        return set()

    def configurar_driver(self):
        opts = Options()
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--start-maximized")
        # Descomente a linha abaixo para rodar sem abrir o navegador visualmente
        # opts.add_argument("--headless")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    def extrair_data_final(self, item_soup):
        """
        Localiza o rótulo <strong> específico e extrai a data do <span> vizinho.
        Padrão: <strong>Prazo para envio de propostas até: </strong> <span>31/08/2026</span>
        """
        try:
            # 1. Busca pela tag <strong> com o texto exato
            filtro_texto = "Prazo para envio de propostas até:"
            strong_tag = item_soup.find("strong", string=re.compile(filtro_texto, re.IGNORECASE))
            
            if strong_tag:
                # Busca o <span> que contém a data dentro do mesmo container
                container = strong_tag.parent
                span_data = container.find("span")
                
                if span_data:
                    data_texto = span_data.get_text(strip=True)
                    match = re.search(r"(\d{2}/\d{2}/\d{4})", data_texto)
                    if match:
                        return datetime.strptime(match.group(1), "%d/%m/%Y")
            
            # 2. Fallback: Se a estrutura de tags falhar, busca por texto bruto no bloco
            texto_bloco = item_soup.get_text(" ", strip=True)
            if filtro_texto in texto_bloco:
                # Busca a primeira data que aparece após o texto do rótulo
                match = re.search(rf"{filtro_texto}.*?(\d{{2}}/\d{{2}}/\d{{4}})", texto_bloco)
                if match:
                    return datetime.strptime(match.group(1), "%d/%m/%Y")
                    
        except Exception as e:
            print(f"      [!] Erro ao processar data: {e}")
        return None

    def minerar_finep(self):
        driver = self.configurar_driver()
        # URL com filtro de situação aberta
        url_alvo = "http://www.finep.gov.br/chamadas-publicas?situacao=aberta"
        total_novos = 0
        
        try:
            driver.get(url_alvo)
            print(f"[*] Acessando: {url_alvo}")
            time.sleep(8) # Tempo para o JavaScript carregar a lista
            
            for num_pagina in range(1, 11):
                print(f"[*] Analisando Página {num_pagina}...")
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                itens = soup.find_all('div', class_='item')
                
                if not itens:
                    print("    [!] Nenhum edital encontrado nesta página.")
                    break

                for item in itens:
                    # Captura link e título
                    h3 = item.find('h3')
                    link_tag = h3.find('a', href=True) if h3 else None
                    if not link_tag: continue
                    
                    url_completa = urljoin("http://www.finep.gov.br", link_tag['href'])
                    
                    # Extração da data de encerramento
                    data_prazo = self.extrair_data_final(item)
                    
                    # FILTRO: Prazo deve ser maior ou igual a 04/03/2026
                    if data_prazo and data_prazo >= self.DATA_CORTE:
                        if url_completa not in self.historico:
                            titulo = link_tag.get_text(strip=True)
                            prazo_formatado = data_prazo.strftime('%d/%m/%Y')
                            
                            print(f"    [MATCH] Edital: {titulo[:60]}... | Fim: {prazo_formatado}")
                            
                            # Salva os dados
                            self.salvar_edital(item.get_text(" ", strip=True), url_completa, data_prazo)
                            self.historico.add(url_completa)
                            total_novos += 1
                    
                # Lógica de Paginação
                try:
                    proxima_pag = str(num_pagina + 1)
                    botao_proximo = driver.find_element(By.LINK_TEXT, proxima_pag)
                    driver.execute_script("arguments[0].click();", botao_proximo)
                    time.sleep(6)
                except:
                    print("    [!] Fim da paginação disponível.")
                    break
                    
        except Exception as e:
            print(f"    [!] Erro durante a execução: {e}")
        finally:
            driver.quit()
        return total_novos

    def salvar_edital(self, texto, url, data_fim):
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        prazo_str = data_fim.strftime("%d/%m/%Y")
        # Limpa o título para o arquivo de texto
        resumo = " ".join(texto.split()).replace("\n", "")
        
        entry = f"[{data_hoje}] [PRAZO FINAL: {prazo_str}] {resumo[:230]}... -> {url}\n"
        
        with open(self.arquivo_saida, "a", encoding="utf-8") as f:
            f.write(entry)
        with open(self.historico_path, "a", encoding="utf-8") as f:
            f.write(f"{url}\n")

if __name__ == "__main__":
    bot = BotFinepExclusivo()
    total = bot.minerar_finep()
    print(f"\n[CONCLUÍDO] O bot encontrou {total} novos editais com prazos válidos.")
    print(f"Verifique o arquivo: {bot.arquivo_saida}")