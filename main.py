import configparser
import os
import re
import sys
import threading
from pathlib import Path
import logging
import traceback

from aider import __version__, models, utils
import git
from dotenv import load_dotenv
from prompt_toolkit.enums import EditingMode

DEFAULT_MODEL_NAME = "gpt-4o-mini"  # or the default model you want to use

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from .file_selector import select_relevant_files
    from aider.args import get_parser
    from aider.coders import Coder
    from aider.commands import Commands, SwitchCoder
    from aider.history import ChatSummary
    from aider.io import InputOutput
    from .llm import litellm  # noqa: F401; properly init litellm on launch
    from .repo import GitRepo
    from .versioncheck import check_version
    from .dump import dump  # noqa: F401
    from .gui import launch_gui  # Import the launch_gui function
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)


def get_git_root():
    """Try and guess the git repo, since the conf.yml can be at the repo root"""
    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except git.InvalidGitRepositoryError:
        return None


def guessed_wrong_repo(io, git_root, fnames, git_dname):
    """After we parse the args, we can determine the real repo. Did we guess wrong?"""

    try:
        check_repo = Path(GitRepo(io, fnames, git_dname).root).resolve()
    except FileNotFoundError:
        return

    # we had no guess, rely on the "true" repo result
    if not git_root:
        return str(check_repo)

    git_root = Path(git_root).resolve()
    if check_repo == git_root:
        return

    return str(check_repo)


def setup_git(git_root, io):
    repo = None
    if git_root:
        repo = git.Repo(git_root)
    elif io.confirm_ask("No git repo found, create one to track GPT's changes (recommended)?"):
        git_root = str(Path.cwd().resolve())
        repo = git.Repo.init(git_root)
        io.tool_output("Git repository created in the current working directory.")
        check_gitignore(git_root, io, False)

    if not repo:
        return

    user_name = None
    user_email = None
    with repo.config_reader() as config:
        try:
            user_name = config.get_value("user", "name", None)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            user_email = config.get_value("user", "email", None)
        except configparser.NoSectionError:
            pass

    if user_name and user_email:
        return repo.working_tree_dir

    with repo.config_writer() as git_config:
        if not user_name:
            git_config.set_value("user", "name", "Lesterpaintstheworld")
            io.tool_error('Update git name with: git config user.name "Your Name"')
        if not user_email:
            git_config.set_value("user", "email", "reynolds.nicorr@gmail.com")
            io.tool_error('Update git email with: git config user.email "you@example.com"')

    return repo.working_tree_dir


def check_gitignore(git_root, io, ask=True):
    if not git_root:
        return

    try:
        repo = git.Repo(git_root)
        if repo.ignored(".aider"):
            return
    except git.exc.InvalidGitRepositoryError:
        pass

    pat = ".aider*"

    gitignore_file = Path(git_root) / ".gitignore"
    if gitignore_file.exists():
        content = io.read_text(gitignore_file)
        if content is None:
            return
        if pat in content.splitlines():
            return
    else:
        content = ""

    if ask and not io.confirm_ask(f"Add {pat} to .gitignore (recommended)?"):
        return

    if content and not content.endswith("\n"):
        content += "\n"
    content += pat + "\n"
    io.write_text(gitignore_file, content)

    io.tool_output(f"Added {pat} to .gitignore")


def format_settings(parser, args):
    show = scrub_sensitive_info(args, parser.format_values())
    # clean up the headings for consistency w/ new lines
    heading_env = "Environment Variables:"
    heading_defaults = "Defaults:"
    if heading_env in show:
        show = show.replace(heading_env, "\n" + heading_env)
        show = show.replace(heading_defaults, "\n" + heading_defaults)
    show += "\n"
    show += "Option settings:\n"
    for arg, val in sorted(vars(args).items()):
        if val:
            val = scrub_sensitive_info(args, str(val))
        show += f"  - {arg}: {val}\n"  # noqa: E221
    return show


def scrub_sensitive_info(args, text):
    # Replace sensitive information with last 4 characters
    if text and args.openai_api_key:
        last_4 = args.openai_api_key[-4:]
        text = text.replace(args.openai_api_key, f"...{last_4}")
    if text and args.anthropic_api_key:
        last_4 = args.anthropic_api_key[-4:]
        text = text.replace(args.anthropic_api_key, f"...{last_4}")
    return text


def check_streamlit_install(io):
    return utils.check_pip_install_extra(
        io,
        "streamlit",
        "You need to install the aider browser feature",
        ["aider-chat[browser]"],
    )


def launch_gui(args):
    from streamlit.web import cli

    from aider import gui

    print()
    print("CONTROL-C to exit...")

    target = gui.__file__

    st_args = ["run", target]

    st_args += [
        "--browser.gatherUsageStats=false",
        "--runner.magicEnabled=false",
        "--server.runOnSave=false",
    ]

    if "-dev" in __version__:
        print("Watching for file changes.")
    else:
        st_args += [
            "--global.developmentMode=false",
            "--server.fileWatcherType=none",
            "--client.toolbarMode=viewer",  # minimal?
        ]

    st_args += ["--"] + args

    cli.main(st_args)

    # from click.testing import CliRunner
    # runner = CliRunner()
    # from streamlit.web import bootstrap
    # bootstrap.load_config_options(flag_options={})
    # cli.main_run(target, args)
    # sys.argv = ['streamlit', 'run', '--'] + args


def parse_lint_cmds(lint_cmds, io):
    err = False
    res = dict()
    for lint_cmd in lint_cmds:
        if re.match(r"^[a-z]+:.*", lint_cmd):
            pieces = lint_cmd.split(":")
            lang = pieces[0]
            cmd = lint_cmd[len(lang) + 1 :]
            lang = lang.strip()
        else:
            lang = None
            cmd = lint_cmd

        cmd = cmd.strip()

        if cmd:
            res[lang] = cmd
        else:
            io.tool_error(f'Unable to parse --lint-cmd "{lint_cmd}"')
            io.tool_error('The arg should be "language: cmd --args ..."')
            io.tool_error('For example: --lint-cmd "python: flake8 --select=E9"')
            err = True
    if err:
        return
    return res


def generate_search_path_list(default_fname, git_root, command_line_file):
    files = []
    default_file = Path(default_fname)
    files.append(Path.home() / default_file)  # homedir
    if git_root:
        files.append(Path(git_root) / default_file)  # git root
    files.append(default_file.resolve())
    if command_line_file:
        files.append(command_line_file)
    files = [Path(fn).resolve() for fn in files]
    files.reverse()
    uniq = []
    for fn in files:
        if fn not in uniq:
            uniq.append(fn)
    uniq.reverse()
    files = uniq
    files = list(map(str, files))
    files = list(dict.fromkeys(files))

    return files


def register_models(git_root, model_settings_fname, io, verbose=False):
    model_settings_files = generate_search_path_list(
        ".aider.model.settings.yml", git_root, model_settings_fname
    )

    try:
        files_loaded = models.register_models(model_settings_files)
        if len(files_loaded) > 0:
            if verbose:
                io.tool_output("Loaded model settings from:")
                for file_loaded in files_loaded:
                    io.tool_output(f"  - {file_loaded}")  # noqa: E221
        elif verbose:
            io.tool_output("No model settings files loaded")
    except Exception as e:
        io.tool_error(f"Error loading aider model settings: {e}")
        return 1

    if verbose:
        io.tool_output("Searched for model settings files:")
        for file in model_settings_files:
            io.tool_output(f"  - {file}")

    return None


def load_dotenv_files(git_root, dotenv_fname):
    dotenv_files = generate_search_path_list(
        ".env",
        git_root,
        dotenv_fname,
    )
    loaded = []
    for fname in dotenv_files:
        if Path(fname).exists():
            loaded.append(fname)
            load_dotenv(fname, override=True)
    return loaded


def register_litellm_models(git_root, model_metadata_fname, io, verbose=False):
    model_metatdata_files = generate_search_path_list(
        ".aider.model.metadata.json", git_root, model_metadata_fname
    )

    try:
        model_metadata_files_loaded = models.register_litellm_models(model_metatdata_files)
        if len(model_metadata_files_loaded) > 0 and verbose:
            io.tool_output("Loaded model metadata from:")
            for model_metadata_file in model_metadata_files_loaded:
                io.tool_output(f"  - {model_metadata_file}")  # noqa: E221
    except Exception as e:
        io.tool_error(f"Error loading model metadata models: {e}")
        return 1


import sys

def main(argv=None, input=None, output=None, force_git_root=None, return_coder=False):
    logger.info("Starting main function")
    if argv is None:
        argv = sys.argv[1:]

    if force_git_root:
        git_root = force_git_root
    else:
        git_root = get_git_root()

    conf_fname = Path(".aider.conf.yml")

    default_config_files = [conf_fname.resolve()]  # CWD
    if git_root:
        git_conf = Path(git_root) / conf_fname  # git root
        if git_conf not in default_config_files:
            default_config_files.append(git_conf)
    default_config_files.append(Path.home() / conf_fname)  # homedir
    default_config_files = list(map(str, default_config_files))

    parser = get_parser(default_config_files, git_root)
    args, unknown = parser.parse_known_args(argv)

    # Check if --gui argument is present
    if args.gui:
        logger.info("GUI mode requested")
        return launch_gui(argv)

    folder = args.folder
    message = args.message
    request = getattr(args, 'request', None)
    append_request = getattr(args, 'append_request', None)

    if folder is None:
        logger.error("Folder not specified")
        print("Usage: python -m aider --folder <folder> [--message <message>] [--request <request>] [--append-request <append_request>]")
        return 1

    # Define folder_path here
    folder_path = os.path.abspath(folder)
    logger.info(f"Working with folder: {folder_path}")

    if message:
        logger.info(f"Using message: {message}")

    # Create the io object
    io = InputOutput(
        args.pretty,
        args.yes,
        args.input_history_file,
        args.chat_history_file,
        input=input,
        output=output,
        user_input_color=args.user_input_color,
        tool_output_color=args.tool_output_color,
        tool_error_color=args.tool_error_color,
        dry_run=args.dry_run,
        encoding=args.encoding,
        llm_history_file=args.llm_history_file,
        editingmode=EditingMode.VI if args.vim else EditingMode.EMACS,
    )
    logger.info("InputOutput object created")

    try:
        # Check if the message is already present in the folder
        message_file = Path(folder_path) / 'message.md'
        if message_file.exists():
            logger.info(f"Message file exists: {message_file}")
            try:
                with open(message_file, 'r', encoding='utf-8') as f:
                    existing_message = f.read().strip()
                if message is None:
                    message = existing_message
                    logger.info("Using existing message")
                elif message.strip() == existing_message:
                    io.tool_output("The message is identical to the one already present. No need to regenerate the specifications.")
                    logger.info("Message is identical, skipping regeneration")
                else:
                    # Save the new message
                    with open(message_file, 'w', encoding='utf-8') as f:
                        f.write(message)
                    io.tool_output(f"New message saved to {message_file}")
                    logger.info(f"New message saved to {message_file}")
                    # Import generation module here to avoid circular import
                    from .generation import generate_specifications
                    specifications, todolist, prompt = generate_specifications(folder_path, message)
                    io.tool_output(f"Specifications, task list, and prompt generated for the folder: {folder_path}")
                    logger.info("Specifications, task list, and prompt generated")
            except Exception as e:
                logger.error(f"Error reading or writing message file: {e}")
                io.tool_error(f"Error processing message file: {e}")
        elif message is None:
            # Create a message.md file with default text
            message = "Set a coherent mission from the information available"
            try:
                with open(message_file, 'w', encoding='utf-8') as f:
                    f.write(message)
                io.tool_output(f"Created a message file with default text: {message_file}")
                logger.info(f"Created default message file: {message_file}")
            except Exception as e:
                logger.error(f"Error creating default message file: {e}")
                io.tool_error(f"Error creating default message file: {e}")
        
        # Save the new message (empty or not)
        try:
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message)
            io.tool_output(f"Message saved to {message_file}")
            logger.info(f"Message saved to {message_file}")
        except Exception as e:
            logger.error(f"Error saving message to file: {e}")
            io.tool_error(f"Error saving message to file: {e}")
        
        # Import generation module here to avoid circular import
        try:
            from .generation import generate_specifications
            specifications, todolist, prompt = generate_specifications(folder_path, message)
            io.tool_output(f"Specifications, task list, and prompt generated for the folder: {folder_path}")
            logger.info("Specifications, task list, and prompt generated")
        except Exception as e:
            logger.error(f"Error generating specifications: {e}")
            io.tool_error(f"Error generating specifications: {e}")

        # Add the append_request to the end of the message file if it's present
        if append_request:
            try:
                with open(message_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n{append_request}")
                io.tool_output(f"Append request added to the end of the message file: {message_file}")
                logger.info(f"Append request added to {message_file}")
            except Exception as e:
                logger.error(f"Error appending request to message file: {e}")
                io.tool_error(f"Error appending request to message file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in file operations: {e}")
        io.tool_error(f"An unexpected error occurred: {e}")

    if args.verbose:
        print("Config files search order, if no --config:")
        for file in default_config_files:
            exists = "(exists)" if Path(file).exists() else ""
            print(f"  - {file} {exists}")

    default_config_files.reverse()

    parser = get_parser(default_config_files, git_root)
    args, unknown = parser.parse_known_args(argv)

    # Load the .env file specified in the arguments
    loaded_dotenvs = load_dotenv_files(git_root, args.env_file)

    # Parse again to include any arguments that might have been defined in .env
    args = parser.parse_args(argv)

    if not args.verify_ssl:
        import httpx

        litellm._load_litellm()
        litellm._lazy_module.client_session = httpx.Client(verify=False)

    if args.dark_mode:
        args.user_input_color = "#32FF32"
        args.tool_error_color = "#FF3333"
        args.assistant_output_color = "#00FFFF"
        args.code_theme = "monokai"

    if args.light_mode:
        args.user_input_color = "green"
        args.tool_error_color = "red"
        args.assistant_output_color = "blue"
        args.code_theme = "default"

    if return_coder and args.yes is None:
        args.yes = True

    editing_mode = EditingMode.VI if args.vim else EditingMode.EMACS

    io = InputOutput(
        args.pretty,
        args.yes,
        args.input_history_file,
        args.chat_history_file,
        input=input,
        output=output,
        user_input_color=args.user_input_color,
        tool_output_color=args.tool_output_color,
        tool_error_color=args.tool_error_color,
        dry_run=args.dry_run,
        encoding=args.encoding,
        llm_history_file=args.llm_history_file,
        editingmode=editing_mode,
    )

    # Create the coder object
    # Set the default model if none is specified
    model_name = args.model or DEFAULT_MODEL_NAME
    
    coder = Coder.create(
        main_model=models.Model(model_name),
        edit_format=args.edit_format,
        io=io,
        repo=None,  # We're not using a Git repo here
        fnames=[],  # We'll add the files later
        read_only_fnames=[],
        show_diffs=args.show_diffs,
        auto_commits=False,  # No automatic commits
        dirty_commits=False,
        dry_run=args.dry_run,
        map_tokens=args.map_tokens,
        verbose=args.verbose,
        assistant_output_color=args.assistant_output_color,
        code_theme=args.code_theme,
        stream=args.stream,
        use_git=False,
        restore_chat_history=args.restore_chat_history,
        auto_lint=args.auto_lint,
        auto_test=args.auto_test,
        lint_cmds=None,
        test_cmd=args.test_cmd,
        commands=Commands(io, None),
        summarizer=ChatSummary(
            [models.Model(model_name).weak_model, models.Model(model_name)],
            args.max_chat_history_tokens or models.Model(model_name).max_chat_history_tokens,
        ),
        map_refresh=args.map_refresh,
        cache_prompts=args.cache_prompts,
    )

    # Ensure the main folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        io.tool_output(f"Main folder created: {folder_path}")
    else:
        io.tool_output(f"Main folder already exists: {folder_path}")

    # Add specific files from the folder
    specific_files = ['todolist.md', 'cdc.md', 'prompt.md']
    added_files = []

    for file in specific_files:
        file_path = Path(folder) / file
        if file_path.exists():
            coder.add_rel_fname(str(file_path))
            added_files.append(str(file_path))
            io.tool_output(f"File {file} added to the chat.")
        else:
            io.tool_output(f"File {file} not found in the folder.")

    if added_files:
        io.tool_output("Files added to the chat: " + ", ".join(added_files))
    else:
        io.tool_output("No specific files were found in the folder.")

    # Select relevant files
    relevant_files = select_relevant_files(folder)
    for file in relevant_files:
        if file not in added_files:
            coder.add_rel_fname(file)
            added_files.append(file)
            io.tool_output(f"Relevant file added to the chat: {file}")

    def check_file_modified(file_path, last_modified_times):
        try:
            current_mtime = os.path.getmtime(file_path)
            if file_path not in last_modified_times or current_mtime > last_modified_times[file_path]:
                last_modified_times[file_path] = current_mtime
                return True
            return False
        except OSError as e:
            io.tool_error(f"Error while checking file {file_path}: {str(e)}")
            return False

    def add_analyses_files(coder, io, analyses_folder, last_modified_times):
        if analyses_folder.exists() and analyses_folder.is_dir():
            analyses_files = [f for f in analyses_folder.iterdir() if f.is_file()]
            io.tool_output("Adding/Updating files from the 'analyses' folder:")
            for file in analyses_files:
                try:
                    if check_file_modified(str(file), last_modified_times):
                        io.tool_output(f"Adding/Updating {file}")
                        coder.add_file(str(file))
                except Exception as e:
                    io.tool_error(f"Error while adding/updating file {file}: {str(e)}")
        else:
            io.tool_output("The 'analyses' folder doesn't exist or is not a directory. Continuing without it.")

    # Create the 'analyses' folder if it doesn't exist
    analyses_folder = Path(folder_path) / 'analyses'
    if not analyses_folder.exists():
        analyses_folder.mkdir(parents=True, exist_ok=True)
        io.tool_output(f"'analyses' folder created: {analyses_folder}")
    else:
        io.tool_output(f"'analyses' folder already exists: {analyses_folder}")
    
    # Add all files from the 'analyses' folder to the chat
    last_modified_times = {}
    try:
        add_analyses_files(coder, io, analyses_folder, last_modified_times)
    except Exception as e:
        io.tool_error(f"Error while adding analysis files: {str(e)}")

    # Check for new files
    try:
        # Check for new files
        new_files = coder.check_for_new_files()
        if new_files:
            io.tool_output("New files detected and added to the chat.")
    except Exception as e:
        io.tool_error(f"Error while checking for new files: {str(e)}")
        
    try:
        while True:
            # Read the content of the files
            files_to_read = {
                'demande': 'demande.md',
                'cdc': 'cdc.md',
                'todolist': 'todolist.md',
                'prompt': 'prompt.md',
                'sortie': 'sortie.md'
            }
            file_contents = {}

            for key, filename in files_to_read.items():
                file_path = Path(folder) / filename
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_contents[key] = f.read()
                else:
                    io.tool_error(f"The file {filename} doesn't exist in the folder {folder}.")
                    file_contents[key] = f"Content of {filename} not available"
        
            # Execute the detailed loop
            coder.run(with_message=f"""
            Context of the initial request ({folder}/demande.md):
            {file_contents['demande']}

            Global Specifications ({folder}/cdc.md):
            {file_contents['cdc']}

            List of tasks to be completed ({folder}/todolist.md):
            {file_contents['todolist']}

            General Prompt ({folder}/sortie.md):
            {file_contents['prompt']}

            Current content of the mission output ({folder}/sortie.md):
            {file_contents['sortie']}

            0. Take into account the user feedback in demande if present, or the mission completion feedback if present.

            For the next item of the todolist of the todolist that is not yet completed, apply the following process:
            1. If the prompt is not created, create a prompt.md file in a mirror directory structure of the steps presented in {folder}/todolist.md. This file should contain the prompt to execute the step in question.
            2. If the step is too complex for a single prompt, create a sub-folder with sub-steps.
            3. Execute the step following the prompt for the step. Make sure to actually do the work necessary to complete the step.
            4. Verify that the work done meets the CDC criteria for the step.
            5. If the criteria are not met, redo the step or break it down into sub-steps.
            6. Once the criteria are met, update the status of the step in {folder}/todolist.md.
            7. Repeat this process until all criteria of the global CDC are met (rendered in the file {folder}/`sortie.md`).
            """)

            # Check if the mission is completed
            completion_check = coder.run(with_message=f"""
            Specifications (CDC):
            {file_contents['cdc']}

            Current output:
            {file_contents['sortie']}

            Based on the CDC and the current output, is the mission completed according to the CDC criteria?
            Answer only with Mission completed?: YES or NO, followed by a detailed explanation, and a request to update the todolist.
            """)

            # Add the YES/NO response to the chat
            completion_response = "YES" if "YES" in completion_check.upper() else "NO"
            coder.cur_messages.append({"role": "assistant", "content": f"Mission completed?: {completion_response}"})

            if completion_response == "YES":
                io.tool_output("Mission completed according to the CDC criteria.")
                break
            else:
                io.tool_output("The mission is not yet completed. Continuing the process.")

        io.tool_output("Process completed.")

    except Exception as e:
        io.tool_error(f"An error occurred: {str(e)}")
    except SwitchCoder as switch:
        kwargs = dict(io=io, from_coder=coder)
        kwargs.update(switch.kwargs)
        if "show_announcements" in kwargs:
            del kwargs["show_announcements"]

        coder = Coder.create(**kwargs)

        if switch.kwargs.get("show_announcements") is not False:
            coder.show_announcements()
    except Exception as e:
        io.tool_error(f"An error occurred: {str(e)}")

    return coder if return_coder else 0


def load_slow_imports():
    # These imports are deferred in various ways to
    # improve startup time.
    # This func is called in a thread to load them in the background
    # while we wait for the user to type their first message.

    try:
        import httpx  # noqa: F401
        import litellm  # noqa: F401
        import networkx  # noqa: F401
        import numpy  # noqa: F401
    except Exception:
        pass


if __name__ == "__main__":
    status = main()
    sys.exit(status)
