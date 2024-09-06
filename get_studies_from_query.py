import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Vérification de la clé API
if not os.getenv('SEARCHAPI_KEY'):
    print("Erreur : La clé SEARCHAPI_KEY n'a pas été trouvée dans le fichier .env")
    exit(1)

def get_studies_from_query(query):
    # Fonction pour faire une requête à Google Scholar
    def google_scholar_request(query):
        url = "https://www.searchapi.io/api/v1/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('SEARCHAPI_KEY')}",
            "Content-Type": "application/json"
        }
        params = {
            "engine": "google_scholar",
            "q": query,
            "num": 40,
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
        print(f"Contenu de la réponse PDF: {response.text}")
        return response.json()

    # Obtenir les résultats de Google Scholar
    scholar_results = google_scholar_request(query)

    if scholar_results is None:
        print("Impossible d'obtenir les résultats de Google Scholar. Vérifiez votre clé API et la connexion internet.")
        return

    # Traiter chaque résultat
    for result in scholar_results.get('organic_results', []):
        url = result.get('link')
        title = result.get('title')
        
        # Essayer d'abord de télécharger directement le PDF
        pdf_content = download_pdf(url) if url else None
        
        if pdf_content:
            # Créer le dossier 'etudes' s'il n'existe pas
            os.makedirs('etudes', exist_ok=True)
            
            # Sauvegarder le PDF
            filename = f"etudes/{title.replace(' ', '_')[:50]}.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_content)
            print(f"PDF sauvegardé : {filename}")
        else:
            # Si le téléchargement direct échoue, essayer avec openaccessbutton
            pdf_result = get_pdf_openaccessbutton(url) if url else None
            if not pdf_result or 'data' not in pdf_result:
                pdf_result = get_pdf_openaccessbutton(title)

            if pdf_result and 'data' in pdf_result:
                doi = pdf_result['data'].get('doi')
                if doi:
                    # Créer le dossier 'etudes' s'il n'existe pas
                    os.makedirs('etudes', exist_ok=True)
                    
                    # Sauvegarder le résultat dans un fichier
                    filename = f"etudes/{doi.replace('/', '_')}.json"
                    with open(filename, 'w') as f:
                        json.dump(pdf_result, f, indent=2)
                    print(f"Sauvegardé : {filename}")
                else:
                    print(f"Pas de DOI trouvé pour : {title}")
            else:
                print(f"Pas de PDF trouvé pour : {title}")

if __name__ == "__main__":
    query = input("Entrez votre requête de recherche : ")
    get_studies_from_query(query)
