import os
import logging
import traceback
from dotenv import load_dotenv
from .sendchat import simple_send_with_retries

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_specifications(folder_path, message):
    logger.info(f"Starting the generation of specifications for the folder: {folder_path}")
    logger.info(f"Received message: {message}")
    
    # Ensure that the folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Folder created: {folder_path}")
    else:
        logger.info(f"Existing folder: {folder_path}")

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

Message from which to generate the specifications:
{message}
"""
    model_name = "claude-3-5-sonnet-20240620"  # Vous pouvez ajuster le modèle selon vos besoins
    messages = [{"role": "user", "content": prompt}]
    
    logger.info(f"Envoi de la request au modèle: {model_name}")
    response = simple_send_with_retries(model_name, messages)
    logger.info("Réponse reçue du modèle")
    
    # Save the response in the specifications.md file
    specifications_file = os.path.join(folder_path, "specifications.md")
    with open(specifications_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Specifications saved in: {specifications_file}")

    # Verify that the specifications were actually generated
    if "# Spécifications" not in response and "# Specifications" not in response:
        logger.error("The generated specifications seem to be empty or invalid.")
        raise ValueError("Failed to generate valid specifications. Please check the model's response.")
    
    # Générer la todolist
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

Message to decompose:
{message}

Generated specifications:
{response}

File paths:
- Specifications: {os.path.join(folder_path, 'specifications.md')}
- Task list: {os.path.join(folder_path, 'todolist.md')}
"""

    logger.info("Envoi de la request pour la génération de la liste des tâches")
    todolist_messages = [{"role": "user", "content": todolist_prompt}]
    todolist_response = simple_send_with_retries(model_name, todolist_messages)
    logger.info("Réponse reçue pour la liste des tâches")
    
    todolist_file = os.path.join(folder_path, "todolist.md")
    with open(todolist_file, "w", encoding="utf-8") as f:
        f.write(todolist_response)
    logger.info(f"Liste des tâches enregistrée dans: {todolist_file}")
    
    logger.info("Generation of specifications and task list completed")

    # Génération du prompt optimisé
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

Initial message:
{message}

Specifications to respect:
{response}

Todolist to implement:
{todolist_response}

Please generate an optimized prompt based on this information.
"""

    logger.info("Envoi de la request pour la génération du prompt")
    prompt_messages = [{"role": "user", "content": prompt_prompt}]
    prompt_response = simple_send_with_retries(model_name, prompt_messages)
    logger.info("Réponse reçue pour le prompt optimisé")
    
    prompt_file = os.path.join(folder_path, "prompt.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_response)
    logger.info(f"Prompt optimisé enregistré dans: {prompt_file}")
    
    logger.info("Génération du cahier des charges, de la liste des tâches et du prompt optimisé terminée")


    return response, todolist_response, prompt_response

# Exemple d'utilisation :
# specifications, todolist, prompt = generate_specifications("my_folder", "Create a task management application for a small business")
# print(specifications)
# print(todolist)
# print(prompt)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        logger.error("Arguments insuffisants")
        print("Usage: python generation.py <dossier> <request>")
        sys.exit(1)
    
    folder = sys.argv[1]
    request = sys.argv[2]
    
    logger.info(f"Starting the script with folder: {folder}")
    logger.info(f"Request: {request}")
    
    # Définir folder_path ici
    folder_path = os.path.abspath(folder)
    
    specifications, todolist, prompt = generate_specifications(folder_path, request)
    logger.info(f"Generation completed for folder: {folder_path}")
    
    print(f"Specifications generated and saved in {os.path.join(folder_path, 'specifications.md')}")
    print(f"Task list generated and saved in {os.path.join(folder_path, 'todolist.md')}")
    print(f"Optimized prompt generated and saved in {os.path.join(folder_path, 'prompt.md')}")
    print("Specifications content:")
    print(specifications)
    print("\nContenu de la liste des tâches :")
    print(todolist)
    print("\nContenu du prompt optimisé :")
    print(prompt)
    
    logger.info("Script completed successfully")
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

Please generate the specifications based on this request. Make sure to include all necessary sections and details as outlined in the methodology above.
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

    # Save the specifications in the specifications.md file as well
    specifications_file = os.path.join(folder_path, "specifications.md")
    with open(specifications_file, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"specifications saved in: {specifications_file}")
    
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
    
    logger.info("Generation of specifications, specifications, and task list completed")

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
    
    try:
        logger.info("Generation of specifications, task list, and optimized prompt completed")
        return response, todolist_response, prompt_response
    except Exception as e:
        logger.error(f"Error in generate_specifications: {e}")
        logger.error(traceback.format_exc())
        raise

# Usage example:
# specifications, todolist, prompt = generer_specifications("my_folder", "Create a task management application for a small business")
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
    message = sys.argv[2]
    
    logger.info(f"Starting the script with folder: {folder}")
    logger.info(f"Message: {message}")
    
    # Define folder_path here
    folder_path = os.path.abspath(folder)
    
    specifications, todolist, prompt = generate_specifications(folder_path, message)
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
    
    try:
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
    except Exception as e:
        logger.error(f"An error occurred during the generation process: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)
