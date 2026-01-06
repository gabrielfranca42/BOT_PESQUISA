from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def buscar_links(termo, minimo_links=10, arquivo_saida="links_filtrados.txt"):
    palavras_chave = termo.lower().split()

    # tenta usar qualquer navegador disponível
    try:
        driver = webdriver.Edge()
    except:
        try:
            driver = webdriver.Chrome()
        except:
            driver = webdriver.Firefox()

    driver.get("https://duckduckgo.com/")
    time.sleep(2)

    caixa_busca = driver.find_element(By.NAME, "q")
    caixa_busca.send_keys(termo)
    caixa_busca.send_keys(Keys.RETURN)
    time.sleep(3)

    links_filtrados = set()

    while len(links_filtrados) < minimo_links:
        resultados = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")

        for r in resultados:
            href = r.get_attribute("href")
            if href:
                href_lower = href.lower()
                if any(palavra in href_lower for palavra in palavras_chave):
                    links_filtrados.add(href)

        # tenta carregar mais resultados
        try:
            botao = driver.find_element(By.CSS_SELECTOR, "a.result--more__btn")
            botao.click()
            time.sleep(3)
        except:
            break

    driver.quit()

    # salva em arquivo txt (bloco de notas)
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        for link in list(links_filtrados)[:minimo_links]:
            f.write(link + "\n")

    return list(links_filtrados)[:minimo_links]


if __name__ == "__main__":
    termo = "inovação esg sustentabilidade verde"
    links = buscar_links(termo, minimo_links=10)

    print(f"Total de links salvos: {len(links)}")
    for link in links:
        print(link)
