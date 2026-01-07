from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from bs4 import BeautifulSoup
import time

# --- NOVAS PALAVRAS-CHAVE INTEGRADAS ---
palavras_chave_br = [
    "subvenção econômica", "recursos obrigatórios P&D", "ICT empresa portuária",
    "encomenda tecnológica", "Rota 2030 logística", "Programa Mover",
    "Finep Mais Inovação Brasil", "Embrapii portos", "BNDES FUNTEC sustentabilidade",
    "ANP descarbonização", "edital portuário", "chamada pública infraestrutura"
]

palavras_chave_int = [
    "TRL Technology Readiness Level port", "Waterborne Transport innovation",
    "ZEWT Zero-Emission Waterborne Transport", "Shore-to-Ship Power funding",
    "Just Transition Fund ports", "Horizon Europe Cluster 5", "BlueInvest startup",
    "IMO technical cooperation greenhouse gas", "World Bank port infrastructure grant"
]

# Unificando as listas para o filtro de conteúdo
todas_palavras = palavras_chave_br + palavras_chave_int

class RedeLentaError(Exception):
    pass

def verificar_conteudo(link, termos, timeout=10):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        texto = " ".join(p.get_text() for p in soup.find_all(["p", "h1", "h2"])).lower()
        # Verifica se ao menos um termo relevante aparece na página
        return any(termo.lower() in texto for termo in termos)
    except:
        return False

def buscar_links_duckduckgo(termos_busca, minimo_links=50, arquivo_saida="links_filtrados.txt"):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    links_final = []

    # Realizamos buscas por blocos para aumentar a precisão
    # Busca 1: Termos Nacionais | Busca 2: Termos Internacionais
    buscas = [
        " ".join(palavras_chave_br[:5]) + " edital 2024 2025",
        " ".join(palavras_chave_int[:4]) + " call for proposals"
    ]

    for query in buscas:
        try:
            driver.get("https://duckduckgo.com/")
            time.sleep(2)
            caixa_busca = driver.find_element(By.NAME, "q")
            caixa_busca.send_keys(query)
            caixa_busca.send_keys(Keys.RETURN)
            
            # Scroll e captura
            for _ in range(3): # Tenta carregar mais resultados 3 vezes
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-testid='result-title-a']"))
                )
                resultados = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
                
                for r in resultados:
                    href = r.get_attribute("href")
                    if href and href not in links_final:
                        print(f"[ANALISANDO] {href}")
                        if verificar_conteudo(href, todas_palavras):
                            links_final.append(href)
                            print(f"  -- ✅ Relevante!")
                    
                    if len(links_final) >= minimo_links: break
                
                if len(links_final) >= minimo_links: break
                
                # Clica em "Mais Resultados" se existir
                try:
                    btn_mais = driver.find_element(By.CSS_SELECTOR, "a.result--more__btn")
                    btn_mais.click()
                    time.sleep(2)
                except:
                    break

        except Exception as e:
            print(f"Erro durante a busca: {e}")

    driver.quit()

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        for link in links_final:
            f.write(link + "\n")
    
    return links_final

if __name__ == "__main__":
    print("Iniciando busca avançada (Brasil & Internacional)...")
    try:
        links = buscar_links_duckduckgo(todas_palavras, minimo_links=30)
        print(f"\n✅ Busca concluída! {len(links)} links salvos em 'links_filtrados.txt'")
    except Exception as e:
        print(f"❌ Erro: {e}")