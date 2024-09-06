import json
import requests
from bs4 import BeautifulSoup
import os
import openai

def lire_etat_de_lart(fichier):
    with open(fichier, 'r', encoding='utf-8') as f:
        contenu = f.read()
    return contenu

def extraire_references(contenu):
    # Cette fonction devrait être implémentée pour extraire les références du contenu
    # Vous pourriez utiliser une bibliothèque comme BeautifulSoup si le contenu est en HTML
    # ou une expression régulière si le format est cohérent
    # Pour l'instant, nous allons simuler quelques références
    return ["Référence 1", "Référence 2", "Référence 3"]

def verifier_presence_dans_analyses(reference):
    # Cette fonction devrait vérifier si la référence est présente dans les analyses
    # Vous devrez implémenter la logique spécifique en fonction de la structure de vos données
    return True  # Simulons que toutes les références sont présentes dans les analyses

def verifier_presence_dans_etudes(reference):
    # Cette fonction devrait vérifier si la référence est présente dans les études
    # Vous devrez implémenter la logique spécifique en fonction de la structure de vos données
    return True  # Simulons que toutes les références sont présentes dans les études

def verifier_lien(reference):
    # Cette fonction devrait extraire le lien de la référence et vérifier s'il renvoie un code 404
    # Pour l'instant, simulons que tous les liens sont valides
    return True

def appel_gpt(prompt):
    # Assurez-vous d'avoir configuré votre clé API OpenAI
    openai.api_key = 'votre-clé-api-ici'
    
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=100
    )
    
    return response.choices[0].text.strip()

def main():
    fichier_etat_de_lart = "etat_de_lart.md"  # Remplacez par le nom réel de votre fichier
    contenu = lire_etat_de_lart(fichier_etat_de_lart)
    references = extraire_references(contenu)
    
    resultats = []
    
    for reference in references:
        dans_analyses = verifier_presence_dans_analyses(reference)
        dans_etudes = verifier_presence_dans_etudes(reference)
        lien_valide = verifier_lien(reference)
        
        # Utilisons GPT pour analyser la référence
        prompt = f"Analysez la référence suivante et dites-moi si elle semble pertinente : {reference}"
        analyse_gpt = appel_gpt(prompt)
        
        resultats.append({
            "reference": reference,
            "dans_analyses": dans_analyses,
            "dans_etudes": dans_etudes,
            "lien_valide": lien_valide,
            "analyse_gpt": analyse_gpt
        })
    
    # Écriture des résultats dans un fichier JSON
    nom_fichier_sortie = os.path.splitext(fichier_etat_de_lart)[0] + "-verification.json"
    with open(nom_fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
