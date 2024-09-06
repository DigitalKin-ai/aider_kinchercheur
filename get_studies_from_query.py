import os
import requests
import json
import time
import re
import hashlib
import base64
from dotenv import load_dotenv
from urllib.parse import quote, urlparse
from tqdm import tqdm
from colorama import init, Fore, Style
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from aider.llm import litellm
from aider.io import InputOutput

init(autoreset=True)  # Initialise colorama

load_dotenv()

# Nombre maximum de workers pour le ThreadPoolExecutor
MAX_WORKERS = 5

# Temps d'attente entre les tentatives de téléchargement (en secondes)
WAIT_TIME = 2

def add_to_todolist(filename):
    with open('todolist.md', 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f"[ ] Lire, analyser et incorporer {filename}\n" + content)

def is_study_in_folder(title, output_dir):
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
    filename = os.path.join(output_dir, f"{safe_title[:100]}.pdf")
    return os.path.exists(filename)

# Vérification de la clé API
if not os.getenv('SEARCHAPI_KEY'):
    print(f"{Fore.RED}Erreur : La clé SEARCHAPI_KEY n'a pas été trouvée dans le fichier .env")
    exit(1)

def get_studies_from_query(query, num_articles=40, output_dir='etudes'):
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
        print(f"{Fore.CYAN}Envoi de la requête à {url}")
        print(f"{Fore.CYAN}Paramètres: {params}")
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"{Fore.GREEN}Statut de la réponse: {response.status_code}")
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Erreur lors de la requête: {e}")
            if hasattr(e, 'response'):
                print(f"{Fore.RED}Statut de la réponse: {e.response.status_code}")
                print(f"{Fore.RED}Contenu de la réponse: {e.response.text}")
            else:
                print(f"{Fore.RED}Pas de réponse du serveur")
            return None
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}Erreur lors du décodage JSON: {e}")
            print(f"{Fore.RED}Contenu de la réponse: {response.text}")
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
        #print(f"Contenu de la réponse OpenAccess Button: {response.text}")
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

    def process_result(result, io):
        url = result.get('link')
        title = result.get('title')
        
        print(f"\n{Fore.CYAN}Traitement de : {Style.BRIGHT}{title}")
        print(f"{Fore.CYAN}URL : {url}")

        if is_pdf_in_cache(title) or is_study_in_folder(title, output_dir):
            print(f"{Fore.YELLOW}PDF déjà téléchargé pour : {title}")
            return
        
        os.makedirs(output_dir, exist_ok=True)

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
            print(f"{Fore.BLUE}Essai de téléchargement via {method_name}...")
            try:
                pdf_content = method_func()
                if pdf_content:
                    successful_method = method_name
                    break
            except Exception as e:
                print(f"{Fore.RED}Erreur lors de la tentative via {method_name}: {e}")
            time.sleep(WAIT_TIME)  # Attendre entre chaque tentative

        if pdf_content and isinstance(pdf_content, bytes):
            # Générer un nom de fichier sûr
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
            filename = os.path.join(output_dir, f"{safe_title[:100]}.pdf")
            
            try:
                with open(filename, 'wb') as f:
                    f.write(pdf_content)
                print(f"{Fore.GREEN}PDF sauvegardé via {successful_method} : {filename}")
                
                # Sauvegarder dans le cache
                save_pdf_to_cache(title, pdf_content)
                
                # Ajouter à la todolist
                add_to_todolist(filename)

                # Extraire les informations du PDF immédiatement après le téléchargement
                extracted_info = extract_pdf_info(pdf_content, url, title, io)
                
                # Sauvegarder les informations extraites dans un fichier JSON
                json_filename = os.path.join(output_dir, f"{safe_title[:100]}.json")
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(extracted_info, f, ensure_ascii=False, indent=2)
                print(f"{Fore.GREEN}Informations extraites sauvegardées : {json_filename}")

            except IOError as e:
                print(f"{Fore.RED}Erreur lors de l'écriture du fichier {filename}: {e}")
        else:
            print(f"{Fore.RED}Impossible de trouver un PDF valide pour : {title}")

    # Obtenir les résultats de Google Scholar
    scholar_results = google_scholar_request(query, num_articles)

    if scholar_results is None:
        print("Impossible d'obtenir les résultats de Google Scholar. Vérifiez votre clé API et la connexion internet.")
        return

    # Create an instance of InputOutput
    io = InputOutput()

    # Traiter chaque résultat en parallèle
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_result, result, io) for result in scholar_results.get('organic_results', [])]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Téléchargement des articles"):
            try:
                future.result()  # This will raise any exceptions that occurred during execution
            except concurrent.futures.TimeoutError:
                print(f"{Fore.RED}Une tâche a dépassé le temps imparti.")
            except Exception as e:
                print(f"{Fore.RED}Une erreur s'est produite lors du traitement d'un article : {e}")

    print(f"{Fore.GREEN}Tous les articles ont été traités.")

class StudyExtractor:
    def __init__(self, io):
        self.io = io

    def extract_and_save_pdf_info(self, pdf_content, url, title):
        # Encode PDF content to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        # Prepare the message for the LLM
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts information from scientific papers."},
            {"role": "user", "content": f"""Please extract the following information from the given PDF:

    |id|Nom|Auteurs|Journal|Date de publication|DOI|Citation|Type|Mots-clés|lienOrigine|Lien Google Drive|Abstract|Objectif de l'étude|Méthodologie|Conclusions de l'étude|Pertinence au regard de l'axe de travail 1|Pertinence au regard de l'axe de travail 2|Pertinence de l'étude au regard de l'axe de travail 3|Pertinence au regard de l'objectif de recherche|Axe de travail|Sélection|Apports et contributions|Verbatims des apports et contributions|Extraits Verbatim des Verrous|Verrous de l'étude|Données chifrées|Date de création|Date de dernière modification|

    The PDF content is provided as a base64 encoded string: {pdf_base64}

    Additional information:
    URL: {url}
    Title: {title}

    Please provide the extracted information in a JSON format."""}
        ]

        # Make the API call
        response = litellm.completion(
            model="gpt-4",
            messages=messages,
        )

        # Parse the extracted information
        extracted_info = json.loads(response.choices[0].message.content)
        
        # Save the extracted information to a markdown file
        safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
        md_filename = os.path.join('analyses', f"{safe_title[:100]}.md")
        os.makedirs('analyses', exist_ok=True)
        
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            for key, value in extracted_info.items():
                f.write(f"## {key}\n{value}\n\n")
        
        print(f"{Fore.GREEN}Analyse sauvegardée : {md_filename}")
        
        # Add the analysis to the current chat session
        with open(md_filename, 'r', encoding='utf-8') as f:
            analysis_content = f.read()
        
        self.io.tool_output(f"Nouvelle analyse ajoutée au chat : {md_filename}")
        self.io.append_chat_history(analysis_content, linebreak=True)
        
        return extracted_info

def extract_pdf_info(pdf_content, url, title, io):
    extractor = StudyExtractor(io)
    return extractor.extract_and_save_pdf_info(pdf_content, url, title)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharger des articles scientifiques basés sur une requête.")
    parser.add_argument("query", help="La requête de recherche")
    parser.add_argument("-n", "--num_articles", type=int, default=40, help="Nombre d'articles à télécharger (max 100)")
    parser.add_argument("-o", "--output", default="etudes", help="Dossier de sortie pour les PDFs")
    args = parser.parse_args()

    num_articles = min(100, max(1, args.num_articles))  # Limiter entre 1 et 100
    get_studies_from_query(args.query, num_articles, args.output)
