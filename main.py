import asyncio
import tracemalloc
import traceback
import sys
import subprocess
import logging
import configparser
import json
import os
import re
import threading
from pathlib import Path

import git
from git.exc import GitCommandError
from dotenv import load_dotenv
from prompt_toolkit.enums import EditingMode

from aider import __version__, models, utils
from aider.args import get_parser
from aider.coders import Coder
from aider.commands import Commands, SwitchCoder
from aider.history import ChatSummary
from aider.io import InputOutput
from aider.repo import GitRepo

# Handle potential import errors
try:
    from aider.llm import litellm  # noqa: F401; properly init litellm on launch
except ImportError:
    print("Error importing litellm. Please ensure you have the correct versions of openai and litellm installed.")
    print("You can update them by running: pip install -r requirements.txt")
    sys.exit(1)
import asyncio
import subprocess
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def install_playwright():
    logger.info("Starting Playwright installation")
    try:
        print("Installing Playwright...")
        # First, install the playwright package
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'install', 'playwright',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            print(f"Error installing playwright package: {stderr.decode()}")
            return

        # Then, install Playwright's dependencies
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print("Playwright and its dependencies installed successfully.")
        else:
            print(f"Error installing Playwright dependencies: {stderr.decode()}")
    except Exception as e:
        print(f"An error occurred while installing Playwright: {e}")

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None
    logger.warning("Playwright is not installed. Some features may not be available.")

try:
    from aider.gui import gui_main
except ImportError:
    gui_main = None
    logging.warning("PySimpleGUI is not installed. GUI features will be disabled.")
from aider.io import InputOutput

DEFAULT_MODEL_NAME = "gpt-4o-mini"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

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


def make_new_repo(git_root, io):
    try:
        repo = git.Repo.init(git_root)
        check_gitignore(git_root, io, False)
    except GitCommandError as err:  # issue #1233
        io.tool_error(f"Unable to create git repo in {git_root}")
        io.tool_output(str(err))
        return

    io.tool_output(f"Git repository created in {git_root}")
    return repo


def setup_git(git_root, io):
    repo = None

    if git_root:
        repo = git.Repo(git_root)
    elif Path.cwd() == Path.home():
        io.tool_warning("You should probably run aider in a directory, not your home dir.")
        return
    elif io.confirm_ask("No git repo found, create one to track aider's changes (recommended)?"):
        git_root = str(Path.cwd().resolve())
        repo = make_new_repo(git_root, io)

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
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

    if user_name and user_email:
        return repo.working_tree_dir

    with repo.config_writer() as git_config:
        if not user_name:
            git_config.set_value("user", "name", "Your Name")
            io.tool_warning('Update git name with: git config user.name "Your Name"')
        if not user_email:
            git_config.set_value("user", "email", "you@example.com")
            io.tool_warning('Update git email with: git config user.email "you@example.com"')

    return repo.working_tree_dir


def check_gitignore(git_root, io, ask=True):
    if not git_root:
        return

    try:
        repo = git.Repo(git_root)
        if repo.ignored(".aider"):
            return
    except GitCommandError:
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
            io.tool_output('The arg should be "language: cmd --args ..."')
            io.tool_output('For example: --lint-cmd "python: flake8 --select=E9"')
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


def sanity_check_repo(repo, io):
    if not repo:
        return True

    try:
        repo.get_tracked_files()
        return True
    except GitCommandError as exc:
        error_msg = str(exc)

        if "version in (1, 2)" in error_msg:
            io.tool_error("Aider only works with git repos with version number 1 or 2.")
            io.tool_output(
                "You may be able to convert your repo: git update-index --index-version=2"
            )
            io.tool_output("Or run aider --no-git to proceed without using git.")
            io.tool_output("https://github.com/paul-gauthier/aider/issues/211")
            return False

        io.tool_error("Unable to read git repository, it may be corrupt?")
        io.tool_output(error_msg)
        return False
    

def import_modules():
    try:
        from aider.file_selector import select_relevant_files
        from aider.args import get_parser
        from aider.coders import Coder
        from aider.commands import Commands, SwitchCoder
        from aider.history import ChatSummary
        from aider.io import InputOutput
        from aider.llm import litellm  # noqa: F401; properly init litellm on launch
        from aider.repo import GitRepo
        from aider.versioncheck import check_version
        from aider.dump import dump  # noqa: F401
        # Import the launch_gui function conditionally to avoid circular import
        return (select_relevant_files, get_parser, Coder, Commands, SwitchCoder, 
                ChatSummary, InputOutput, GitRepo, check_version)
    except ImportError as e:
        logger.error(f"Error importing modules: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
# Import modules
(select_relevant_files, get_parser, Coder, Commands, SwitchCoder, 
 ChatSummary, InputOutput, GitRepo, check_version) = import_modules()


async def main(argv=None, input=None, output=None, force_git_root=None, return_coder=False):
    logger.info("Starting main function")
    try:
        tracemalloc.start()
        logger.debug(f"Command line arguments: {sys.argv}")

        # Check if Playwright is installed
        if async_playwright:
            logger.info("Playwright is available, proceeding with installation")
            # Install Playwright
            await install_playwright()

            # Initialize Playwright
            logger.info("Initializing Playwright")
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
            logger.info("Playwright initialized successfully")
        else:
            logger.warning("Playwright is not installed. Some features may not be available.")

        # Check if --gui argument is present
        if argv is not None and '--gui' in argv:
            logger.info("GUI argument detected")
            if check_streamlit_install(InputOutput(pretty=True, yes=True)):
                logger.info("Launching GUI")
                return await launch_gui(argv)
            else:
                logger.warning("Streamlit not installed, cannot launch GUI")
                return 1

        # If Playwright is not available, we can still continue with other functionalities
        if not async_playwright:
            logger.info("Continuing without Playwright. Some features may be limited.")

        if force_git_root:
            git_root = force_git_root
        else:
            git_root = get_git_root()
        logger.info(f"Git root: {git_root}")

        conf_fname = Path(".aider.conf.yml")

        default_config_files = [conf_fname.resolve()]  # CWD
        if git_root:
            git_conf = Path(git_root) / conf_fname  # git root
            if git_conf not in default_config_files:
                default_config_files.append(git_conf)
        default_config_files.append(Path.home() / conf_fname)  # homedir
        default_config_files = list(map(str, default_config_files))
        logger.debug(f"Default config files: {default_config_files}")

        parser = get_parser(default_config_files, git_root)
        args, unknown = parser.parse_known_args(argv)
        logger.debug(f"Parsed arguments: {args}")
        logger.debug(f"Unknown arguments: {unknown}")

        role = getattr(args, 'role', None)
        message = args.message
        request = getattr(args, 'request', None)
        append_request = getattr(args, 'append_request', None)
        new_request_provided = request is not None

        if argv is not None and '--folder' in argv:
            folder = args.folder
            folder_path = os.path.abspath(folder)
            logger.info(f"Working with folder: {folder_path}")
        else:
            logger.info("No specific folder provided. Working in the current directory.")
            folder_path = os.getcwd()
            folder = "./"

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
            # Check if the role file exists, if not create it
            role_file_path = os.path.join(folder_path, 'role.md')
            if not os.path.exists(role_file_path):
                default_role_text = "Act as an expert developer and writer."
                os.makedirs(os.path.dirname(role_file_path), exist_ok=True)
                with open(role_file_path, 'w', encoding='utf-8') as role_file:
                    role_file.write(default_role_text)
                logger.info(f"Created role file with default content: {role_file_path}")
                io.tool_output(f"Created role file: {role_file_path}")
            # Check if the request is already present in the folder
            request_file = Path(folder_path) / 'request.md'
            if request_file.exists():
                logger.info(f"Request file exists: {request_file}")
                try:
                    with open(request_file, 'r', encoding='utf-8') as f:
                        existing_request = f.read().strip()
                    if request is None:
                        request = existing_request
                        logger.info("Using existing request")
                    elif request.strip() == existing_request:
                        io.tool_output("The request is identical to the one already present. No need to regenerate the specifications.")
                        logger.info("Request is identical, skipping regeneration")
                    else:
                        # Save the new request
                        with open(request_file, 'w', encoding='utf-8') as f:
                            f.write(request)
                        io.tool_output(f"New request saved to {request_file}")
                        logger.info(f"New request saved to {request_file}")
                except Exception as e:
                    logger.error(f"Error reading or writing request file: {e}")
                    io.tool_error(f"Error processing request file: {e}")
            elif request is not None:
                # Create a request.md file with the provided request
                try:
                    with open(request_file, 'w', encoding='utf-8') as f:
                        f.write(request)
                    io.tool_output(f"Created a request file: {request_file}")
                    logger.info(f"Created request file: {request_file}")
                except Exception as e:
                    logger.error(f"Error creating request file: {e}")
                    io.tool_error(f"Error creating request file: {e}")

            # Generate new only if a new request is provided via command line
            if new_request_provided:
                try:
                    from .generation import generation
                    logger.info("Generating specifications, todolist...")
                    specifications, todolist = generation(folder_path, request, role="default")
                    io.tool_output(f"Specifications, todolist generated for the folder: {folder_path}")
                    logger.info("Specifications, todolist generated")
                except Exception as e:
                    logger.error(f"Error generating specifications: {e}")
                    io.tool_error(f"Error generating specifications: {e}")
            else:
                logger.info("No new request provided via command line, skipping specification generation")

            # Add the append_request to the end of the request file if it's present
            if append_request:
                try:
                    with open(request_file, 'a', encoding='utf-8') as f:
                        f.write(f"\n\n{append_request}")
                    io.tool_output(f"Append request added to the end of the request file: {request_file}")
                    logger.info(f"Append request added to {request_file}")
                except Exception as e:
                    logger.error(f"Error appending request to request file: {e}")
                    io.tool_error(f"Error appending request to request file: {e}")
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
            from .llm import litellm

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

        try:
            while True:
                # Add specific files from the folder
                specific_files = ['todolist.md', 'specifications.md']
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
                if folder:
                    folder_path = os.path.abspath(folder)
                    io.tool_output(f"Using folder path: {folder_path}")
                    relevant_files = select_relevant_files(folder_path, role="default")
                    for file in relevant_files:
                        if file and file not in added_files:
                            try:
                                coder.add_rel_fname(str(file))
                                added_files.append(file)
                                io.tool_output(f"Relevant file added to the chat: {file}")
                            except Exception as e:
                                io.tool_error(f"Error adding file {file}: {str(e)}")
                else:
                    io.tool_error("Folder is not specified. Cannot select relevant files.")

                # Read the content of the files
                files_to_read = {
                    'request': 'request.md',
                    'role': 'role.md',
                    'specifications': 'specifications.md',
                    'todolist': 'todolist.md',
                    'output': 'output.md'
                }
                file_contents = {}

                for key, filename in files_to_read.items():
                    if filename in ['role.md']:
                        file_path = Path(role) / filename
                    else:
                        file_path = Path(folder) / filename
                    try:
                        if file_path.exists():
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_contents[key] = f.read()
                        else:
                            if filename == 'output.md':
                                # Create output.md if it doesn't exist
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write("")  # Create an empty file
                                file_contents[key] = ""
                                io.tool_output(f"Created empty {filename} in the folder {folder}.")
                            elif filename == 'role.md':
                                file_contents[key] = "Act as an expert developer and writer."
                                io.tool_output(f"Default content set for {filename} as it doesn't exist in the folder {folder}.")
                            else:
                                io.tool_error(f"The file {filename} doesn't exist in the folder {folder}.")
                                file_contents[key] = f"Content of {filename} not available"
                                logger.error(f"File not found: {file_path}")
                    except Exception as e:
                        io.tool_error(f"Error reading file {filename}: {str(e)}")
                        file_contents[key] = f"Error reading content of {filename}"
                        logger.error(f"Error reading file {file_path}: {str(e)}")

                # Execute the detailed loop
                logger.info("Starting task execution process")
                result = coder.run(with_message=f"""
                You are an expert developer and writer tasked with completing a project. Your role and context are defined in the following files:
                I) Role ({role}/role.md):
                {file_contents['role']}          
                II) Initial Request ({folder}/request.md):
                {file_contents['request']}
                III) Global Specifications ({folder}/specifications.md):
                {file_contents['specifications']}
                IV) Tasks to Complete ({folder}/todolist.md):
                {file_contents['todolist']}
                V) Current Mission Output ({folder}/output.md):
                {file_contents['output']}
                Process for completing tasks. YOU MUST EXECUTE ALL ACTIONS IN ONE RESPONSE:
                0. Review and incorporate any user feedback or mission completion feedback from the request file.
                For the first uncompleted task of the todolist:
                5. **Execute the task**, using the SEARCH / REPLACE format.
                6. Verify the work is explicitly visible in the output, not just marked as complete.
                7. Confirm the outcome matches the task specifications and the work process is visible.
                8. If the outcome is not achieved or work is not fully visible, revise the task or break it down further.
                9. Update the task status in {folder}/todolist.md upon successful completion.
                Remember: Avoid hallucinations. Only report on actions you've actually taken and results you can verify.
                """)

                # Choose and run a terminal command
                command_choice = coder.run(with_message=f"""
                Based on the current state of the project, choose a terminal command to run.
                Consider the following context:
                Role: {file_contents['role']}
                Request: {file_contents['request']}
                Specifications: {file_contents['specifications']}
                Todolist: {file_contents['todolist']}
                Current output: {file_contents['output']}
                Repository structure:
                {coder.get_repo_map()}
                Choose a terminal command that would be most helpful for progressing the project.
                The command should be an appropriate shell command for the current operating system.
                Provide a brief explanation of why you chose this command.
                Your response should be in the format:
                Command: <your_chosen_command>
                Explanation: <your_explanation>
                """)

                # Extract the command from the response
                command_lines = command_choice.split('\n')
                chosen_command = None
                for line in command_lines:
                    if line.startswith("Command:"):
                        chosen_command = line.split("Command:")[1].strip()
                        break

                if chosen_command:
                    io.tool_output(f"Executing command: {chosen_command}")
                    try:
                        import subprocess
                        import shlex

                        # Split the command into arguments, respecting quoted strings
                        command_args = shlex.split(chosen_command)

                        # Execute the command
                        result = subprocess.run(command_args, check=True, capture_output=True, text=True, cwd=folder_path)
                        io.tool_output(f"Command output:\n{result.stdout}")
                        if result.stderr:
                            io.tool_error(f"Command error output:\n{result.stderr}")
                    except subprocess.CalledProcessError as e:
                        io.tool_error(f"Command execution failed: {e}")
                        io.tool_error(f"Error output:\n{e.stderr}")
                    except Exception as e:
                        io.tool_error(f"An error occurred while executing the command: {str(e)}")
                else:
                    io.tool_error("No valid command was chosen.")

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
            print(f"An error occurred: {str(e)}", file=sys.stderr)
            if 'io' in locals():
                io.tool_error(f"An error occurred: {str(e)}")
        finally:
            tracemalloc.stop()

    except Exception as e:
        logger.error(f"An error occurred in main: {str(e)}")
        logger.error(traceback.format_exc())
        io.tool_error(f"An error occurred: {str(e)}")

    return coder if return_coder else 0

async def install_playwright():
    try:
        print("Installing Playwright...")
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'install', 'playwright',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print("Playwright package installed successfully.")
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                print("Playwright browser installed successfully.")
            else:
                print(f"Error installing Playwright browser: {stderr.decode()}")
        else:
            print(f"Error installing Playwright package: {stderr.decode()}")
    except Exception as e:
        print(f"An error occurred while installing Playwright: {e}")

async def async_main():
    try:
        tracemalloc.start()

        print("Debug: Command line arguments:", sys.argv)  # Debug print

        # Install Playwright
        await install_playwright()

        # Check if --gui argument is present
        if '--gui' in sys.argv:
            print("Debug: GUI argument detected")  # Debug print
            io = InputOutput(pretty=True, yes=True)
            if gui_main is None:
                print("Error: PySimpleGUI is not installed. Please install it to use the GUI feature.")
                return 1
            else:
                print("Debug: PySimpleGUI is installed, launching GUI")  # Debug print
                # Run the GUI
                return await launch_gui(sys.argv)
        else:
            print("Debug: Running CLI version")  # Debug print
            # Run the regular CLI version
            return await main(sys.argv[1:])
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Error details: {traceback.format_exc()}")
        return 1

def check_streamlit_install(io):
    try:
        import streamlit
        return True
    except ImportError:
        io.tool_error("Streamlit is not installed. Please install it to use the GUI feature.")
        io.tool_output("You can install it by running: pip install streamlit")
        return False

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"An error occurred in __main__: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
