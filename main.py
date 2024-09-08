import configparser
import os
import re
import sys
import threading
from pathlib import Path

from aider import __version__, models, utils
import git
from dotenv import load_dotenv
from prompt_toolkit.enums import EditingMode

DEFAULT_MODEL_NAME = "gpt-4o-mini"  # ou le modèle par défaut que vous souhaitez utiliser

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

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

    folder = args.folder
    demande = args.demande

    if folder is None:
        print("Usage: python -m aider --folder <folder> [--demande <demande>]")
        return 1

    # Définir folder_path ici
    folder_path = os.path.abspath(folder)

    # Créer l'objet io
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

    # Vérifier si la demande est déjà présente dans le dossier
    demande_file = Path(folder_path) / 'demande.md'
    if demande_file.exists():
        with open(demande_file, 'r', encoding='utf-8') as f:
            existing_demande = f.read().strip()
        if demande is None:
            demande = existing_demande
        elif demande.strip() == existing_demande:
            io.tool_output("La demande est identique à celle déjà présente. Pas besoin de régénérer le CDC.")
        else:
            # Import generation module here to avoid circular import
            from .generation import generer_cdc
            cdc, todolist, prompt = generer_cdc(folder_path, demande)
            io.tool_output(f"Cahier des charges, liste des tâches et prompt générés pour le dossier : {folder_path}")
    elif demande is None:
        io.tool_error("Erreur : Aucune demande fournie et aucune demande existante dans le dossier.")
        return 1
    else:
        # Import generation module here to avoid circular import
        from .generation import generer_cdc
        cdc, todolist, prompt = generer_cdc(folder_path, demande)
        io.tool_output(f"Cahier des charges, liste des tâches et prompt générés pour le dossier : {folder_path}")

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

    # Créer l'objet coder
    # Définir le modèle par défaut si aucun n'est spécifié
    model_name = args.model or DEFAULT_MODEL_NAME
    
    coder = Coder.create(
        main_model=models.Model(model_name),
        edit_format=args.edit_format,
        io=io,
        repo=None,  # Nous n'utilisons pas de repo Git ici
        fnames=[],  # Nous ajouterons les fichiers plus tard
        read_only_fnames=[],
        show_diffs=args.show_diffs,
        auto_commits=False,  # Pas de commits automatiques
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

    # Ajout des fichiers spécifiques du dossier
    specific_files = ['todolist.md', 'cdc.md', 'prompt.md']
    added_files = []

    for file in specific_files:
        file_path = Path(folder) / file
        if file_path.exists():
            coder.add_rel_fname(str(file_path))
            added_files.append(str(file_path))
            io.tool_output(f"Fichier {file} ajouté au chat.")
        else:
            io.tool_output(f"Fichier {file} non trouvé dans le dossier.")

    if added_files:
        io.tool_output("Fichiers ajoutés au chat : " + ", ".join(added_files))
    else:
        io.tool_output("Aucun fichier spécifique n'a été trouvé dans le dossier.")

    # Sélection des fichiers pertinents
    relevant_files = select_relevant_files(folder)
    for file in relevant_files:
        if file not in added_files:
            coder.add_rel_fname(file)
            added_files.append(file)
            io.tool_output(f"Fichier pertinent ajouté au chat : {file}")

    def check_file_modified(file_path, last_modified_times):
        try:
            current_mtime = os.path.getmtime(file_path)
            if file_path not in last_modified_times or current_mtime > last_modified_times[file_path]:
                last_modified_times[file_path] = current_mtime
                return True
            return False
        except OSError as e:
            io.tool_error(f"Erreur lors de la vérification du fichier {file_path}: {str(e)}")
            return False

    def add_analyses_files(coder, io, analyses_folder, last_modified_times):
        if analyses_folder.exists() and analyses_folder.is_dir():
            analyses_files = [f for f in analyses_folder.iterdir() if f.is_file()]
            io.tool_output("Ajout/Mise à jour des fichiers du dossier 'analyses':")
            for file in analyses_files:
                try:
                    if check_file_modified(str(file), last_modified_times):
                        io.tool_output(f"Ajout/Mise à jour de {file}")
                        coder.add_file(str(file))
                except Exception as e:
                    io.tool_error(f"Erreur lors de l'ajout/mise à jour du fichier {file}: {str(e)}")
        else:
            io.tool_output("Le dossier 'analyses' n'existe pas ou n'est pas un répertoire. Continuons sans.")

    # S'assurer que le dossier principal existe
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        io.tool_output(f"Dossier principal créé: {folder_path}")
    else:
        io.tool_output(f"Dossier principal existant: {folder_path}")


    # Création du dossier 'analyses' s'il n'existe pas
    analyses_folder = Path(folder_path) / 'analyses'
    if not analyses_folder.exists():
        analyses_folder.mkdir(parents=True, exist_ok=True)
        io.tool_output(f"Dossier 'analyses' créé: {analyses_folder}")
    else:
        io.tool_output(f"Dossier 'analyses' existant: {analyses_folder}")
    
    # Ajout de tous les fichiers du dossier 'analyses' au chat
    last_modified_times = {}
    try:
        add_analyses_files(coder, io, analyses_folder, last_modified_times)
    except Exception as e:
        io.tool_error(f"Erreur lors de l'ajout des fichiers d'analyses : {str(e)}")

    # Vérification des nouveaux fichiers
    try:
        # Vérification des nouveaux fichiers
        new_files = coder.check_for_new_files()
        if new_files:
            io.tool_output("Nouveaux fichiers détectés et ajoutés au chat.")
    except Exception as e:
        io.tool_error(f"Erreur lors de la vérification des nouveaux fichiers : {str(e)}")
        
    try:
        while True:
            # Lire le contenu des fichiers
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
                    io.tool_error(f"Le fichier {filename} n'existe pas dans le dossier {folder}.")
                    file_contents[key] = f"Contenu de {filename} non disponible"
        
            # Exécuter la boucle détaillée
            coder.run(with_message=f"""
            Contexte de la demande initiale ({folder}/demande.md) :
            {file_contents['demande']}

            Cahier des Charges global ({folder}/cdc.md) :
            {file_contents['cdc']}

            Liste des tâches à réaliser ({folder}/todolist.md) :
            {file_contents['todolist']}

            Prompt Général ({folder}/sortie.md) :
            {file_contents['prompt']}

            Contenu actuel de la sortie de la mission ({folder}/sortie.md) :
            {file_contents['sortie']}

            Pour chaque étape du de la todolist encore non-complétée, applique le processus suivant:
            1. Pour les prompts non-crées, crée un fichier prompt.md dans une arborescence miroir des étapes présentées dans {folder}/todolist.md. Ce fichier doit contenir le prompt pour exécuter l'étape en question.
            2. Si l'étape est trop complexe pour un seul prompt, crée un sous-dossier avec des sous-étapes
            3. Exécute l'étape en suivant le prompt de l'étape. Assure-toi de vraiment réaliser le travail nécessaire à la completion de l'étape
            4. Vérifie que le travail effectué remplit bien les critères du CDC pour l'étape
            5. Si les critères ne sont pas remplis, recommence l'étape ou décompose-la en sous-étapes
            6. Une fois les critères remplis, mets à jour le statut de l'étape dans {folder}/todolist.md
            7. Répète ce processus jusqu'à ce que tous les critères du CDC global soient remplis (rendu dans le fichier {folder}/`sortie.md`)
            """)

            # Vérifier si la mission est terminée
            completion_check = coder.run(with_message=f"""
            Cahier des charges (CDC) :
            {file_contents['cdc']}

            Sortie actuelle :
            {file_contents['sortie']}

            En vous basant sur le CDC et la sortie actuelle, la mission est-elle terminée selon les critères du CDC ?
            Répondez uniquement par Mission terminée ? : OUI ou NON, suivi d'une explication détaillée.
            """)

            #TODO: ajouter la réponse oui non au chat

            if "OUI" in completion_check.upper():
                io.tool_output("Mission terminée selon les critères du CDC.")
                break
            else:
                io.tool_output("La mission n'est pas encore terminée. Continuation du processus.")

        io.tool_output("Processus terminé.")

    except Exception as e:
        io.tool_error(f"Une erreur s'est produite : {str(e)}")
    except SwitchCoder as switch:
        kwargs = dict(io=io, from_coder=coder)
        kwargs.update(switch.kwargs)
        if "show_announcements" in kwargs:
            del kwargs["show_announcements"]

        coder = Coder.create(**kwargs)

        if switch.kwargs.get("show_announcements") is not False:
            coder.show_announcements()
    except Exception as e:
        io.tool_error(f"Une erreur s'est produite : {str(e)}")

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
