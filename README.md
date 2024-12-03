# Python Runner

Ce repository contient le code et les fichiers nécessaires à l'utilisation de la library _Python Runner_.
Cette library a pour but de lancer de manière fiable une série de scripts python de différents projets, le tout avec une stratégie de logs persistants et également sous forme d'email (via une boite Outlook).

## Exemple

```python
import os

from python_runner import Runner
from python_runner.helpers import load_config

projects = [
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_1",
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_2",
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_3",
]

for project in projects:

    scripts, python_command, recipients, email_strategy, include_traceback, logs_backup_count = (
        load_config(project)
    )

    scripts_list = [os.path.join(project, script) for script in scripts]

    runner = Runner(project, recipients, logs_backup_count=logs_backup_count)
    
    runner.run(
        python_scripts=scripts_list,
        python_command=python_command,
        email_strategy=email_strategy,
        include_traceback=include_traceback,
    )
```

# Sommaire

- [Installation](#installation)
- [Utilisation](#utilisation)
  - [Configuration](#variables-de-configuation)
  - [Stratégie d'email](#email-strategy)
  - [Stratégie de logging](#logging-strategy)
- [Méthodes](#méthodes)

# Installation

1) Créer un environnement virtuel et l'activer

_Windows_
```bash
python -m venv .venv
.venv/Scripts/activate
```

_Linux_
```bash
python3 -m venv .venv
.venv/bin/activate
```

`(.venv)` devrait apparaître dans votre terminal, si c'est le cas, l'environnement virtuel est activé.

3) Installer la dépendance via pip

```bash
pip install git+https://github.com/Rayanworkout/python_runner.git
```

Si tout s'est bien passé, vous pouvez maintenant importer la librairie dans votre code.

Toutes les dépendances de la library sont présentes dans la library standard Python, hormis `python_dotenv` qui sera automatiquement installée.


## Variables d'environnement

Pour l'envoi de mails, 2 variables sont nécessaires. Si elles ne sont pas fournies, le programme lèvera une exception de type `MissingEnvironmentVariable`.
Ces 2 variables sont les suivantes: `LOGIN_MAIL` et `PASSWORD_MAIL`.

Notez que l'envoi de mail se fait par une adresse outlook à travers le port 587 du serveur `smtp.office365.com`. Je n'ai pas testé d'autres fournisseurs d'email, mais il suffira de modifier la dernière partie de la méthode `python_runner.__main__.__send_email()` pour utiliser votre propre manière d'envoyer des emails.

Un fichier `.env.example` est fourni. Il suffit de modifier les valeurs et de renommer le fichier en `.env`.


# Utilisation

Le fichier `example.py` contient un exemple d'utilisation de la librairie. Pour l'utiliser, il faudra cependant bien l'installer (ou cloner le repo) et créer les dossiers `project_1`, `project_2` et `project_3` avec pour chacun un ou plusieurs scripts ainsi que son fichier de configuration.

Pour que le runner puisse lancer l'ensemble des scripts d'un projet, certaines variables doivent **obligatoirement** figurer à l'intérieur d'un fichier `exec_config.json` à la racine du projet. Si ces variables ne sont pas **toutes** présentes, une exception sera levée. Un fichier `exec_config.example.json` est mis à disposition.

Pour obtenir ces variables, il est nécessaire d'utiliser la fonction `load_config` présente dans `python_runner.helpers.load_config`.

```python
from python_runner.helpers import load_config

# Utilisation de l'unpacking
scripts, python_command, recipients, email_strategy, include_traceback, logs_backup_count = (
    load_config(r"C:\Users\some_user\Desktop\Dev\python_runner\project_2")
)
```

### Variables de configuation

- `python_command: str`: la commande de l'interpréteur python à utiliser. Il est possible d'utiliser `"python"` pour l'interpréteur python global du système, ou mentionner celui d'un environnement virtuel (exemple: `.venv/Scripts/python`). Une exception de type `BadPythonInterpreter` sera levée si l'interpréteur n'est pas trouvé.

- `scripts: list[str]`: l'ensemble des scripts du projet qu'il sera nécessaire de lancer, **dans l'ordre d'exécution**. Cette variable est une liste de strings contenant le chemin d'accès absolu ou relatif de chaque fichier, en mentionnant le nom complet du fichier (avec `.py`). Exemple: `cycle_court/main_script.py`

- `recipients: list[str]`: la liste des destinataires pour l'email qui concerne ce projet. Une liste de strings comportant des adresses email valides. Notez que la réception d'email sera dépendante de la stratégie choisie.

- `email_strategy: str`: la stratégie d'emailing à suivre pour ce projet. Les valeurs possibles sont mentionnées [ici](#email-strategy).

- `include_traceback: bool`: un booléen qui détermine s'il sera nécessaire d'inclure le traceback de l'erreur dans les logs du projet. Attention, dans un fichier json, la syntaxe acceptée ne contient pas de majuscule, donc `true / false`.

- `logs_backup_count: int`: le nombre d'archives de fichiers de logs à conserver. Si la valeur est réglée à 0, **TOUTES** les archives sont conservées. Si par exemple cette variable est réglée sur 4, cela signifie que nous conservons 4 fichiers de logs en plus du fichier actuel. Le plus ancien est successivement supprimé. Autrement dit, nous gardons une durée de 4 fois le nombre de jours prévus dans la stratégie de rotation. Si `logs_backup_count = 4` et la stratégie de rotation est réglée sur 3 jours, cela signifie que nous conserverons continuellement les logs sur une durée de 12 jours, et que les plus anciens sont supprimés. La stratégie de logging est détaillée [ici](#logging-strategy).


Le runner passera à travers chaque projet et exécutera de manière séquentielle les scripts du projet mentionnés dans la variable `scripts` de sa configuration. Pour chacun, on monitore si l'exécution a été un succès ou un échec ainsi que son temps d'exécution.

Ensuite, on envoie un email aux destinataires présents dans la variable `recipients`du projet si la stratégie d'email le prévoit.

## Email Strategy
Les stratégies d'email disponibles sont les suivantes:

- `all`: on envoie à la fois les succès et les erreurs de chaque script du projet.
- `none`: aucun email n'est envoyé pour ce projet.
- `failure_only`: uniquement les scripts du projet qui n'ont pas été exécutés correctement sont mentionnés dans l'email.

## Logging Strategy

La stratégie de logging est basée sur la rotation temporelle, configurée avec la classe `TimedRotatingFileHandler` de Python.

La rotation des fichiers de logs s’effectue automatiquement tous les `3 jours`. Les fichiers de logs précédents sont conservés en fonction de la variable `logs_backup_count`. Chaque fichier de log est renommé avec un suffixe correspondant à la date à laquelle il a été archivé, par exemple `project_3.log.2024-11-28_09-25`.

Cela signifie que le fichier de log en cours contient les entrées des 3 derniers jours. Une fois cette limite dépassée, il est archivé et un nouveau fichier est créé.

Les logs sont enregistrés dans le dossier du projet lancé, à l'intérieur d'un dossier `logs` qui se situe à la racine (ex: `project_1/logs`).

Le format est le suivant:

- `Date et heure - Niveau de log - Machine qui lance le runner - ID unique du run - Durée d'exécution du script en minutes - Nom du script - statut (success / failure) - Traceback en cas de failure (optionnel)`

- `2024-11-27 09:51:58,954 - INFO - LAPTOP-BS85JNP7 - 39be3d37aed64 - 0.08 - main.py - success`

# Méthodes

## Initialisation de l'objet

Pour instancier le runner, certaines variables sont obligatoires, d'autres optionnelles.

### Obligatoires
- `project_path: str` représente le chemin d'accès absolu du dossier du projet. Puisque nous utilisons Windows, on préfèrera utiliser un _raw string_ pour éviter tout problème d'échappement. Par exemple `r"C:\Users\some_user\Desktop\Dev\email_sender_wrapper\project_1"` sera un chemin d'accès valide. `"C:\Users\stest\Desktop\Dev\email_sender_wrapper\new_project"` posera des problèmes à cause de `/s` et `\n`.


- `recipient_emails: list[str]` représente la liste des destinataires pour le projet mentionné dans la variable `project_path`.

- `backup_count: int >= 0` le nombre de backups de logs à garder. 0 signifie que l'on garde un nombre illimité de logs.

### Optionnelles

- `log_filename: str` représente le nom qui sera donné au fichier de logs du projet. Par défaut, le fichier de log est nommé selon le nom du projet. **Attention, ce nom ne peut pas être un chemin d'accès.**


```python
# Exemple d'initialisation manuelle
runner = Runner(
    project_path=r"C:\Users\some_user\Desktop\Dev\email_sender_wrapper\project_1",
    recipient_emails=["my_email@gmail.com"],
    log_filename=None,
    logs_backup_count=0 # garder TOUS les logs
    )
```


## run(python_scripts: list, python_command: str = None, email_strategy: ["all", "failure_only", "none"] = "all", include_traceback: bool = False) -> dict

- `python_scripts`: la liste des scripts à exécuter pour ce projet.

- `python_command`: la commande de l'intepréteur Python qui sera utilisé pour lancer les scripts du projet.

- `email_strategy`: la stratégie d'email à sélectionner pour ce projet. Les stratégies sont expliquées [ici](#email-strategy)

- `include_traceback`: Un booléen qui détermine si le traceback des éventuelles erreurs devra apparaître dans les logs du projet.

La méthode retourne une liste de dictionnaires qui contiennent pour chaque script son nom, le succès (booléen), le temps d'exécution en minute(s) et l'éventuel traceback.
