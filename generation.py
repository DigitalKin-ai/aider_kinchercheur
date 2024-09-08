import os
import logging
from dotenv import load_dotenv
from .sendchat import simple_send_with_retries

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generer_cdc(folder_path, demande):
    logger.info(f"Début de la génération du cahier des charges pour le dossier: {folder_path}")
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
    
    # S'assurer que le dossier existe
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Dossier créé: {folder_path}")
    else:
        logger.info(f"Dossier existant: {folder_path}")
    
    # Enregistrer la réponse dans le fichier cdc.md
    cdc_file = os.path.join(folder_path, "cdc.md")
    with open(cdc_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Cahier des charges enregistré dans: {cdc_file}")
    
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

Chemins des fichiers :
- Cahier des charges : {os.path.join(folder_path, 'cdc.md')}
- Liste des tâches : {os.path.join(folder_path, 'todolist.md')}
"""

    logger.info("Envoi de la demande pour la génération de la liste des tâches")
    todolist_messages = [{"role": "user", "content": todolist_prompt}]
    todolist_response = simple_send_with_retries(model_name, todolist_messages)
    logger.info("Réponse reçue pour la liste des tâches")
    
    todolist_file = os.path.join(folder_path, "todolist.md")
    with open(todolist_file, "w", encoding="utf-8") as f:
        f.write(todolist_response)
    logger.info(f"Liste des tâches enregistrée dans: {todolist_file}")
    
    logger.info("Génération du cahier des charges et de la liste des tâches terminée")

    # Génération du prompt optimisé
    prompt_prompt = f"""# Prompt pour KinPromptGenerator

## Identité et Rôle
Vous êtes KinPromptGenerator, un assistant IA spécialisé dans la création de prompts optimisés. Votre rôle est de générer un prompt détaillé et structuré qui permettra à un autre assistant IA d'accomplir une tâche spécifique selon les spécifications et le processus définis.

## Objectif Principal
Créer un prompt complet et efficace qui guidera un assistant IA dans l'exécution des étapes nécessaires pour atteindre les objectifs spécifiés dans le cahier des charges, en suivant le processus détaillé dans la todolist.

## Méthodologie de Travail
1. Analyser le cahier des charges et la todolist
2. Extraire les informations clés et les étapes du processus
3. Structurer le prompt de manière logique et séquentielle
4. Inclure des instructions précises pour chaque étape du processus
5. Optimiser le prompt pour la clarté et l'efficacité

## Processus de Génération du Prompt

### 1. Analyse des Documents
- Examiner attentivement le cahier des charges et la todolist
- Identifier les objectifs principaux, les contraintes et les critères de succès
- Repérer les étapes clés du processus à suivre

### 2. Structuration du Prompt
- Créer une introduction claire définissant le rôle et l'objectif de l'assistant
- Organiser les instructions en sections correspondant aux étapes principales du processus
- Inclure des sous-sections pour les détails spécifiques de chaque étape

### 3. Formulation des Instructions
- Rédiger des instructions claires et précises pour chaque étape du processus
- Inclure des directives sur la manière d'utiliser les informations du cahier des charges
- Spécifier les formats de sortie attendus pour chaque étape

### 4. Optimisation du Prompt
- Vérifier la cohérence entre les instructions et les objectifs du cahier des charges
- S'assurer que toutes les étapes de la todolist sont couvertes
- Ajouter des conseils pour gérer les cas particuliers ou les difficultés potentielles

### 5. Finalisation
- Inclure des instructions pour la vérification et la validation du résultat final
- Ajouter des directives pour la présentation et le format du livrable final

## Format de Sortie
Le prompt généré doit suivre cette structure :
1. Introduction et contexte
2. Objectif principal
3. Instructions étape par étape
4. Directives pour la vérification et la validation
5. Format de présentation du résultat final

## Style de Rédaction
- Clair, concis et sans ambiguïté
- Utilisation d'un langage directif et précis
- Inclusion d'exemples ou d'explications si nécessaire

## Instructions d'Utilisation
1. Lisez attentivement le cahier des charges et la todolist fournis.
2. Générez un prompt complet en suivant la méthodologie et le processus décrits.
3. Assurez-vous que le prompt couvre tous les aspects nécessaires pour atteindre les objectifs spécifiés.
4. Présentez le prompt généré dans votre réponse, en utilisant une structure claire et des sections bien définies.

Demande initiale :
{demande}

Cahier des charges à respecter :
{response}

Todolist à implémenter:
{todolist_response}

Veuillez générer un prompt optimisé basé sur ces informations.
"""

    logger.info("Envoi de la demande pour la génération du prompt")
    prompt_messages = [{"role": "user", "content": prompt_prompt}]
    prompt_response = simple_send_with_retries(model_name, prompt_messages)
    logger.info("Réponse reçue pour le prompt optimisé")
    
    prompt_file = os.path.join(folder_path, "prompt.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_response)
    logger.info(f"Prompt optimisé enregistré dans: {prompt_file}")
    
    logger.info("Génération du cahier des charges, de la liste des tâches et du prompt optimisé terminée")
    
    # Log du prompt de la boucle
    loop_prompt = f"""
    Contexte de la demande initiale {folder_path}/demande.md :
    {demande}

    Cahier des charges global (niveau 0) {folder_path}/cdc.md :
    {response}

    Liste des tâches à réaliser {folder_path}/todolist.md:
    {todolist_response}

    Prompt Général {folder_path}/prompt.md:
    {prompt_response}

    Pour chaque étape du processus détaillé, applique le processus suivant:
    1. Crée un fichier prompt.md dans une arborescence miroir des étapes présentées dans {folder_path}/todolist.md. Ce fichier doit contenir le prompt pour exécuter l'étape en question.
    2. Si l'étape est trop complexe pour un seul prompt, crée un sous-dossier avec des sous-étapes
    3. Exécute l'étape en suivant le prompt créé. Assure-toi de vraiment réaliser le travail nécessaire à la completion de l'étape.
    4. Vérifie que le travail effectué remplit les critères du CDC pour l'étape (dans {folder_path}
    5. Si les critères ne sont pas remplis, recommence l'étape ou décompose-la en sous-étapes
    6. Une fois les critères remplis, mets à jour le statut de l'étape dans {folder_path}/todolist.md
    7. Répète ce processus jusqu'à ce que tous les critères du CDC global (niveau 0) soient remplis
    """
    logger.info("Prompt de la boucle généré:")
    logger.info(loop_prompt)

    return response, todolist_response, prompt_response

# Exemple d'utilisation :
# cdc, todolist, prompt = generer_cdc("mon_dossier", "Créer une application de gestion de tâches pour une petite entreprise")
# print(cdc)
# print(todolist)
# print(prompt)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        logger.error("Arguments insuffisants")
        print("Usage: python generation.py <dossier> <demande>")
        sys.exit(1)
    
    folder = sys.argv[1]
    demande = sys.argv[2]
    
    logger.info(f"Démarrage du script avec le dossier: {folder}")
    logger.info(f"Demande: {demande}")
    
    # Définir folder_path ici
    folder_path = os.path.abspath(folder)
    
    cdc, todolist, prompt = generer_cdc(folder_path, demande)
    logger.info(f"Génération terminée pour le dossier: {folder_path}")
    
    print(f"Cahier des charges généré et enregistré dans {os.path.join(folder_path, 'cdc.md')}")
    print(f"Liste des tâches générée et enregistrée dans {os.path.join(folder_path, 'todolist.md')}")
    print(f"Prompt optimisé généré et enregistré dans {os.path.join(folder_path, 'prompt.md')}")
    print("Contenu du cahier des charges :")
    print(cdc)
    print("\nContenu de la liste des tâches :")
    print(todolist)
    print("\nContenu du prompt optimisé :")
    print(prompt)
    
    logger.info("Script terminé avec succès")
import os
import logging
from dotenv import load_dotenv
from .sendchat import simple_send_with_retries

# Load environment variables from the .env file
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_specifications(folder_path, request):
    logger.info(f"Starting the generation of specifications for the folder: {folder_path}")
    logger.info(f"Received request: {request}")

    prompt = f"""# Prompt for the Specifications Generator (KinSpecifier)

## Identity and Role
You are KinSpecifier, an AI assistant specialized in generating detailed and structured specifications. Your expertise lies in transforming usage intentions into clear and complete functional specifications.

## Main Objective
Generate a complete, detailed, and structured specification document in a single interaction, based on the information provided by the user.

## Work Methodology
1. Needs analysis: Extract and structure essential information provided by the user.
2. Hierarchical structuring: Organize the specifications into levels (global, sections, subsections) with a maximum of two title levels.
3. Detailed specification: For each level, define characteristics, expected effects, and best practices.
4. Summary table generation: Create an HTML table summarizing all elements of the specifications.

## Specifications Generation Process

### 1. Information Collection and Analysis
- Extract from the user's request:
  - The WHAT (subject of the specifications)
  - The USER (who will use the WHAT)
  - The HOW (how the WHAT will be used)
  - The CONTEXT of use
  - The GOAL (desired result)

### 2. Specifications Structure
For each level (global document, sections, subsections):
- Designation and hierarchical level
- Content nature (text, images, diagrams, etc.)
- Estimated length
- Content plan (lower level titles or topics to cover)
- Expected effects on the user
- Minimum necessary information
- Best practices to maximize efficiency

### 3. Content Generation
For each section and subsection:
- Apply the structure defined above
- Ensure consistency between levels (expected effects of sub-parts should derive from the expected effect of the higher level)
- Limit the hierarchy to a maximum of two title levels

### 4. Summary Table Creation
- Generate an HTML table with columns:
  - Level
  - Designation
  - Nature
  - Length
  - Plan/Content
  - Expected Effects
  - Necessary Information
  - Best Practices
- Fill the table with information from each section and subsection

## Output Format
1. Complete and structured Specifications
2. HTML summary table

## Writing Style
- Structured and concise
- Focused on the essential
- Clear and precise, avoiding any ambiguity

## Usage Instructions
1. Carefully analyze the user's request to extract all relevant information.
2. Generate the complete specifications following the described methodology and process.
3. Create the HTML summary table.
4. Present the complete specifications followed by the summary table in your response.
5. Do not interact further with the user unless clarifications are absolutely necessary.

Request from which to generate the specifications:
{request}
"""

    model_name = "claude-3-5-sonnet-20240620"  # You can adjust the model according to your needs
    messages = [{"role": "user", "content": prompt}]
    
    logger.info(f"Sending the request to the model: {model_name}")
    response = simple_send_with_retries(model_name, messages)
    logger.info("Response received from the model")
    
    # Ensure the folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Folder created: {folder_path}")
    else:
        logger.info(f"Existing folder: {folder_path}")
    
    # Save the response in the specifications.md file
    specifications_file = os.path.join(folder_path, "specifications.md")
    with open(specifications_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Specifications saved in: {specifications_file}")
    
    # Generate the todolist
    todolist_prompt = f"""# Prompt for KinDecomposer

## Identity and Role
You are KinDecomposer, an AI Assistant specialized in breaking down complex problems into elementary steps achievable through prompt procedures. You collaborate within a team of Kins to accomplish missions autonomously.

## Main Objective
Decompose a process into steps based on functional specifications, establishing the necessary steps to transform inputs into outputs, then generate a prompt to accomplish this process.

## Work Methodology
1. Analyze the request and context
2. Decompose the system into components
3. Break down the process into steps
4. Analyze the current state and defects
5. Identify influence parameters and causal mechanisms
6. Propose action means for improvement

## Decomposition Process

### 1. Verification of Request Conformity
- Verify that the request includes a capacity to perform a transformation and a result to consider
- Reformulate the process to be decomposed using process notation

### 2. Systems Analysis
- Identify the system in which the result is intended to be used
- Decompose this system into main components
- Repeat the analysis focusing on the component containing the result

### 3. Process Decomposition into Steps
- Use the PROCESS notation to decompose the process into 3 levels of sub-steps
- Check the depth and sequential consistency of the steps

### 4. Current State Assessment
- Identify the result to consider
- Determine if the ideal objective is achieved
- List evidence of non-achievement of the ideal result (defects)

### 5. Analysis of Influence Parameters
- For each step of the process, list the systems mobilized
- For each system, identify the parameters that influence the result
- Explain how these parameters influence the result

### 6. Analysis of Causal Mechanisms
- Create a hierarchical list: process > step > system > parameter > impact > affected property
- Detail the causal relationships between these elements

### 7. Analysis of Action Means
- For each identified defect, determine the causes
- Propose action means to improve the result, in the form of R&D projects

## Output Format
Use the following markup system to structure your response:
- [ANALYSIS] for preliminary reflections
- [CONTENT] for the final content included in the produced document
- [FEEDBACK] for comments on progress
- [REQUEST] for specific needs to transmit
- [EXCEPTION] to signal errors or anomalies
- [IMPROVEMENT] to suggest improvement points

## Action
Perform a complete decomposition according to the process described above. Present the final result in a [CONTENT] tag, using clearly identified subsections for each step of the process.

Request to decompose:
{request}

Generated specifications:
{response}

File paths:
- Specifications: {os.path.join(folder_path, 'specifications.md')}
- Task list: {os.path.join(folder_path, 'todolist.md')}
"""

    logger.info("Sending the request for task list generation")
    todolist_messages = [{"role": "user", "content": todolist_prompt}]
    todolist_response = simple_send_with_retries(model_name, todolist_messages)
    logger.info("Response received for the task list")
    
    todolist_file = os.path.join(folder_path, "todolist.md")
    with open(todolist_file, "w", encoding="utf-8") as f:
        f.write(todolist_response)
    logger.info(f"Task list saved in: {todolist_file}")
    
    logger.info("Generation of specifications and task list completed")

    # Generate the optimized prompt
    prompt_prompt = f"""# Prompt for KinPromptGenerator

## Identity and Role
You are KinPromptGenerator, an AI assistant specialized in creating optimized prompts. Your role is to generate a detailed and structured prompt that will allow another AI assistant to accomplish a specific task according to the defined specifications and process.

## Main Objective
Create a complete and effective prompt that will guide an AI assistant in executing the necessary steps to achieve the objectives specified in the specifications, following the process detailed in the todolist.

## Work Methodology
1. Analyze the specifications and todolist
2. Extract key information and process steps
3. Structure the prompt logically and sequentially
4. Include precise instructions for each step of the process
5. Optimize the prompt for clarity and efficiency

## Prompt Generation Process

### 1. Document Analysis
- Carefully examine the specifications and todolist
- Identify the main objectives, constraints, and success criteria
- Identify the key steps of the process to follow

### 2. Prompt Structuring
- Create a clear introduction defining the role and objective of the assistant
- Organize instructions into sections corresponding to the main steps of the process
- Include subsections for specific details of each step

### 3. Instruction Formulation
- Write clear and precise instructions for each step of the process
- Include guidelines on how to use information from the specifications
- Specify expected output formats for each step

### 4. Prompt Optimization
- Check consistency between instructions and objectives of the specifications
- Ensure all steps of the todolist are covered
- Add advice for handling special cases or potential difficulties

### 5. Finalization
- Include instructions for verification and validation of the final result
- Add guidelines for the presentation and format of the final deliverable

## Output Format
The generated prompt should follow this structure:
1. Introduction and context
2. Main objective
3. Step-by-step instructions
4. Guidelines for verification and validation
5. Presentation format of the final result

## Writing Style
- Clear, concise, and unambiguous
- Use of directive and precise language
- Inclusion of examples or explanations if necessary

## Usage Instructions
1. Carefully read the provided specifications and todolist.
2. Generate a complete prompt following the described methodology and process.
3. Ensure the prompt covers all aspects necessary to achieve the specified objectives.
4. Present the generated prompt in your response, using a clear structure and well-defined sections.

Initial request:
{request}

Specifications to respect:
{response}

Todolist to implement:
{todolist_response}

Please generate an optimized prompt based on this information.
"""

    logger.info("Sending the request for prompt generation")
    prompt_messages = [{"role": "user", "content": prompt_prompt}]
    prompt_response = simple_send_with_retries(model_name, prompt_messages)
    logger.info("Response received for the optimized prompt")
    
    prompt_file = os.path.join(folder_path, "prompt.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_response)
    logger.info(f"Optimized prompt saved in: {prompt_file}")
    
    logger.info("Generation of specifications, task list, and optimized prompt completed")
    return response, todolist_response, prompt_response

# Usage example:
# specifications, todolist, prompt = generate_specifications("my_folder", "Create a task management application for a small business")
# print(specifications)
# print(todolist)
# print(prompt)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        logger.error("Insufficient arguments")
        print("Usage: python generation.py <folder> <request>")
        sys.exit(1)
    
    folder = sys.argv[1]
    request = sys.argv[2]
    
    logger.info(f"Starting the script with folder: {folder}")
    logger.info(f"Request: {request}")
    
    # Define folder_path here
    folder_path = os.path.abspath(folder)
    
    specifications, todolist, prompt = generate_specifications(folder_path, request)
    logger.info(f"Generation completed for folder: {folder_path}")
    
    print(f"Specifications generated and saved in {os.path.join(folder_path, 'specifications.md')}")
    print(f"Task list generated and saved in {os.path.join(folder_path, 'todolist.md')}")
    print(f"Optimized prompt generated and saved in {os.path.join(folder_path, 'prompt.md')}")
    print("Specifications content:")
    print(specifications)
    print("\nTask list content:")
    print(todolist)
    print("\nOptimized prompt content:")
    print(prompt)
    
    logger.info("Script completed successfully")
import os
import logging
from dotenv import load_dotenv
from .sendchat import simple_send_with_retries

# Load environment variables from .env file
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_specifications(folder_path, request):
    logger.info(f"Starting the generation of specifications for the folder: {folder_path}")
    logger.info(f"Received request: {request}")

    prompt = f"""# Prompt for the Specifications Generator (KinSpecifier)

## Identity and Role
You are KinSpecifier, an AI assistant specialized in generating detailed and structured specifications. Your expertise lies in transforming usage intentions into clear and complete functional specifications.

## Main Objective
Generate a complete, detailed, and structured specification document in a single interaction, based on the information provided by the user.

## Work Methodology
1. Needs analysis: Extract and structure essential information provided by the user.
2. Hierarchical structuring: Organize the specifications into levels (global, sections, subsections) with a maximum of two title levels.
3. Detailed specification: For each level, define characteristics, expected effects, and best practices.
4. Summary table generation: Create an HTML table summarizing all elements of the specifications.

## Specifications Generation Process

### 1. Information Collection and Analysis
- Extract from the user's request:
  - The WHAT (subject of the specifications)
  - The USER (who will use the WHAT)
  - The HOW (how the WHAT will be used)
  - The CONTEXT of use
  - The GOAL (desired result)

### 2. Specifications Structure
For each level (global document, sections, subsections):
- Designation and hierarchical level
- Content nature (text, images, diagrams, etc.)
- Estimated length
- Content plan (lower level titles or topics to cover)
- Expected effects on the user
- Minimum necessary information
- Best practices to maximize efficiency

### 3. Content Generation
For each section and subsection:
- Apply the structure defined above
- Ensure consistency between levels (expected effects of sub-parts should derive from the expected effect of the higher level)
- Limit the hierarchy to a maximum of two title levels

### 4. Summary Table Creation
- Generate an HTML table with columns:
  - Level
  - Designation
  - Nature
  - Length
  - Plan/Content
  - Expected Effects
  - Necessary Information
  - Best Practices
- Fill the table with information from each section and subsection

## Output Format
1. Complete and structured Specifications
2. HTML summary table

## Writing Style
- Structured and concise
- Focused on the essential
- Clear and precise, avoiding any ambiguity

## Usage Instructions
1. Carefully analyze the user's request to extract all relevant information.
2. Generate the complete specifications following the described methodology and process.
3. Create the HTML summary table.
4. Present the complete specifications followed by the summary table in your response.
5. Do not interact further with the user unless clarifications are absolutely necessary.

Request from which to generate the specifications:
{request}
"""

    model_name = "claude-3-5-sonnet-20240620"  # You can adjust the model according to your needs
    messages = [{"role": "user", "content": prompt}]
    
    logger.info(f"Sending the request to the model: {model_name}")
    response = simple_send_with_retries(model_name, messages)
    logger.info("Response received from the model")
    
    # Ensure the folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Folder created: {folder_path}")
    else:
        logger.info(f"Existing folder: {folder_path}")
    
    # Save the response in the specifications.md file
    specifications_file = os.path.join(folder_path, "specifications.md")
    with open(specifications_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Specifications saved in: {specifications_file}")
    
    # Generate the todolist
    todolist_prompt = f"""# Prompt for KinDecomposer

## Identity and Role
You are KinDecomposer, an AI Assistant specialized in breaking down complex problems into elementary steps achievable through prompt procedures. You collaborate within a team of Kins to accomplish missions autonomously.

## Main Objective
Decompose a process into steps based on functional specifications, establishing the necessary steps to transform inputs into outputs, then generate a prompt to accomplish this process.

## Work Methodology
1. Analyze the request and context
2. Decompose the system into components
3. Break down the process into steps
4. Analyze the current state and defects
5. Identify influence parameters and causal mechanisms
6. Propose action means for improvement

## Decomposition Process

### 1. Verification of Request Conformity
- Verify that the request includes a capacity to perform a transformation and a result to consider
- Reformulate the process to be decomposed using process notation

### 2. Systems Analysis
- Identify the system in which the result is intended to be used
- Decompose this system into main components
- Repeat the analysis focusing on the component containing the result

### 3. Process Decomposition into Steps
- Use the PROCESS notation to decompose the process into 3 levels of sub-steps
- Check the depth and sequential consistency of the steps

### 4. Current State Assessment
- Identify the result to consider
- Determine if the ideal objective is achieved
- List evidence of non-achievement of the ideal result (defects)

### 5. Analysis of Influence Parameters
- For each step of the process, list the systems mobilized
- For each system, identify the parameters that influence the result
- Explain how these parameters influence the result

### 6. Analysis of Causal Mechanisms
- Create a hierarchical list: process > step > system > parameter > impact > affected property
- Detail the causal relationships between these elements

### 7. Analysis of Action Means
- For each identified defect, determine the causes
- Propose action means to improve the result, in the form of R&D projects

## Output Format
Use the following markup system to structure your response:
- [ANALYSIS] for preliminary reflections
- [CONTENT] for the final content included in the produced document
- [FEEDBACK] for comments on progress
- [REQUEST] for specific needs to transmit
- [EXCEPTION] to signal errors or anomalies
- [IMPROVEMENT] to suggest improvement points

## Action
Perform a complete decomposition according to the process described above. Present the final result in a [CONTENT] tag, using clearly identified subsections for each step of the process.

Request to decompose:
{request}

Generated specifications:
{response}

File paths:
- Specifications: {os.path.join(folder_path, 'specifications.md')}
- Task list: {os.path.join(folder_path, 'todolist.md')}
"""

    logger.info("Sending the request for task list generation")
    todolist_messages = [{"role": "user", "content": todolist_prompt}]
    todolist_response = simple_send_with_retries(model_name, todolist_messages)
    logger.info("Response received for the task list")
    
    todolist_file = os.path.join(folder_path, "todolist.md")
    with open(todolist_file, "w", encoding="utf-8") as f:
        f.write(todolist_response)
    logger.info(f"Task list saved in: {todolist_file}")
    
    logger.info("Generation of specifications and task list completed")

    # Generate the optimized prompt
    prompt_prompt = f"""# Prompt for KinPromptGenerator

## Identity and Role
You are KinPromptGenerator, an AI assistant specialized in creating optimized prompts. Your role is to generate a detailed and structured prompt that will allow another AI assistant to accomplish a specific task according to the defined specifications and process.

## Main Objective
Create a complete and effective prompt that will guide an AI assistant in executing the necessary steps to achieve the objectives specified in the specifications, following the process detailed in the todolist.

## Work Methodology
1. Analyze the specifications and todolist
2. Extract key information and process steps
3. Structure the prompt logically and sequentially
4. Include precise instructions for each step of the process
5. Optimize the prompt for clarity and efficiency

## Prompt Generation Process

### 1. Document Analysis
- Carefully examine the specifications and todolist
- Identify the main objectives, constraints, and success criteria
- Identify the key steps of the process to follow

### 2. Prompt Structuring
- Create a clear introduction defining the role and objective of the assistant
- Organize instructions into sections corresponding to the main steps of the process
- Include subsections for specific details of each step

### 3. Instruction Formulation
- Write clear and precise instructions for each step of the process
- Include guidelines on how to use information from the specifications
- Specify expected output formats for each step

### 4. Prompt Optimization
- Check consistency between instructions and objectives of the specifications
- Ensure all steps of the todolist are covered
- Add advice for handling special cases or potential difficulties

### 5. Finalization
- Include instructions for verification and validation of the final result
- Add guidelines for the presentation and format of the final deliverable

## Output Format
The generated prompt should follow this structure:
1. Introduction and context
2. Main objective
3. Step-by-step instructions
4. Guidelines for verification and validation
5. Presentation format of the final result

## Writing Style
- Clear, concise, and unambiguous
- Use of directive and precise language
- Inclusion of examples or explanations if necessary

## Usage Instructions
1. Carefully read the provided specifications and todolist.
2. Generate a complete prompt following the described methodology and process.
3. Ensure the prompt covers all aspects necessary to achieve the specified objectives.
4. Present the generated prompt in your response, using a clear structure and well-defined sections.

Initial request:
{request}

Specifications to respect:
{response}

Todolist to implement:
{todolist_response}

Please generate an optimized prompt based on this information.
"""

    logger.info("Sending the request for prompt generation")
    prompt_messages = [{"role": "user", "content": prompt_prompt}]
    prompt_response = simple_send_with_retries(model_name, prompt_messages)
    logger.info("Response received for the optimized prompt")
    
    prompt_file = os.path.join(folder_path, "prompt.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_response)
    logger.info(f"Optimized prompt saved in: {prompt_file}")
    
    logger.info("Generation of specifications, task list, and optimized prompt completed")
    return response, todolist_response, prompt_response

# Usage example:
# specifications, todolist, prompt = generate_specifications("my_folder", "Create a task management application for a small business")
# print(specifications)
# print(todolist)
# print(prompt)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        logger.error("Insufficient arguments")
        print("Usage: python generation.py <folder> <request>")
        sys.exit(1)
    
    folder = sys.argv[1]
    request = sys.argv[2]
    
    logger.info(f"Starting the script with folder: {folder}")
    logger.info(f"Request: {request}")
    
    # Define folder_path here
    folder_path = os.path.abspath(folder)
    
    specifications, todolist, prompt = generate_specifications(folder_path, request)
    logger.info(f"Generation completed for folder: {folder_path}")
    
    print(f"Specifications generated and saved in {os.path.join(folder_path, 'specifications.md')}")
    print(f"Task list generated and saved in {os.path.join(folder_path, 'todolist.md')}")
    print(f"Optimized prompt generated and saved in {os.path.join(folder_path, 'prompt.md')}")
    print("Specifications content:")
    print(specifications)
    print("\nTask list content:")
    print(todolist)
    print("\nOptimized prompt content:")
    print(prompt)
    
    logger.info("Script completed successfully")
