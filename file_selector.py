import os
import re

def is_demande(filename):
    return re.search(r'demande\.md', filename.lower()) is not None

def is_cdc(filename):
    return re.search(r'cdc\.md', filename.lower()) is not None

def is_todolist(filename):
    return re.search(r'todolist\.md', filename.lower()) is not None

def is_prompt(filename):
    return re.search(r'prompt\.md', filename.lower()) is not None

def is_sortie(filename):
    return re.search(r'sortie\.md', filename.lower()) is not None

def is_analyse(filename):
    return filename.lower().startswith('analyses/')

def is_text_file(filename):
    text_extensions = ['.md', '.txt', '.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg']
    return any(filename.lower().endswith(ext) for ext in text_extensions)

def select_relevant_files(folder):
    print(f"DEBUG: select_relevant_files function called for folder: {folder}")
    
    relevant_files = []
    
    for root, dirs, files in os.walk(folder):
        for file in files:
            full_path = os.path.join(root, file)
            if is_text_file(file):
                if is_demande(file) or is_cdc(file) or is_todolist(file) or is_prompt(file):
                    relevant_files.append(full_path)
                elif is_analyse(os.path.relpath(full_path, folder)):
                    relevant_files.append(full_path)
    
    print("DEBUG: Final selected files:")
    for file in relevant_files:
        print(f"  - {file}")
    
    return relevant_files

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python file_selector.py <folder>")
        sys.exit(1)
    
    folder = sys.argv[1]
    print(f"DEBUG: file_selector.py executed directly for folder: {folder}")
    
    selected_files = select_relevant_files(folder)
    print("\nSelected files:")
    for file in selected_files:
        print(file)
