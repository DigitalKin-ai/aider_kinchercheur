import os
import re
import random

def is_demande_or_todolist(filename):
    patterns = [
        r'.*demande.*',
        r'.*todolist.*'
    ]
    return any(re.search(pattern, filename.lower()) for pattern in patterns)

def is_prompt(filename):
    return re.search(r'.*prompt.*', filename.lower()) is not None

def is_analyse(filename):
    return re.search(r'.*analyses.*', filename.lower()) is not None

def is_text_file(filename):
    text_extensions = ['.md', '.txt', '.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg']
    return any(filename.lower().endswith(ext) for ext in text_extensions)

def select_relevant_files(file_list, max_files=20):
    print("DEBUG: select_relevant_files function called")
    print(f"DEBUG: Total files found: {len(file_list)}")
    
    text_files = [file for file in file_list if is_text_file(file)]
    
    demandes_and_todolists = [file for file in text_files if is_demande_or_todolist(file)]
    prompts = [file for file in text_files if is_prompt(file)]
    analyses = [file for file in text_files if is_analyse(file)]
    
    print(f"DEBUG: Demandes and Todolists: {len(demandes_and_todolists)}")
    print("DEBUG: Demandes and Todolists files:")
    for file in demandes_and_todolists:
        print(f"  - {file}")
    
    print(f"DEBUG: prompts: {len(prompts)}")
    print("DEBUG: prompt files:")
    for file in prompts:
        print(f"  - {file}")
    
    print(f"DEBUG: analyses: {len(analyses)}")
    print("DEBUG: analyse files:")
    for file in analyses:
        print(f"  - {file}")
    
    relevant_files = demandes_and_todolists.copy()
    
    # Add up to 3 random prompt files
    relevant_files.extend(random.sample(prompts, min(3, len(prompts))))
    
    # Add up to 3 random analyse files
    relevant_files.extend(random.sample(analyses, min(3, len(analyses))))
    
    # Ensure we don't exceed max_files
    relevant_files = relevant_files[:max_files]
    
    print("DEBUG: Final selected files:")
    for file in relevant_files:
        print(f"  - {file}")
    
    return relevant_files

if __name__ == "__main__":
    print("DEBUG: file_selector.py executed directly")
    all_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            all_files.append(os.path.join(root, file))
    print(f"DEBUG: All files: {all_files}")
    
    selected_files = select_relevant_files(all_files)
    print("\nSelected files:")
    for file in selected_files:
        print(file)