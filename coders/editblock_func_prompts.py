# flake8: noqa: E501

from .base_prompts import CoderPrompts


class EditBlockFunctionPrompts(CoderPrompts):
    main_system = """Agis comme demandé dans les fichiers de prompt système donnés.

Once you chose the Action you MUST use the `replace_lines` function to edit the files to make the needed changes.
"""

    system_reminder = """
ONLY return text using the `replace_lines` function.
NEVER return text outside the `replace_lines` function.
"""

    files_content_prefix = "Here is the current content of the files:\n"
    files_no_full_files = "I am not sharing any files yet."

    redacted_edit_message = "No changes are needed."

    repo_content_prefix = (
        "Below here are summaries of other files! Do not propose changes to these *read-only*"
        " files without asking me first.\n"
    )
