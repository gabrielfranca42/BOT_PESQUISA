from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from bs4 import BeautifulSoup
import time

# >>> MODIFICAÇÃO: imports para filtro temporal
from datetime import datetime
import re

# --- PALAVRAS-CHAVE ---
palavras_chave_br = [
    "subvenção econômica", "recursos obrigatórios P&D", "ICT empresa portuária",
    "encomenda tecnológica", "Rota 2030 logística", "Programa Mover",
    "Finep Mais Inovação Brasil", "Embrapii portos", "BNDES FUNTEC sustentabilidade",
    "ANP descarbonização", "edital portuário", "chamada pública infraestrutura",
    "MCTI", "FACEPE", "premiação"
]

palavras_chave_int = [
    "TRL Technology Readiness Level port", "Waterborne Transport innovation",
    "ZEWT Zero-Emission Waterborne Transport", "Shore-to-Ship Power funding",
    "Just Transition Fund ports", "Horizon Europe Cluster 5", "BlueInvest startup",
    "IMO technical cooperation greenhouse gas", "World Bank port infrastructure grant"
]

# >>> MODIFICAÇÃO INGLÊS: somente palavras internacionais
todas_palavras = palavras_chave_int


# >>> MODIFICAÇÃO INGLÊS: termos obrigatórios em inglês
termos_ingles_obrigatorios = [
    "call for proposals", "funding", "grant", "programme",
    "innovation", "horizon europe", "application", "deadline"
]


class RedeLentaError(Exception):
    pass


# >>> RANGE TEMPORAL
DATA_INICIO = datetime(2025, 6, 1)
DATA_FIM    = datetime(2026, 1, 8)


# >>> FUNÇÃO DE EXTRAÇÃO DE DATA (inalterada)
def extrair_data(texto):
    padroes = [
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}\s+de\s+\w+\s+de\s+\d{4})'
    ]

    meses = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
    }

    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            data_str = match.group(1)
            try:
                if "/" in data_str:
                    return datetime.strptime(data_str, "%d/%m/%Y")
                elif "-" in data_str:
                    return datetime.strptime(data_str, "%Y-%m-%d")
                elif "de" in data_str.lower():
                    partes = data_str.lower().split(" de ")
                    dia = int(partes[0])
                    mes = meses.get(partes[1], 0)
                    ano = int(partes[2])
                    if mes:
                        return datetime(ano, mes, dia)
            except:
                pass
    return None


# >>> MODIFICAÇÃO INGLÊS: detecção real de idioma
def pagina_em_ingles(soup):
    html = soup.find("html")
    if html and html.get("lang"):
        return html.get("lang").lower().startswith("en")

    meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
    if meta_lang and "en" in meta_lang.get("content", "").lower():
        return True

    return False


# >>> FUNÇÃO PRINCIPAL COM FILTROS DE INGLÊS + DATA
def verificar_conteudo(link, termos, timeout=10):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link, headers=headers, timeout=timeout)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # >>> MODIFICAÇÃO INGLÊS: rejeita páginas não inglesas
        if not pagina_em_ingles(soup):
            return False

        texto = " ".join(
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(["p", "h1", "h2", "span", "time"])
        ).lower()

        # >>> DATA
        data_publicacao = extrair_data(texto)
        if not data_publicacao:
            return False

        if not (DATA_INICIO <= data_publicacao <= DATA_FIM):
            return False

        # >>> MODIFICAÇÃO INGLÊS: exige termos técnicos em inglês
        if not any(t in texto for t in termos_ingles_obrigatorios):
            return False

        # >>> Palavras-chave internacionais
        return any(termo.lower() in texto for termo in termos)

    except:
        return False


def buscar_links_duckduckgo(termos_busca, minimo_links=50, arquivo_saida="links_filtrados_ingles.txt"):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    links_final = []

    # >>> MODIFICAÇÃO INGLÊS: buscas focadas internacionalmente
    buscas = [
        " ".join(palavras_chave_int[:4]) + " call for proposals funding grant",
        "Horizon Europe port innovation call funding",
        "World Bank port infrastructure grant call"
    ]

    for query in buscas:
        try:
            driver.get("https://duckduckgo.com/")
            time.sleep(2)

            caixa_busca = driver.find_element(By.NAME, "q")
            caixa_busca.send_keys(query)
            caixa_busca.send_keys(Keys.RETURN)

            for _ in range(3):
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "a[data-testid='result-title-a']")
                    )
                )

                resultados = driver.find_elements(
                    By.CSS_SELECTOR, "a[data-testid='result-title-a']"
                )

                for r in resultados:
                    href = r.get_attribute("href")
                    if href and href not in links_final:
                        print(f"[ANALISANDO] {href}")

                        if verificar_conteudo(href, todas_palavras):
                            links_final.append(href)
                            print("  -- ✅ English | Relevant | In period")

                    if len(links_final) >= minimo_links:
                        break

                if len(links_final) >= minimo_links:
                    break

                try:
                    driver.find_element(By.CSS_SELECTOR, "a.result--more__btn").click()
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
    print("🔍 Iniciando busca EXCLUSIVA em inglês...")
    try:
        links = buscar_links_duckduckgo(todas_palavras, minimo_links=30)
        print(f"\n✅ Busca concluída! {len(links)} links salvos em 'links_filtrados_ingles.txt'")
    except Exception as e:
        print(f"❌ Erro: {e}")
