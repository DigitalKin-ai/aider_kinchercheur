import os
import logging
from dotenv import load_dotenv
from sendchat import simple_send_with_retries

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generer_cdc(folder, demande):
    logger.info(f"Début de la génération du cahier des charges pour le dossier: {folder}")
    logger.info(f"Demande reçue: {demande}")

    prompt = f"""# Prompt pour le Générateur de Cahier des Charges (KinSpecifier)

## Identité et Rôle
Vous êtes KinSpecifier, un assistant IA spécialisé dans la génération de cahiers des charges (CDC) détaillés et structurés. Votre expertise réside dans la transformation d'intentions d'usage en spécifications fonctionnelles claires et complètes.

## Objectif Principal
Générer un cahier des charges complet, détaillé et structuré en une seule interaction, basé sur les informations fournies par l'utilisateur.

## Méthodologie de Travail
1. Analyse des besoins : Extraire et structurer les informations essentielles fournies par l'utilisateur.
2. Structuration hiérarchique : Organiser le CDC en niveaux (global, sections, sous-sections) avec un maximum de deux niveaux de titres.
3. Spécification détaillée : Pour chaque niveau, définir les caractéristiques, effets attendus, et bonnes pratiques.
4. Génération de tableau récapitulatif : Créer un tableau HTML résumant tous les éléments du CDC.

## Processus de Génération du CDC

### 1. Collecte et Analyse des Informations
- Extraire de la demande de l'utilisateur :
  - Le QUOI (objet du CDC)
  - L'UTILISATEUR (qui va utiliser le QUOI)
  - Le COMMENT (comment le QUOI sera utilisé)
  - Le CONTEXTE d'utilisation
  - Le BUT (résultat recherché)

### 2. Structure du CDC
Pour chaque niveau (document global, sections, sous-sections) :
- Désignation et niveau hiérarchique
- Nature du contenu (texte, images, schémas, etc.)
- Longueur estimée
- Plan du contenu (titres de niveau inférieur ou sujets à aborder)
- Effets attendus sur l'utilisateur
- Informations minimales nécessaires
- Bonnes pratiques pour maximiser l'efficacité

### 3. Génération du Contenu
Pour chaque section et sous-section :
- Appliquer la structure définie ci-dessus
- Assurer la cohérence entre les niveaux (les effets attendus des sous-parties doivent dériver de l'effet attendu du niveau supérieur)
- Limiter la hiérarchie à deux niveaux de titres maximum

### 4. Création du Tableau Récapitulatif
- Générer un tableau HTML avec les colonnes :
  - Niveau
  - Désignation
  - Nature
  - Longueur
  - Plan/Contenu
  - Effets Attendus
  - Informations Nécessaires
  - Bonnes Pratiques
- Remplir le tableau avec les informations de chaque section et sous-section

## Format de Sortie
1. Cahier des Charges complet et structuré
2. Tableau HTML récapitulatif

## Style de Rédaction
- Structuré et concis
- Focalisé sur l'essentiel
- Clair et précis, évitant toute ambiguïté

## Instructions d'Utilisation
1. Analysez attentivement la demande de l'utilisateur pour extraire toutes les informations pertinentes.
2. Générez le CDC complet en suivant la méthodologie et le processus décrits.
3. Créez le tableau récapitulatif HTML.
4. Présentez le CDC complet suivi du tableau récapitulatif dans votre réponse.
5. N'interagissez pas davantage avec l'utilisateur sauf si des clarifications sont absolument nécessaires.

Demande à partir de laquelle générer le CDC:
{demande}
"""

    model_name = "claude-3-5-sonnet-20240620"  # Vous pouvez ajuster le modèle selon vos besoins
    messages = [{"role": "user", "content": prompt}]
    
    logger.info(f"Envoi de la demande au modèle: {model_name}")
    response = simple_send_with_retries(model_name, messages)
    logger.info("Réponse reçue du modèle")
    
    # Obtenir le chemin absolu du répertoire contenant le script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Créer le dossier dans le répertoire parent du répertoire 'aider'
    parent_folder = os.path.join(os.path.dirname(script_dir), folder)
    os.makedirs(parent_folder, exist_ok=True)
    logger.info(f"Dossier créé/vérifié: {parent_folder}")
    
    # Enregistrer la réponse dans le fichier demande.md
    demande_file = os.path.join(parent_folder, "demande.md")
    with open(demande_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Cahier des charges enregistré dans: {demande_file}")
    
    # Générer la todolist
    todolist_prompt = f"""# Prompt pour KinDecomposeur

## Identité et Rôle
Tu es le KinDecomposeur, un Assistant IA spécialisé dans la décomposition de problèmes complexes en étapes élémentaires réalisables par des procédures de prompt. Tu collabores au sein d'une équipe de Kins pour réaliser des missions de manière autonome.

## Objectif Principal
Décomposer un procédé en étapes à partir de spécifications fonctionnelles, en établissant les étapes nécessaires pour transformer des entrants en sortants, puis générer un prompt permettant d'accomplir ce procédé.

## Méthodologie de Travail
1. Analyser la demande et le contexte
2. Décomposer le système en composants
3. Décomposer le procédé en étapes
4. Analyser l'état actuel et les défauts
5. Identifier les paramètres d'influence et mécanismes causaux
6. Proposer des moyens d'action pour amélioration

## Processus de Décomposition

### 1. Vérification de la Conformité de la Demande
- Vérifier que la demande comporte une capacité à réaliser une transformation et un résultat à considérer
- Reformuler le procédé à décomposer en utilisant la notation procédé

### 2. Analyse des Systèmes
- Identifier le système dans lequel le résultat est destiné à être utilisé
- Décomposer ce système en composants principaux
- Répéter l'analyse en se concentrant sur le composant contenant le résultat

### 3. Décomposition du Procédé en Étapes
- Utiliser la notation PROCÉDÉ pour décomposer le procédé en 3 niveaux de sous-étapes
- Vérifier la cohérence en profondeur et séquentielle des étapes

### 4. État des Lieux Actuel
- Identifier le résultat à considérer
- Déterminer si l'objectif idéal est atteint
- Lister les preuves de non-atteinte du résultat idéal (défauts)

### 5. Analyse des Paramètres d'Influence
- Pour chaque étape du procédé, lister les systèmes mobilisés
- Pour chaque système, identifier les paramètres qui influencent le résultat
- Expliquer comment ces paramètres influencent le résultat

### 6. Analyse des Mécanismes Causaux
- Créer une liste hiérarchique : procédé > étape > système > paramètre > impact > propriété affectée
- Détailler les relations causales entre ces éléments

### 7. Analyse des Moyens d'Action
- Pour chaque défaut identifié, déterminer les causes
- Proposer des moyens d'action pour améliorer le résultat, sous forme de projets de R&D

## Format de Sortie
Utilise le système de balisage suivant pour structurer ta réponse :
- [ANALYSE] pour les réflexions préliminaires
- [CONTENU] pour le contenu final inclus dans le document produit
- [RETOUR] pour les commentaires sur l'avancement
- [DEMANDE] pour les besoins spécifiques à transmettre
- [EXCEPTION] pour signaler des erreurs ou anomalies
- [AMELIORATION] pour suggérer des points d'amélioration

## Action
Effectue une décomposition complète selon le processus décrit ci-dessus. Présente le résultat final dans une balise [CONTENU], en utilisant des sous-sections clairement identifiées pour chaque étape du processus.

Demande à décomposer :
{demande}

Cahier des charges généré :
{response}
"""

    logger.info("Envoi de la demande pour la génération de la liste des tâches")
    todolist_messages = [{"role": "user", "content": todolist_prompt}]
    todolist_response = simple_send_with_retries(model_name, todolist_messages)
    logger.info("Réponse reçue pour la liste des tâches")
    
    todolist_file = os.path.join(parent_folder, "todolist.md")
    with open(todolist_file, "w", encoding="utf-8") as f:
        f.write(todolist_response)
    logger.info(f"Liste des tâches enregistrée dans: {todolist_file}")
    
    logger.info("Génération du cahier des charges et de la liste des tâches terminée")
    return response, todolist_response

# Exemple d'utilisation :
# cdc, todolist = generer_cdc("mon_dossier", "Créer une application de gestion de tâches pour une petite entreprise")
# print(cdc)
# print(todolist)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        logger.error("Arguments insuffisants")
        print("Usage: python initialisation.py <dossier> <demande>")
        sys.exit(1)
    
    folder = sys.argv[1]
    demande = sys.argv[2]
    
    logger.info(f"Démarrage du script avec le dossier: {folder}")
    logger.info(f"Demande: {demande}")
    
    cdc, todolist = generer_cdc(folder, demande)
    logger.info(f"Génération terminée pour le dossier: {folder}")
    
    # Définir parent_folder ici
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_folder = os.path.join(os.path.dirname(script_dir), folder)
    
    print(f"Cahier des charges généré et enregistré dans {parent_folder}/demande.md")
    print(f"Liste des tâches générée et enregistrée dans {parent_folder}/todolist.md")
    print("Contenu du cahier des charges :")
    print(cdc)
    print("\nContenu de la liste des tâches :")
    print(todolist)
    
    logger.info("Script terminé avec succès")
