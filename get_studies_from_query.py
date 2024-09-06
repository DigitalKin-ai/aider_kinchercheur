import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def get_studies_from_query(query):
    # Fonction pour faire une requête à Google Scholar
    def google_scholar_request(query):
        url = "https://www.searchapi.io/api/v1/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('SEARCHAPI_TOKEN')}",
            "Content-Type": "application/json"
        }
        payload = {
            "engine": "google_scholar",
            "q": query,
            "num": 40,
            "time_period_min": 2010
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    # Fonction pour obtenir le PDF d'une étude
    def get_pdf(id):
        url = f"https://api.openaccessbutton.org/find?id={id}"
        response = requests.get(url)
        return response.json()

    # Obtenir les résultats de Google Scholar
    scholar_results = google_scholar_request(query)

    # Traiter chaque résultat
    for result in scholar_results.get('organic_results', []):
        url = result.get('link')
        title = result.get('title')
        
        # Essayer d'abord avec l'URL, puis avec le titre
        pdf_result = get_pdf(url) if url else None
        if not pdf_result or 'data' not in pdf_result:
            pdf_result = get_pdf(title)

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
