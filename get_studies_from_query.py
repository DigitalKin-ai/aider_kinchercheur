import os
import requests
import json
import time
import re
import hashlib
import base64
import signal
import sys
import subprocess
from dotenv import load_dotenv
from urllib.parse import quote
from tqdm import tqdm
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from aider.llm import litellm
from aider.io import InputOutput
from pydantic import BaseModel, ValidationError, field_validator
from typing import List, Optional

init(autoreset=True)  # Initialise colorama

# Définition des constantes globales
DEFAULT_MAX_WORKERS = 10
DEFAULT_WAIT_TIME = 2

load_dotenv()

def check_and_install_dependencies():
    required_packages = [
        'requests', 'python-dotenv', 'tqdm', 'colorama', 'aider'
    ]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"{Fore.YELLOW}Le package {package} n'est pas installé. Installation en cours...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print(f"{Fore.GREEN}Toutes les dépendances sont installées.")

check_and_install_dependencies()

# Variable globale pour gérer l'interruption
interrupted = False

def signal_handler(signum, frame):
    global interrupted
    interrupted = True
    print(f"\n{Fore.YELLOW}Interruption demandée. Arrêt en cours...")

# Configurer le gestionnaire de signal
signal.signal(signal.SIGINT, signal_handler)

# Nombre maximum de workers pour le ThreadPoolExecutor
MAX_WORKERS = 5

# Temps d'attente entre les tentatives de téléchargement (en secondes)
WAIT_TIME = 2

def add_to_todolist(filename):
    with open('todolist.md', 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f"[ ] Incorporer les informations analysées dans {filename} au sein de l'état de l'art en cours de rédaction\n" + content)

def is_study_in_folder(title, output_dir):
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
    pdf_filename = os.path.join(output_dir, f"{safe_title[:100]}.pdf")
    json_filename = os.path.join(output_dir, f"{safe_title[:100]}.json")
    return os.path.exists(pdf_filename) or os.path.exists(json_filename)

# Vérification de la clé API
if not os.getenv('SEARCHAPI_KEY'):
    print(f"{Fore.RED}Erreur : La clé SEARCHAPI_KEY n'a pas été trouvée dans le fichier .env")
    exit(1)

def get_studies_from_query(query, num_articles=20, output_dir='etudes', max_workers=DEFAULT_MAX_WORKERS, analyze_immediately=True, io=None):
    global interrupted
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
        #print(f"url: {url}")
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
                # Utiliser une expression régulière pour trouver l'URL du PDF
                pdf_url_match = re.search(r'<iframe[^>]*src="([^"]*)"', response.text)
                if pdf_url_match and pdf_url_match.groups():
                    pdf_url = pdf_url_match.group(1)
                    if pdf_url.startswith('//'):
                        pdf_url = 'https:' + pdf_url
                    pdf_response = requests.get(pdf_url)
                    if pdf_response.headers.get('content-type') == 'application/pdf':
                        return pdf_response.content
                else:
                    print("Impossible de trouver l'URL du PDF sur la page Sci-Hub")
        except IndexError:
            print("Erreur d'index lors de l'extraction de l'URL du PDF sur Sci-Hub")
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

        if not os.path.exists(output_dir):
            print(f"{Fore.RED}Le dossier de sortie {output_dir} n'existe pas. Création...")
            os.makedirs(output_dir)

        if is_pdf_in_cache(title):
            print(f"{Fore.YELLOW}PDF déjà dans le cache pour : {title}")
            return
    
        if is_study_in_folder(title, output_dir):
            print(f"{Fore.YELLOW}Étude déjà dans le dossier de sortie pour : {title}")
            return
    
        print(f"{Fore.BLUE}Tentative de téléchargement pour : {title}")

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

                if analyze_immediately:
                    # Extraire les informations du PDF immédiatement après le téléchargement
                    extracted_info = extract_pdf_info(pdf_content, url, title, io)
                    
                    if extracted_info is not None:
                        # Sauvegarder les informations extraites dans le fichier analyses.md
                        md_filename = 'analyses.md'
                        with open(md_filename, 'a', encoding='utf-8') as f:
                            f.write(f"# {title}\n\n")
                            for key, value in extracted_info.items():
                                if value:  # N'écrit que les champs non vides
                                    f.write(f"## {key}\n{value}\n\n")
                            f.write("---\n\n")  # Séparateur entre les analyses
                        print(f"{Fore.GREEN}Informations extraites ajoutées à : {md_filename}")
                    else:
                        print(f"{Fore.YELLOW}L'étude n'a pas été traitée en raison de sa taille ou d'une erreur.")
                else:
                    print(f"{Fore.YELLOW}L'analyse immédiate est désactivée. Le PDF a été téléchargé mais pas analysé.")

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
    if io is None:
        io = InputOutput()

    # Traiter chaque résultat en parallèle
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for result in scholar_results.get('organic_results', []):
                if interrupted:
                    break
                futures.append(executor.submit(process_result, result, io))
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Téléchargement des articles"):
                if interrupted:
                    for f in futures:
                        f.cancel()
                    executor.shutdown(wait=False)
                    print(f"{Fore.YELLOW}Interruption détectée. Arrêt des téléchargements.")
                    break
                try:
                    future.result(timeout=60)  # Ajouter un timeout de 60 secondes
                except concurrent.futures.TimeoutError:
                    print(f"{Fore.RED}Une tâche a dépassé le temps imparti.")
                except Exception as e:
                    print(f"{Fore.RED}Une erreur s'est produite lors du traitement d'un article : {e}")

        if not interrupted:
            print(f"{Fore.GREEN}Tous les articles ont été traités.")
        else:
            print(f"{Fore.YELLOW}Le traitement a été interrompu.")
    except KeyboardInterrupt:
        interrupted = True
        print(f"\n{Fore.YELLOW}Interruption détectée. Arrêt des téléchargements.")
    
    # Vérifier le nombre de fichiers téléchargés et d'analyses ajoutées
    pdf_count = len([f for f in os.listdir(output_dir) if f.endswith('.pdf')])
    print(f"{Fore.GREEN}Nombre de PDFs téléchargés : {pdf_count}")
    
    if os.path.exists('analyses.md'):
        with open('analyses.md', 'r', encoding='utf-8') as f:
            analysis_count = f.read().count('# ')
        print(f"{Fore.GREEN}Nombre d'analyses ajoutées : {analysis_count}")

def run_all_analysis(io, model="gpt-4o-2024-08-06"):
    etudes_dir = 'etudes'
    analyses_dir = 'analyses'
    
    if not os.path.exists(analyses_dir):
        os.makedirs(analyses_dir)
    
    pdf_files = [f for f in os.listdir(etudes_dir) if f.endswith('.pdf')]
    
    extractor = StudyExtractor(io, model=model)
    
    def process_pdf(pdf_file):
        if interrupted:
            return None
        pdf_path = os.path.join(etudes_dir, pdf_file)
        analysis_file = os.path.join(analyses_dir, pdf_file.replace('.pdf', '.md'))
        
        if not os.path.exists(analysis_file):
            print(f"{Fore.CYAN}Analyse en cours pour : {pdf_file}")
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            title = pdf_file[:-4]  # Remove .pdf extension
            url = ""  # We don't have the original URL here
            
            return extractor.extract_and_save_pdf_info(pdf_content, url, title)
        else:
            print(f"{Fore.YELLOW}Analyse déjà existante pour : {pdf_file}")
            return None

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_pdf, pdf_file) for pdf_file in pdf_files]
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Analyse des PDFs"):
                if interrupted:
                    executor.shutdown(wait=False, cancel_futures=True)
                    print(f"{Fore.YELLOW}Interruption détectée. Arrêt des analyses.")
                    break
                try:
                    result = future.result()
                    if result:
                        print(f"{Fore.GREEN}Analyse terminée pour un fichier.")
                except Exception as e:
                    print(f"{Fore.RED}Une erreur s'est produite lors de l'analyse d'un PDF : {e}")

        if not interrupted:
            print(f"{Fore.GREEN}Toutes les analyses ont été effectuées.")

            # Vérification des analyses pour le mot "ÉCARTÉ"
            print(f"{Fore.CYAN}Vérification des analyses pour le mot 'ÉCARTÉ'...")
            for analysis_file in os.listdir(analyses_dir):
                if analysis_file.endswith('.md'):
                    file_path = os.path.join(analyses_dir, analysis_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "ÉCARTÉ" in content:
                            print(f"{Fore.YELLOW}Le mot 'ÉCARTÉ' a été trouvé dans {analysis_file}. Suppression de l'analyse du chat...")
                            io.tool_output(f"Suppression de l'analyse {analysis_file} du chat.")
                            io.append_chat_history(f"L'analyse {analysis_file} a été supprimée car elle contient le mot 'ÉCARTÉ'.", linebreak=True)

            print(f"{Fore.GREEN}Vérification terminée.")
        else:
            print(f"{Fore.YELLOW}Le traitement a été interrompu.")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interruption détectée. Arrêt des analyses.")

class StudyInfo(BaseModel):
    id: Optional[str] = None
    Nom: str = ""
    Auteurs: List[str] = []
    Journal: Optional[str] = None
    Date_de_publication: Optional[str] = None
    DOI: Optional[str] = None
    Citation: Optional[str] = None
    Type: Optional[str] = None
    Mots_cles: List[str] = []
    lienOrigine: Optional[str] = None
    Lien_Google_Drive: Optional[str] = None
    Abstract: str = ""
    Objectif_de_l_etude: str = ""
    Methodologie: str = ""
    Conclusions_de_l_etude: str = ""
    Pertinence_axe_1: Optional[str] = None
    Pertinence_axe_2: Optional[str] = None
    Pertinence_axe_3: Optional[str] = None
    Pertinence_objectif_recherche: str = ""
    Axe_de_travail: Optional[str] = None
    Selection: Optional[str] = None
    Apports_et_contributions: str = ""
    Verbatims_apports_contributions: List[str] = []
    Extraits_Verbatim_Verrous: List[str] = []
    Verrous_de_l_etude: List[str] = []
    Donnees_chiffrees: List[str] = []
    Date_de_creation: Optional[str] = None
    Date_de_derniere_modification: Optional[str] = None

    class Config:
        extra = "ignore"

    @field_validator('Auteurs', 'Mots_cles', 'Verbatims_apports_contributions', 'Extraits_Verbatim_Verrous', 'Verrous_de_l_etude', 'Donnees_chiffrees', mode='before')
    @classmethod
    def convert_empty_to_list(cls, v):
        if v == '' or v is None:
            return []
        elif isinstance(v, str):
            return [v]
        return v

class StudyExtractor:
    def __init__(self, io, model="gpt-4o-2024-08-06"):
        self.io = io
        self.model = model

    def extract_and_save_pdf_info(self, pdf_content, url, title):
        print(f"{Fore.CYAN}Début de l'extraction des informations pour : {title}")
        
        try:
            # Encode PDF content to base64
            print(f"{Fore.CYAN}Encodage du contenu PDF en base64...")
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            # Split the PDF content into chunks
            chunk_size = 50000  # Further reduced chunk size
            print(f"{Fore.CYAN}Découpage du contenu PDF en morceaux...")
            chunks = [pdf_base64[i:i+chunk_size] for i in range(0, len(pdf_base64), chunk_size)]
            print(f"{Fore.CYAN}Nombre de morceaux : {len(chunks)}")

            extracted_info = {}
            chunks_to_process = chunks[:30] + chunks[-10:] if len(chunks) > 50 else chunks
            for i, chunk in enumerate(chunks_to_process):
                if interrupted:
                    print(f"{Fore.YELLOW}Interruption détectée. Arrêt de l'extraction.")
                    return None
                chunk_index = i if i < 30 else len(chunks) - (50 - i)
                print(f"{Fore.CYAN}Traitement du morceau {chunk_index+1}/{len(chunks)} pour l'étude : {title}")
                # Prepare the message for the LLM
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that extracts information from scientific papers."},
                    {"role": "user", "content": f"""Please extract the following information from the given PDF chunk:

|id|Nom|Auteurs|Journal|Date de publication|DOI|Citation|Type|Mots-clés|lienOrigine|Lien Google Drive|Abstract|Objectif de l'étude|Méthodologie|Conclusions de l'étude|Pertinence au regard de l'axe de travail 1|Pertinence au regard de l'axe de travail 2|Pertinence de l'étude au regard de l'axe de travail 3|Pertinence au regard de l'objectif de recherche|Axe de travail|Sélection|Apports et contributions|Verbatims des apports et contributions|Extraits Verbatim des Verrous|Verrous de l'étude|Données chifrées|Date de création|Date de dernière modification|

This is chunk {i+1} of {len(chunks)} of the PDF content.
The PDF content chunk is provided as a base64 encoded string: {chunk}

Additional information:
URL: {url}
Title: {title}

Please provide the extracted information in a JSON format. If you can't find information for a field, leave it empty. Be thorough and include verbatim extracts whenever possible. Make sure to extract as much relevant information as possible, especially for key fields like Abstract, Objectif de l'étude, Méthodologie, and Conclusions de l'étude."""}
                ]

                # Make the API call
                try:
                    response = litellm.completion(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                    )

                    # Parse the extracted information
                    try:
                        chunk_info = StudyInfo.parse_raw(response.choices[0].message.content)
                    except ValidationError as e:
                        print(f"{Fore.YELLOW}Erreur de validation : {e}")
                        # Créer un objet StudyInfo avec des valeurs par défaut
                        chunk_info = StudyInfo()
                        # Essayer de remplir les champs disponibles
                        content = json.loads(response.choices[0].message.content)
                        for field in StudyInfo.__fields__:
                            if field in content:
                                setattr(chunk_info, field, content[field])

                    # Merge the chunk info into the main extracted_info
                    for field in StudyInfo.__fields__:
                        value = getattr(chunk_info, field)
                        if field not in extracted_info or not extracted_info[field]:
                            extracted_info[field] = value
                        elif isinstance(value, list):
                            extracted_info[field] = list(set(extracted_info[field] + value))
                        elif isinstance(value, str) and value:
                            extracted_info[field] += " " + value
                except Exception as e:
                    print(f"{Fore.RED}Erreur lors de l'extraction des informations du PDF (morceau {i+1}/{len(chunks)}) : {e}")
                    print(f"{Fore.RED}Contenu de la réponse : {response.choices[0].message.content[:500]}...")
                    continue  # Continue with the next chunk instead of returning None

            if not extracted_info:
                print(f"{Fore.RED}Aucune information n'a pu être extraite du PDF.")
                return None

            print(f"{Fore.CYAN}Extraction terminée. Début de la synthèse...")

            # Synthesize the results
            synthesis_messages = [
                {"role": "system", "content": "You are a helpful assistant that synthesizes information from scientific papers."},
                {"role": "user", "content": f"""Please synthesize the following information extracted from a scientific paper:

            {json.dumps(extracted_info, indent=2)}

            Provide a thorough summary for each field, ensuring that the information is coherent and non-repetitive. 
            Return the result in JSON format."""}
            ]

            synthesis_response = litellm.completion(
                model=self.model,
                messages=synthesis_messages,
                response_format={"type": "json_object"},
            )

            # Parse the synthesized information
            try:
                synthesized_info = StudyInfo.parse_raw(synthesis_response.choices[0].message.content)
            except ValidationError as e:
                print(f"{Fore.YELLOW}Erreur de validation lors de la synthèse : {e}")
                # Créer un objet StudyInfo avec des valeurs par défaut
                synthesized_info = StudyInfo()
                # Essayer de remplir les champs disponibles
                content = json.loads(synthesis_response.choices[0].message.content)
                for field in StudyInfo.__fields__:
                    if field in content:
                        setattr(synthesized_info, field, content[field])

            # Vérifier si l'analyse est vide ou insuffisante
            non_empty_fields = sum(1 for value in synthesized_info.dict().values() if value)
            if non_empty_fields < 5:  # Vous pouvez ajuster ce seuil selon vos besoins
                print(f"{Fore.YELLOW}L'analyse générée est insuffisante. Utilisation des informations brutes.")
                synthesized_info = StudyInfo(**extracted_info)
            
            # Vérifier à nouveau si l'analyse est toujours insuffisante
            non_empty_fields = sum(1 for value in synthesized_info.dict().values() if value)
            if non_empty_fields < 5:
                print(f"{Fore.RED}L'analyse reste insuffisante même après utilisation des informations brutes. Abandon du traitement pour : {title}")
                return None

            # Save the synthesized information to the analyses.md file
            md_filename = 'analyses.md'
            os.makedirs('analyses', exist_ok=True)
            
            with open(md_filename, 'a', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                for key, value in synthesized_info.dict().items():
                    if value:  # N'écrit que les champs non vides
                        f.write(f"## {key}\n{value}\n\n")
                f.write("---\n\n")  # Séparateur entre les analyses
            
            print(f"{Fore.GREEN}Analyse ajoutée à : {md_filename}")
            
            # Add the analysis to the current chat session
            analysis_content = f"# {title}\n\n"
            for key, value in synthesized_info.dict().items():
                if value:
                    analysis_content += f"## {key}\n{value}\n\n"
            
            self.io.tool_output(f"Nouvelle analyse ajoutée au chat et à {md_filename}")
            self.io.append_chat_history(analysis_content, linebreak=True)
            
            print(f"{Fore.GREEN}Extraction et synthèse terminées pour : {title}")
            print(f"{Fore.CYAN}Contenu de l'analyse :\n{analysis_content[:500]}...")  # Affiche les 500 premiers caractères

            return synthesized_info
        except Exception as e:
            print(f"{Fore.RED}Erreur générale lors de l'extraction et de la synthèse des informations : {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            print(f"{Fore.CYAN}Fin du traitement pour : {title}")

def extract_pdf_info(pdf_content, url, title, io):
    extractor = StudyExtractor(io)
    return extractor.extract_and_save_pdf_info(pdf_content, url, title)

def clean_orphan_files():
    print(f"{Fore.CYAN}Nettoyage des fichiers orphelins...")
    etudes_dir = 'etudes'
    
    # Obtenir la liste des fichiers PDF dans le dossier 'etudes'
    pdf_files = set(f[:-4] for f in os.listdir(etudes_dir) if f.endswith('.pdf'))
    
    # Obtenir la liste des analyses dans le fichier analyses.md
    analyses = set()
    if os.path.exists('analyses.md'):
        with open('analyses.md', 'r', encoding='utf-8') as f:
            content = f.read()
            analyses = set(re.findall(r'# (.+)', content))
    
    # Trouver les fichiers orphelins
    orphan_pdfs = pdf_files - analyses
    
    # Supprimer les fichiers orphelins
    for orphan in orphan_pdfs:
        os.remove(os.path.join(etudes_dir, f"{orphan}.pdf"))
        print(f"{Fore.YELLOW}Suppression du PDF orphelin : {orphan}.pdf")
    
    print(f"{Fore.GREEN}Nettoyage terminé.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharger ou analyser des articles scientifiques.")
    parser.add_argument("query", nargs="?", help="La requête de recherche pour télécharger des articles")
    parser.add_argument("-n", "--num_articles", type=int, default=20, help="Nombre d'articles à télécharger (max 100)")
    parser.add_argument("-o", "--output", default="etudes", help="Dossier de sortie pour les PDFs")
    parser.add_argument("--analyze-all", action="store_true", help="Analyser tous les PDFs dans le dossier de sortie")
    parser.add_argument("--model", default="gpt-4o-mini", help="Modèle GPT à utiliser pour l'analyse (par défaut: gpt-4o-mini)")
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS, help=f"Nombre maximum de workers pour le ThreadPoolExecutor (par défaut: {DEFAULT_MAX_WORKERS})")
    parser.add_argument("--no-immediate-analysis", action="store_true", help="Désactiver l'analyse immédiate après le téléchargement")
    parser.add_argument("--clean", action="store_true", help="Nettoyer les fichiers orphelins")
    args = parser.parse_args()

    io = InputOutput()

    if args.clean:
        clean_orphan_files()

    if args.query:
        num_articles = min(100, max(1, args.num_articles))  # Limiter entre 1 et 100
        get_studies_from_query(args.query, num_articles, args.output, max_workers=args.max_workers, analyze_immediately=not args.no_immediate_analysis)

    if args.analyze_all:
        run_all_analysis(io, model=args.model)
import requests
from bs4 import BeautifulSoup


def get_studies_from_query(query):
    """
    Fonction pour récupérer les études à partir d'une requête.

    Args:
    query (str): La requête de recherche.

    Returns:
    list: Une liste de dictionnaires contenant les informations des études.
    """
    # URL de base pour la recherche PubMed
    base_url = "https://pubmed.ncbi.nlm.nih.gov/"

    # Effectuer la requête
    response = requests.get(f"{base_url}?term={query}")

    # Vérifier si la requête a réussi
    if response.status_code != 200:
        print(f"Erreur lors de la requête : {response.status_code}")
        return []

    # Parser le contenu HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # Trouver tous les articles
    articles = soup.find_all('article', class_='full-docsum')

    # Liste pour stocker les informations des études
    studies = []

    # Extraire les informations de chaque article
    for article in articles:
        title = article.find('a', class_='docsum-title').text.strip()
        authors = article.find('span', class_='full-authors').text.strip()
        citation = article.find('span', class_='citation-part').text.strip()

        studies.append({
            'title': title,
            'authors': authors,
            'citation': citation
        })

    return studies
