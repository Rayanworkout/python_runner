import json
import os

from .exceptions import MissingConfigurationVariable

CONFIG_FILE = "exec_config.json"

MANDATORY_VARS = [
    "scripts",
    "python_command",
    "recipients",
    "email_strategy",
    "include_traceback",
    "logs_backup_count",
]


def load_config(project: str) -> list:
    """
    Méthode permettant de charger et retourner les variables nécessaires depuis
    le fichier de configuration d'un projet.
    
    Pour rendre une variable obligatoire, il suffit de l'ajouter à la liste MANDATORY_VARS.

    Args:
        project (str): Le chemin d'accès absolu du projet.

    Raises:
        MissingConfigurationVariable: Lorsqu'une variable du fichier de configuration est manquante.
        FileNotFoundError: Lorsque le fichier de configuration n'est pas trouvé ou n'existe pas.
        json.JSONDecodeError: Lorsque le contenu du fichier de configuration est invalide.

    Returns:
        list: La liste des variables de configuration, dans le même ordre que la liste MANDATORY_VARS.
    """
    try:
        config_file_path = os.path.join(project, CONFIG_FILE)

        with open(config_file_path, "r") as file:
            config = json.load(file)

            for var in MANDATORY_VARS:
                if var not in config:
                    raise MissingConfigurationVariable(
                        f"{project}\\{config_file_path} ne contient pas la variable {var}."
                    )

            return [config.get(var) for var in MANDATORY_VARS]

    except FileNotFoundError:
        raise FileNotFoundError(
            f"{config_file_path} n'existe pas. Merci de créer le fichier de configuration."
        )

    except json.JSONDecodeError:
        raise json.JSONDecodeError(
            f"Le format du fichier JSON est incorrect. {config_file_path}"
        )
