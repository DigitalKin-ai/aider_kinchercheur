import os
import requests
import json
import time
import re
import hashlib
from dotenv import load_dotenv
from urllib.parse import quote, urlparse
from tqdm import tqdm

load_dotenv()

# Vérification de la clé API
if not os.getenv('SEARCHAPI_KEY'):
    print("Erreur : La clé SEARCHAPI_KEY n'a pas été trouvée dans le fichier .env")
    exit(1)

def get_studies_from_query(query, num_articles=40):
    # Fonction pour faire une requête à Google Scholar
    def google_scholar_request(query, num_articles):
        url = "https://www.searchapi.io/api/v1/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('SEARCHAPI_KEY')}",
            "Content-Type": "application/json"
        }
        params = {
            "engine": "google_scholar",
            "q": query,
            "num": num_articles,
            "time_period_min": 2010
        }
        print(f"Envoi de la requête à {url}")
        print(f"Paramètres: {params}")
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Statut de la réponse: {response.status_code}")
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête: {e}")
            if hasattr(e, 'response'):
                print(f"Statut de la réponse: {e.response.status_code}")
                print(f"Contenu de la réponse: {e.response.text}")
            else:
                print("Pas de réponse du serveur")
            return None
        except json.JSONDecodeError as e:
            print(f"Erreur lors du décodage JSON: {e}")
            print(f"Contenu de la réponse: {response.text}")
            return None

    # Fonction pour vérifier si un PDF est déjà en cache
    def is_pdf_in_cache(title):
        cache_dir = 'cache'
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        cache_file = os.path.join(cache_dir, hashlib.md5(title.encode()).hexdigest() + '.pdf')
        return os.path.exists(cache_file)

    # Fonction pour sauvegarder un PDF dans le cache
    def save_pdf_to_cache(title, pdf_content):
        cache_dir = 'cache'
        cache_file = os.path.join(cache_dir, hashlib.md5(title.encode()).hexdigest() + '.pdf')
        with open(cache_file, 'wb') as f:
            f.write(pdf_content)

    # Fonction pour télécharger directement le PDF
    def download_pdf(url):
        try:
            response = requests.get(url, allow_redirects=True)
            if response.headers.get('content-type') == 'application/pdf':
                return response.content
        except requests.exceptions.RequestException:
            return None
        return None

    # Fonction pour obtenir le PDF d'une étude via openaccessbutton
    def get_pdf_openaccessbutton(id):
        url = f"https://api.openaccessbutton.org/find?id={id}"
        print(f"url: {url}")
        response = requests.get(url)
        print(f"Contenu de la réponse OpenAccess Button: {response.text}")
        data = response.json()
        if 'data' in data and 'url' in data['data']:
            pdf_url = data['data']['url']
            pdf_response = requests.get(pdf_url)
            if pdf_response.headers.get('content-type') == 'application/pdf':
                return pdf_response.content
        return None

    # Fonction pour obtenir le PDF via Sci-Hub
    def get_pdf_scihub(identifier):
        scihub_url = f"https://sci-hub.ru/{quote(identifier)}"
        try:
            response = requests.get(scihub_url)
            if response.status_code == 200:
                pdf_url = response.text.split('iframe src="')[1].split('"')[0]
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                pdf_response = requests.get(pdf_url)
                if pdf_response.headers.get('content-type') == 'application/pdf':
                    return pdf_response.content
        except Exception as e:
            print(f"Erreur lors de la tentative de téléchargement via Sci-Hub: {e}")
        return None

    def get_pdf_arxiv(url):
        if 'arxiv.org' in url:
            arxiv_id = url.split('/')[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            try:
                response = requests.get(pdf_url)
                if response.headers.get('content-type') == 'application/pdf':
                    return response.content
            except Exception as e:
                print(f"Erreur lors de la tentative de téléchargement depuis arXiv: {e}")
        return None

    def get_pdf_google_scholar(title):
        query = f"{title} filetype:pdf"
        url = "https://www.searchapi.io/api/v1/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('SEARCHAPI_KEY')}",
            "Content-Type": "application/json"
        }
        params = {
            "engine": "google",
            "q": query,
            "num": 1
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            if 'organic_results' in result and result['organic_results']:
                pdf_url = result['organic_results'][0].get('link')
                if pdf_url:
                    pdf_response = requests.get(pdf_url)
                    if pdf_response.headers.get('content-type') == 'application/pdf':
                        return pdf_response.content
        except Exception as e:
            print(f"Erreur lors de la recherche sur Google Scholar: {e}")
        return None

    # Obtenir les résultats de Google Scholar
    scholar_results = google_scholar_request(query, num_articles)

    if scholar_results is None:
        print("Impossible d'obtenir les résultats de Google Scholar. Vérifiez votre clé API et la connexion internet.")
        return

    # Traiter chaque résultat
    for result in tqdm(scholar_results.get('organic_results', []), desc="Téléchargement des articles"):
        url = result.get('link')
        title = result.get('title')
        
        print(f"\nTraitement de : {title}")
        print(f"URL : {url}")

        if is_pdf_in_cache(title):
            print(f"PDF déjà en cache pour : {title}")
            continue

        # Liste des méthodes de téléchargement à essayer
        download_methods = [
            ("Téléchargement direct", lambda: download_pdf(url) if url else None),
            ("arXiv", lambda: get_pdf_arxiv(url) if url else None),
            ("OpenAccess Button", lambda: get_pdf_openaccessbutton(url or title)),
            ("Google Scholar", lambda: get_pdf_google_scholar(title)),
            ("Sci-Hub", lambda: get_pdf_scihub(url or title))
        ]

        pdf_content = None
        successful_method = None

        for method_name, method_func in download_methods:
            print(f"Essai de téléchargement via {method_name}...")
            try:
                pdf_content = method_func()
                if pdf_content:
                    successful_method = method_name
                    break
            except Exception as e:
                print(f"Erreur lors de la tentative via {method_name}: {e}")
            time.sleep(2)  # Attendre 2 secondes entre chaque tentative

        if pdf_content and isinstance(pdf_content, bytes):
            # Créer le dossier 'etudes' s'il n'existe pas
            os.makedirs('etudes', exist_ok=True)
            
            # Générer un nom de fichier sûr
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
            filename = f"etudes/{safe_title[:50]}.pdf"
            
            with open(filename, 'wb') as f:
                f.write(pdf_content)
            print(f"PDF sauvegardé via {successful_method} : {filename}")
            
            # Sauvegarder dans le cache
            save_pdf_to_cache(title, pdf_content)
        else:
            print(f"Impossible de trouver un PDF valide pour : {title}")

        time.sleep(5)  # Attendre 5 secondes entre chaque article

if __name__ == "__main__":
    query = input("Entrez votre requête de recherche : ")
    num_articles = int(input("Combien d'articles voulez-vous télécharger ? (max 100) : "))
    num_articles = min(100, max(1, num_articles))  # Limiter entre 1 et 100
    get_studies_from_query(query, num_articles)
