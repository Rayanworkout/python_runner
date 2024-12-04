import os

from python_runner import Runner
from python_runner.helpers import load_config

projects = [
    r"./project_1"
    r"./project_2"
    r"./project_3"
]

for project in projects:

    (
        scripts,
        python_command,
        recipients,
        email_strategy,
        include_traceback,
        logs_backup_count,
    ) = load_config(project)

    scripts_list = [os.path.join(project, script) for script in scripts]

    runner = Runner(project, recipients, logs_backup_count=logs_backup_count)

    runner.run(
        python_scripts=scripts_list,
        python_command=python_command,
        email_strategy=email_strategy,
        include_traceback=include_traceback,
    )
