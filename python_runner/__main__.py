import logging
import os
import shutil
import smtplib
import socket
import subprocess
import time

from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import TimedRotatingFileHandler
from typing import Union, Tuple, Literal, List
from uuid import uuid4

from .exceptions import (
    MissingEnvironmentVariable,
    BadRecipientList,
    BadPythonInterpreter,
)


class Runner:
    def __init__(
        self,
        project_path: str,
        recipient_emails: list,
        log_filename: str = None,
        logs_backup_count: int = 0,
    ):
        load_dotenv()
        # Obtenir les variables d'environnement nécessaires en utilisant l'unpacking
        (
            self.__USER_EMAIL,
            self.__USER_PASSWORD,
        ) = self.__check_and_get_env_variables()

        if not isinstance(project_path, str) or len(project_path) < 1:
            raise ValueError(
                f'"{project_path}" est incorrect, merci de fournir un nom de projet valide.'
            )

        if not os.path.exists(project_path):
            raise ValueError(f"Le dossier {project_path} n'existe pas.")
        
        if not os.path.isdir(project_path):
            raise ValueError(f"Le chemin {project_path} n'est pas un dossier.")

        if not isinstance(logs_backup_count, int):
            raise ValueError(
                f"logs_backup_count doit être un entier. Projet: {self.project_name}"
            )

        if logs_backup_count < 0:
            raise ValueError(
                f"logs_backup_count doit être un entier positif. Projet: {self.project_name}"
            )

        self.logs_backup_count = logs_backup_count
        self.project_path = project_path
        self.project_name = os.path.basename(os.path.abspath(self.project_path))

        # Vérifier si la liste des personnes recevant l'email est fournie
        if not isinstance(recipient_emails, list):
            raise BadRecipientList(
                f"La variable recipient_emails doit être une liste. Projet: {self.project_name}"
            )

        self.recipient_emails = recipient_emails
        self.log_filename = log_filename

        self.logger = logging.getLogger(self.project_name)

        if not self.logger.handlers:
            self.__generate_logger()

    ############ PUBLIC METHODS ############
    def run(
        self,
        python_scripts: list,
        python_command: str = None,
        email_strategy: Literal["all", "failure_only", "none"] = "all",
        include_traceback: bool = False,
    ) -> List[dict]:
        """
        Fonction qui permet de lancer une liste de scripts python avec une commande spécifique.
        Le log se fait automatiquement en fonction de l'exit code renvoyé par le script python.
        Pour rappel, un exit code de 0 signifie que le script a réussi son exécution, tout autre
        code signifie que le script a échoué.

        Une fois les scripts lancés, la méthode __send_email() est appelée pour notifier les résultats.

        Args:
            python_scripts (list): La liste des scripts python à exécuter.
            python_command (str, optional): La commande d'appel de l'interpreteur python, il peut être
            l'installation globale ou l'intepréteur d'un environnement virtuel.
            email_strategy (str, optional): La stratégie d'envoi d'email pour les résultats.
            include_traceback (bool, optional): Indique si le traceback doit être inclus dans les logs.
        """

        if python_command is None:
            raise ValueError(
                f"Merci de mentionner une commande d'appel de l'interpréteur python. Projet: {self.project_name}"
            )

        # Commande pour vérifier si l'interpréteur est valide
        if shutil.which(python_command) is None:
            raise BadPythonInterpreter(
                f"{python_command} n'est pas un interpréteur valide, merci de vérifier votre configuration."
            )

        if not isinstance(email_strategy, str):
            raise ValueError(
                f"L'argument 'email_strategy' doit être une chaîne de caractères. Projet: {self.project_name}"
            )

        email_strategy = email_strategy.lower()

        if email_strategy not in ["all", "failure_only", "none"]:
            raise ValueError(
                f"L'argument 'email_strategy' doit être 'all', 'failure_only', ou 'none'. Projet: {self.project_name}"
            )

        if not self.recipient_emails and email_strategy != "none":
            raise ValueError(
                f'La stratégie d\'email doit être "none" car la liste des destinataires est vide. Projet: {self.project_name}'
            )

        # Générer un ID unique pour ce run
        run_id = str(uuid4()).replace("-", "")[:13]

        results = []

        # Je vérifie si tous les scripts existent avant de commencer le run.
        for script in python_scripts:
            if not os.path.exists(script):
                script = os.path.basename(script)
                raise FileNotFoundError(
                    f'{self.project_name}: "{script}" est mentionné dans le fichier de configuration mais n\'existe pas.'
                )

        global_start = time.time()

        for script in python_scripts:
            start = time.time()

            try:
                script_name = os.path.basename(script)
                subprocess.run([python_command, script], check=True)
                end = time.time()
                # J'évite d'utiliser des accents dans mes logs
                # pour éviter des problèmes d'encoding / traitement
                execution_time = (end - start) / 60
                self.logger.info(
                    f"{run_id} - {execution_time:.2f} - {script_name} - success"
                )
                results.append(
                    {
                        "script": script_name,
                        "success": True,
                        "execution_time": execution_time,
                    }
                )

            except subprocess.CalledProcessError as e:
                end = time.time()
                execution_time = (end - start) / 60
                error_msg = e.stderr.decode("utf-8").replace("\n", "")
                results.append(
                    {
                        "script": script_name,
                        "success": False,
                        "traceback": error_msg,
                        "execution_time": execution_time,
                    }
                )

                log_msg = f"{run_id} - {execution_time:.2f} - {script_name} - failure"
                if include_traceback is True:
                    log_msg += f"- {error_msg}"

                self.logger.error(log_msg)

        global_end = time.time()

        # Envoyer un email avec les informations de succès et d'erreurs
        self.__send_email(results, strategy=email_strategy)

        # Séparateur pour facilement repérer les blocks
        self.logger.info("-" * 15)

        print(
            f'\nLe run "{run_id}" de {self.project_name} s\'est déroulé avec succès en {(global_end - global_start) / 60:.2f} minute(s).'
        )
        return results

    ####### INTERNAL METHODS ############
    def __send_email(
        self,
        run_results: dict,
        strategy: Literal["all", "failure_only", "none"] = "all",
    ) -> None:

        # Si la strégie est none, je n'envoie rien, je met fin à la fonction
        if strategy == "none":
            return

        error_scripts = [
            e.get("script") for e in run_results if e.get("success") is False
        ]

        if not error_scripts and strategy == "failure_only":
            return

        success_scripts = [
            e.get("script") for e in run_results if e.get("success") is True
        ]

        message = MIMEMultipart()

        if error_scripts:
            message["Subject"] = (
                f"{self.project_name.capitalize()} a rencontré une ou plusieurs erreur(s)."
            )
            message_body = f'Une ou plusieurs erreurs ont été détectées dans les scripts de "{self.project_name}" :\n'
            for script in success_scripts:
                message_body += f"\n - {script} ✅"

            for script in error_scripts:
                message_body += f"\n - {script} ❌"

        else:
            message["Subject"] = (
                f"Le projet a tourné avec succès ({self.project_name.capitalize()})."
            )
            message_body = f'Tous les scripts de "{self.project_name}" ont été lancés avec succès.\n'
            for script in success_scripts:
                message_body += f"\n - {script} ✅"

        # ======
        # Envoi de l'e-mail
        # ======
        message["From"] = self.__USER_EMAIL
        message["To"] = ", ".join(self.recipient_emails)
        message.attach(MIMEText(message_body, "plain"))

        with smtplib.SMTP("smtp.office365.com", 587) as server:
            server.starttls()
            server.login(self.__USER_EMAIL, self.__USER_PASSWORD)
            server.sendmail(
                self.__USER_EMAIL, self.recipient_emails, message.as_string()
            )
            server.quit()

            print(f"\nE-mail envoyé avec succès à {', '.join(self.recipient_emails)}")

    def __check_and_get_env_variables(self) -> Union[Tuple[str, str, str], ValueError]:
        """
        Cette fonction vérifie et retourne les variables d'environnement nécessaires.

        Raises:
            ValueError: Si les variables d'environnement ne sont pas définies.

        Returns:
            Tuple[str, str] -- Un tuple contenant les variables d'environnement nécessaires.
        """
        __LOGIN_MAIL = os.getenv("LOGIN_MAIL")
        __PASSWORD_MAIL = os.getenv("PASSWORD_MAIL")

        mapping = {
            "LOGIN_MAIL": __LOGIN_MAIL,
            "PASSWORD_MAIL": __PASSWORD_MAIL,
        }

        for key, value in mapping.items():
            if value is None:
                raise MissingEnvironmentVariable(
                    f"La variable d'environnement \"{key}\" n'est pas définie.\n"
                    "Merci de définir toutes les variables d'environnement nécessaires."
                )

        return (
            __LOGIN_MAIL,
            __PASSWORD_MAIL,
        )

    def __generate_logger(self):
        """
        Méthode permettant de générer dynamiquement un logger pour chaque projet.
        Instancier un nouveau runner avec sa propre logging.basicConfig() ne suffit pas
        car le logger n'est configuré qu'une fois par process.

        J'utilise donc cette méthode pour écrire dans des fichiers de logs séparés pour chaque projet.

        Le TimedRotatingFileHandler est utilisé pour la stratégie de rotation des logs.
        La stratégie de rotation est détaillée dans le README de la lib.
        """

        # On stocke les logs de chaque projet à l'intérieur d'un dossier logs
        project_logs_dir_path = os.path.join(self.project_path, "logs")

        # Création du dossier logs s'il n'existe pas
        os.makedirs(project_logs_dir_path, exist_ok=True)

        # Nom du fichier (nom de projet ou custom)
        if self.log_filename is None:
            self.log_filename = f"{self.project_name}.log"
        else:
            if not self.log_filename.endswith(".log"):
                self.log_filename += ".log"

            self.log_filename = os.path.relpath(self.log_filename)

        # Stratégie de rotation des logs
        handler = TimedRotatingFileHandler(
            filename=os.path.join(project_logs_dir_path, self.log_filename),
            when="d",
            interval=7,
            backupCount=self.logs_backup_count,
            encoding="utf-8",
        )

        handler.setLevel(logging.DEBUG)

        # Nom de la machine hôte
        _hostname = socket.gethostname()

        formatter = logging.Formatter(
            f"%(asctime)s - %(levelname)s - {_hostname} - %(message)s",
        )
        formatter.datefmt = "%d-%m-%Y %H:%M:%S"

        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
