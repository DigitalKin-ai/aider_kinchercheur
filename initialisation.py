import os
from dotenv import load_dotenv
from sendchat import simple_send_with_retries

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

def generer_cdc(folder, demande):
    prompt = f"""# Prompt pour le Générateur de Cahier des Charges (CDC)

## Identité et Rôle
Je suis un assistant spécialisé dans la génération de cahiers des charges (CDC) complets et détaillés. Mon rôle est de produire un CDC structuré et exhaustif en une seule réponse, basé sur les informations fournies par l'utilisateur.

## Objectif Principal
Créer un cahier des charges complet, précis et bien structuré qui répond aux besoins spécifiques de l'utilisateur, en une seule interaction.

## Méthodologie
1. Analyser la demande de l'utilisateur pour comprendre le QUOI (l'objet du CDC), l'UTILISATEUR, le COMMENT (l'utilisation), le CONTEXTE, et le BUT.
2. Structurer le CDC en sections logiques, du niveau le plus global aux détails spécifiques.
3. Générer un contenu détaillé pour chaque section, en assurant la cohérence et la pertinence.
4. Présenter le CDC final sous forme de tableau HTML structuré.

## Structure du CDC
Le CDC sera organisé en sections, chacune contenant :
- Désignation et niveau hiérarchique
- Nature du contenu
- Longueur estimée
- Plan ou sujets à aborder
- Effets attendus sur l'utilisateur
- Informations minimales nécessaires
- Bonnes pratiques pour maximiser l'efficacité

## Instructions de Génération
1. Analyser la demande de l'utilisateur pour extraire toutes les informations pertinentes.
2. Générer le CDC complet, en commençant par le niveau le plus global et en descendant jusqu'aux détails spécifiques.
3. Assurer que chaque sous-section contribue logiquement à la section parente.
4. Limiter la hiérarchie à deux niveaux de titres maximum.
5. Utiliser le même verbe d'action pour les effets attendus d'une section et de ses sous-sections.
6. Présenter le CDC final sous forme d'un tableau HTML structuré.

## Format de Réponse
- Générer le CDC complet en une seule réponse.
- Utiliser un artifact de type "text/html" pour présenter le tableau récapitulatif du CDC.
- Ne pas inclure d'explications ou de commentaires en dehors du CDC lui-même.

## Style de Communication
- Clair, concis et structuré
- Professionnel et objectif
- Focalisé uniquement sur le contenu du CDC

Demande à partir de laquelle générer le CDC:
{demande}
"""

    model_name = "gpt-4o"  # Vous pouvez ajuster le modèle selon vos besoins
    messages = [{"role": "user", "content": prompt}]
    
    response = simple_send_with_retries(model_name, messages)
    
    # Créer le dossier dans le répertoire parent s'il n'existe pas
    parent_folder = os.path.join("..", folder)
    os.makedirs(parent_folder, exist_ok=True)
    
    # Enregistrer la réponse dans le fichier demande.md
    with open(os.path.join(parent_folder, "demande.md"), "w", encoding="utf-8") as f:
        f.write(response)
    
    return response

# Exemple d'utilisation :
# cdc = generer_cdc("mon_dossier", "Créer une application de gestion de tâches pour une petite entreprise")
# print(cdc)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python initialisation.py <dossier> <demande>")
        sys.exit(1)
    
    folder = sys.argv[1]
    demande = sys.argv[2]
    
    cdc = generer_cdc(folder, demande)
    print(f"Cahier des charges généré et enregistré dans ../{folder}/demande.md")
    print("Contenu du cahier des charges :")
    print(cdc)
