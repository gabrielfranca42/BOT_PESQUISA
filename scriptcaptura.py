from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from bs4 import BeautifulSoup
import time

# Lista de palavras-chave
palavras_chave = [
    "inovação",  "desenvolvimento", "sustentabilidade", 
    "tecnologia limpa", "transformação digital", "criatividade",
    "novas soluções", "empreendedorismo", 
    "economia verde", "edital", "chamada pública", "concurso",
    "projeto", "financiamento", "subvenção", "apoio financeiro", "incentivo", "bolsa",
    "programa de fomento", "seleção pública", "proposta", "captação de recursos",
    "verde", "ambiental", "desenvolvimento sustentável", "economia circular" 
    , "redução de emissões", "gestão ambiental", "biodiversidade",
    "tecnologia sustentável", "inovação verde"
]

class RedeLentaError(Exception):
    """Erro customizado para quando a rede está lenta ou o carregamento falha"""
    pass

def verificar_conteudo(link, palavras_chave, timeout=10):
    """
    Retorna True se alguma palavra-chave estiver no conteúdo da página.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        texto = " ".join(p.get_text() for p in soup.find_all("p"))
        return any(palavra.lower() in texto.lower() for palavra in palavras_chave)
    except:
        return False

def buscar_links_duckduckgo(termos, minimo_links=50, arquivo_saida="links_prioridade_duck.txt", tempo_espera=10):
    termos = [t.lower() for t in termos]

    # Configurações do Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        raise RuntimeError(f"Não foi possível iniciar o Chrome: {e}")

    # Tenta acessar DuckDuckGo
    try:
        driver.get("https://duckduckgo.com/")
    except WebDriverException:
        driver.quit()
        raise RedeLentaError("Falha ao acessar DuckDuckGo. Possível problema de rede.")

    time.sleep(2)

    # Faz a busca
    try:
        caixa_busca = driver.find_element(By.NAME, "q")
        caixa_busca.send_keys(" ".join(termos))
        caixa_busca.send_keys(Keys.RETURN)
    except:
        driver.quit()
        raise RedeLentaError("Não foi possível localizar a barra de pesquisa. Verifique a rede ou o site.")

    links_final = []
    pagina = 1

    while len(links_final) < minimo_links:
        print(f"\n[DEBUG] Capturando página {pagina}...")

        try:
            WebDriverWait(driver, tempo_espera).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-testid='result-title-a']"))
            )
        except TimeoutException:
            driver.quit()
            raise RedeLentaError(f"Tempo de espera excedido na página {pagina}. Rede lenta ou site não carregou.")

        resultados = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
        print(f"[DEBUG] Links encontrados nesta página: {len(resultados)}")

        for r in resultados:
            href = r.get_attribute("href")
            if href and href not in links_final:
                # agora filtramos pelo conteúdo, não pelo URL
                if verificar_conteudo(href, palavras_chave):
                    links_final.append(href)
                    print(f"[DEBUG] Adicionado: {href}")

            if len(links_final) >= minimo_links:
                break

        print(f"[DEBUG] Total de links coletados até agora: {len(links_final)}")

        # Tenta ir para próxima página
        if len(links_final) < minimo_links:
            try:
                btn_mais = driver.find_element(By.CSS_SELECTOR, "a.result--more__btn")
                btn_mais.click()
                pagina += 1
                time.sleep(2)
            except:
                print("[DEBUG] Não há mais resultados. Finalizando.")
                break

    driver.quit()

    if not links_final:
        raise RedeLentaError("Nenhum link coletado com conteúdo relevante.")

    # Salva em arquivo
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        for link in links_final[:minimo_links]:
            f.write(link + "\n")

    return links_final[:minimo_links]

if __name__ == "__main__":
    try:
        links = buscar_links_duckduckgo(palavras_chave, minimo_links=50)
        print(f"\nTotal de links salvos: {len(links)}")
        for link in links:
            print(link)
    except RedeLentaError as e:
        print(f"\n❌ ERRO: {e}")
    except Exception as e:
        print(f"\n❌ ERRO inesperado: {e}")
