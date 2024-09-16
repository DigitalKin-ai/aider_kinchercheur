import os
import logging
import traceback
from dotenv import load_dotenv
from .sendchat import simple_send_with_retries

# Load environment variables from .env file
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generation(folder_path, request, role="default"):
    logger.info(f"Starting the generation of specifications for the folder: {folder_path}")
    logger.info(f"Received request: {request}")

    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)
    logger.info(f"Using folder: {folder_path}")

    model_name = "gpt-4o-mini"  # You can adjust the model according to your needs

    role_file_path = os.path.join(folder_path, role, "role.md")
    try:
        with open(role_file_path, 'r', encoding='utf-8') as role_file:
            roleText = role_file.read()
    except FileNotFoundError:
        logger.warning(f"Role file not found: {role_file_path}")
        os.makedirs(os.path.dirname(role_file_path), exist_ok=True)
        default_role_text = "Act as an expert developer and writer."
        with open(role_file_path, 'w', encoding='utf-8') as role_file:
            role_file.write(default_role_text)
        roleText = default_role_text
        logger.info(f"Created role file with default content: {role_file_path}")

    # Generate specifications
    specifications = generate_content(model_name, roleText, "specifications", request, folder_path)

    # Generate todolist
    todolist = generate_content(model_name, roleText, "todolist", request, folder_path, specifications)

    logger.info("Generation of specifications, task list and Toolbox completed")
    return specifications, todolist

def generate_content(model_name, role, content_type, request, folder_path, specifications=None, todolist=None):
    file_name = f"{content_type}.{'py' if content_type == 'toolbox' else 'md'}"
    file_path = os.path.join(folder_path, file_name)
    
    # Read existing content if file exists
    existing_content = ""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
    
    prompt = get_prompt(content_type, request, specifications, todolist, folder_path, role, existing_content)
    
    logger.info(f"Sending the request for {content_type} generation")
    messages = [{"role": "user", "content": prompt}]
    response = simple_send_with_retries(model_name, messages)
    logger.info(f"Response received for {content_type}")
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"{content_type.capitalize()} saved in: {file_path}")
    
    return response

def get_prompt(content_type, request, specifications, todolist, folder_path, role, existing_content):
    base_prompt = f"""# Role
{role}

## SubRole
Specialized in generating and improving content for {content_type}. Your expertise lies in creating or enhancing the existing content based on the provided information and requirements.

## Main Objective
Generate or improve the {content_type} based on the given request, specifications, and existing content (if any).

## Work Methodology
1. Analyze the existing content (if any) and the new requirements.
2. Identify areas for improvement or additions.
3. Generate or modify the content to meet the new requirements while preserving valuable existing information.
4. Ensure consistency and coherence in the final output.

## Existing Content
{existing_content}

## New Request
{request}

## Action
Based on the existing content and the new request, please generate or improve the {content_type}. If there's existing content, incorporate it where appropriate and make necessary improvements. If there's no existing content, create new content that meets the requirements.

"""

    if content_type == "specifications":
        base_prompt += f"""
## Additional Context
Specifications should be detailed, structured, and clear. Include a summary table if appropriate.

## Output Format
1. Complete and structured Specifications
2. HTML summary table (if applicable)

Specifications to respect:
{specifications}
"""
    elif content_type == "todolist":
        base_prompt += f"""
## Additional Context
The todolist should break down the process into clear, actionable steps.

## Output Format
Use the following markup system to structure your response:
- [ANALYSIS] for preliminary reflections
- [CONTENT] for the final content included in the produced document
- [FEEDBACK] for comments on progress
- [REQUEST] for specific needs to transmit
- [EXCEPTION] to signal errors or anomalies
- [IMPROVEMENT] to suggest improvement points

Specifications to respect:
{specifications}
"""
    elif content_type == "toolbox":
        base_prompt += f"""
## Additional Context
Generate a complete, functional Python script named "toolbox.py" that implements a set of utility functions based on the specifications and task list. These functions should be designed to be easily called by LLM models via command line arguments.

## Output Format
A complete, executable Python script named "toolbox.py" that includes:
1. Necessary imports
2. Toolbox function definitions
3. Command-line argument parsing
4. Main execution block
5. Comprehensive docstrings and comments

Specifications to respect:
{specifications}

Todolist to implement:
{todolist}

Please generate a complete Python script based on this information. Do not include any text, do not preface with "```python". The answer should be the functional python code only.
"""
    else:
        raise ValueError(f"Unknown content type: {content_type}")

    return base_prompt

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        logger.error("Insufficient arguments")
        print("Usage: python generation.py <folder> <request> [role]")
        sys.exit(1)
    
    folder = sys.argv[1]
    request = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "default"
    
    logger.info(f"Starting the toolbox with folder: {folder}")
    logger.info(f"Request: {request}")
    logger.info(f"Role: {role}")
    
    folder_path = os.path.abspath(folder)
    
    try:
        specifications, todolist = generation(folder_path, request, role)
        logger.info(f"Generation completed for folder: {folder_path}")
        
        for content_type in ["specifications", "todolist"]:
            print(f"{content_type.capitalize()} generated and saved in {os.path.join(folder_path, f'{content_type}.{'py' if content_type == 'toolbox' else 'md'}')}")
        
        for content_type, content in [("Specifications", specifications), ("Todolist", todolist)]:
            print(f"\n{content_type} content:")
            print(content)
        
        logger.info("Toolbox completed successfully")
    except Exception as e:
        logger.error(f"An error occurred during the generation process: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"Error: {str(e)}")
        sys.exit(1)
