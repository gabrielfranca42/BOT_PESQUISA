##esse deve resumir e ler deve ser rodado primeiro o e de captura sempre  
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize

def extrair_texto(url, timeout=10):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # remove scripts e estilos
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        texto = " ".join(p.get_text() for p in soup.find_all("p"))
        return texto.strip()

    except Exception as e:
        print(f"Erro ao ler {url}: {e}")
        return ""

def resumir_texto(texto, max_frases=5):
    frases = sent_tokenize(texto, language="portuguese")

    if len(frases) <= max_frases:
        return " ".join(frases)

    return " ".join(frases[:max_frases])

def processar_links(arquivo_links="links_filtrados.txt", arquivo_saida="resumos.txt"):
    with open(arquivo_links, "r", encoding="utf-8") as f:
        links = [l.strip() for l in f if l.strip()]

    with open(arquivo_saida, "w", encoding="utf-8") as out:
        for i, link in enumerate(links, 1):
            print(f"\nLendo ({i}/{len(links)}): {link}")

            texto = extrair_texto(link)

            if len(texto) < 300:
                print("Conteúdo muito curto, pulando...")
                continue

            resumo = resumir_texto(texto)

            out.write(f"LINK: {link}\n")
            out.write("RESUMO:\n")
            out.write(resumo + "\n")
            out.write("-" * 80 + "\n")

    print("\n✅ Resumos salvos em resumos.txt")

if __name__ == "__main__":
    processar_links()