# flake8: noqa: E501

from .base_prompts import CoderPrompts


class SingleWholeFileFunctionPrompts(CoderPrompts):
    main_system = """Agis comme demandé dans les fichiers de prompt système donnés.
    
Once you chose the Action you MUST use the `write_file` function to update the file to make the changes.
"""

    system_reminder = """
ONLY return text using the `write_file` function.
NEVER return text outside the `write_file` function.
"""

    files_content_prefix = "Here is the current content of the file:\n"
    files_no_full_files = "I am not sharing any files yet."

    redacted_edit_message = "No changes are needed."

    # TODO: should this be present for using this with gpt-4?
    repo_content_prefix = None

    # TODO: fix the chat history, except we can't keep the whole file
