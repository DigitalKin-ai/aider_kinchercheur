import json
import os
from openai import OpenAI
import requests
from tqdm import tqdm
from dotenv import load_dotenv

def compter_etudes_lues():
    dossier_etudes = "etudes"  # Assurez-vous que ce chemin est correct
    fichiers_etudes = os.listdir(dossier_etudes)
    return len(fichiers_etudes)

def lire_etat_de_lart(fichier):
    print(f"Lecture du fichier '{fichier}'...")
    with open(fichier, 'r', encoding='utf-8') as f:
        contenu = f.read()
    print(f"Fichier '{fichier}' lu avec succès.")
    return contenu

def extraire_references(contenu):
    print("Extraction des références à l'aide de GPT...")
    load_dotenv()  # Charge les variables d'environnement depuis le fichier .env
    client = OpenAI()
    if not client.api_key:
        raise ValueError("La clé API OpenAI n'est pas définie dans le fichier .env. Veuillez ajouter OPENAI_API_KEY à votre fichier .env.")
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Vous êtes un assistant chargé d'extraire des références à partir d'un document d'état de l'art."},
            {"role": "user", "content": f"Extrayez toutes les références du texte suivant et retournez-les sous forme de liste JSON : \n\n{contenu}"}
        ]
    )
    
    references = json.loads(response.choices[0].message.content)
    print(f"{len(references)} références extraites.")
    return references

def verifier_presence_dans_analyses(reference):
    dossier_analyses = "analyses"  # Assurez-vous que ce chemin est correct
    fichiers_analyses = os.listdir(dossier_analyses)
    
    for fichier in fichiers_analyses:
        nom_fichier, _ = os.path.splitext(fichier)
        if nom_fichier.lower() in reference.lower():
            contenu = lire_fichier(os.path.join(dossier_analyses, fichier))
            return verifier_presence_gpt(reference, contenu)
    
    return False

def verifier_presence_dans_etudes(reference):
    dossier_etudes = "etudes"  # Assurez-vous que ce chemin est correct
    fichiers_etudes = os.listdir(dossier_etudes)
    
    for fichier in fichiers_etudes:
        nom_fichier, _ = os.path.splitext(fichier)
        if nom_fichier.lower() in reference.lower():
            contenu = lire_fichier(os.path.join(dossier_etudes, fichier))
            return verifier_presence_gpt(reference, contenu)
    
    return False

def lire_fichier(chemin_fichier):
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        return f.read()

def verifier_presence_gpt(reference, contenu):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Vous êtes un assistant chargé de vérifier si une référence est présente dans un texte."},
            {"role": "user", "content": f"La référence suivante est-elle présente dans le texte ? Répondez par 'true' ou 'false'.\n\nRéférence : {reference}\n\nTexte : {contenu[:2000]}"}  # Limite de 2000 caractères pour éviter de dépasser les limites de l'API
        ]
    )
    
    reponse = response.choices[0].message.content.strip().lower()
    return reponse == 'true'

def verifier_lien(lien):
    try:
        response = requests.head(lien, allow_redirects=True, timeout=5)
        return response.status_code != 404
    except requests.RequestException:
        return False

def main(fichier_etat_de_lart):
    nombre_etudes_lues = compter_etudes_lues()
    if nombre_etudes_lues < 10:
        print(f"Attention : Seulement {nombre_etudes_lues} études ont été lues. Il est recommandé d'en lire au moins 10.")
    else:
        print(f"{nombre_etudes_lues} études ont été lues, ce qui est suffisant.")

    contenu = lire_etat_de_lart(fichier_etat_de_lart)
    references = extraire_references(contenu)
    
    resultats = []
    
    print("Vérification des références...")
    for reference in tqdm(references, desc="Progression", unit="référence"):
        dans_analyses = verifier_presence_dans_analyses(reference["texte"])
        dans_etudes = verifier_presence_dans_etudes(reference["texte"])
        lien_valide = verifier_lien(reference["lien"])
        
        resultats.append({
            "reference": reference["texte"],
            "lien": reference["lien"],
            "dans_analyses": dans_analyses,
            "dans_etudes": dans_etudes,
            "lien_valide": lien_valide
        })
    
    # Écriture des résultats dans un fichier JSON
    nom_fichier_sortie = os.path.splitext(fichier_etat_de_lart)[0] + "-verification.json"
    print(f"Écriture des résultats dans '{nom_fichier_sortie}'...")
    with open(nom_fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, ensure_ascii=False, indent=4)
    print(f"Résultats écrits dans '{nom_fichier_sortie}'.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python verification.py <chemin_vers_etat_de_lart.md>")
        sys.exit(1)
    fichier_etat_de_lart = sys.argv[1]
    main(fichier_etat_de_lart)
