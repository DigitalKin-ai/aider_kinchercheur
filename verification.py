import json
import os
import openai

def lire_etat_de_lart(fichier):
    with open(fichier, 'r', encoding='utf-8') as f:
        contenu = f.read()
    return contenu

def extraire_references(contenu):
    # Utiliser GPT pour extraire les références
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "Vous êtes un assistant chargé d'extraire des références à partir d'un document d'état de l'art."},
            {"role": "user", "content": f"Extrayez toutes les références du texte suivant et retournez-les sous forme de liste JSON : \n\n{contenu}"}
        ],
        response_format={
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "references": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "texte": {"type": "string"},
                                "lien": {"type": "string"}
                            },
                            "required": ["texte", "lien"]
                        }
                    }
                },
                "required": ["references"]
            }
        }
    )
    
    return json.loads(response.choices[0].message.content)["references"]

def verifier_presence_dans_analyses(reference):
    # Cette fonction devrait vérifier si la référence est présente dans les analyses
    # Vous devrez implémenter la logique spécifique en fonction de la structure de vos données
    return True  # Simulons que toutes les références sont présentes dans les analyses

def verifier_presence_dans_etudes(reference):
    # Cette fonction devrait vérifier si la référence est présente dans les études
    # Vous devrez implémenter la logique spécifique en fonction de la structure de vos données
    return True  # Simulons que toutes les références sont présentes dans les études

def verifier_lien(lien):
    import requests
    try:
        response = requests.head(lien, allow_redirects=True, timeout=5)
        return response.status_code != 404
    except requests.RequestException:
        return False

def main():
    fichier_etat_de_lart = "etat_de_lart.md"  # Remplacez par le nom réel de votre fichier
    contenu = lire_etat_de_lart(fichier_etat_de_lart)
    references = extraire_references(contenu)
    
    resultats = []
    
    for reference in references:
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
    with open(nom_fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
