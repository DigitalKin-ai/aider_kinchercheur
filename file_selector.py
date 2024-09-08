import os
import re

import os

def is_in_correct_folder(filename, folder):
    return os.path.dirname(filename) == folder

def is_message(filename, folder):
    return re.search(r'message\.md', filename.lower()) is not None and is_in_correct_folder(filename, folder)

def is_specifications(filename, folder):
    return re.search(r'specifications\.md', filename.lower()) is not None and is_in_correct_folder(filename, folder)

def is_todolist(filename, folder):
    return re.search(r'todolist\.md', filename.lower()) is not None and is_in_correct_folder(filename, folder)

def is_prompt(filename, folder):
    return re.search(r'prompt\.md', filename.lower()) is not None and is_in_correct_folder(filename, folder)

def is_output(filename, folder):
    return re.search(r'output\.md', filename.lower()) is not None and is_in_correct_folder(filename, folder)

def is_analysis(filename, folder):
    return filename.lower().startswith('analysis/') and is_in_correct_folder(filename, os.path.join(folder, 'analysis'))

def is_text_file(filename):
    text_extensions = ['.md', '.txt', '.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg']
    return any(filename.lower().endswith(ext) for ext in text_extensions)

def select_relevant_files(folder_or_files):
    print(f"DEBUG: select_relevant_files function called for: {folder_or_files}")
    
    if isinstance(folder_or_files, list):
        all_files = folder_or_files
    else:
        all_files = [os.path.join(root, file) for root, dirs, files in os.walk(folder_or_files) for file in files]
    
    relevant_files = []
    
    for full_path in all_files:
        file = os.path.basename(full_path)
        folder = os.path.dirname(full_path)
        if is_text_file(file):
            if (is_message(full_path, folder) or 
                is_specifications(full_path, folder) or 
                is_todolist(full_path, folder) or 
                is_prompt(full_path, folder) or
                is_output(full_path, folder) or
                is_analysis(full_path, folder)):
                relevant_files.append(full_path)
    
    print("DEBUG: Final selected files:")
    for file in relevant_files:
        print(f"  - {file}")
    
    return relevant_files

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python file_selector.py <folder_or_file1> [file2] [file3] ...")
        sys.exit(1)
    
    args = sys.argv[1:]
    print(f"DEBUG: file_selector.py executed directly with arguments: {args}")
    
    if len(args) == 1 and os.path.isdir(args[0]):
        selected_files = select_relevant_files(args[0])
    else:
        selected_files = select_relevant_files(args)
    
    print("\nSelected files:")
    for file in selected_files:
        print(file)
