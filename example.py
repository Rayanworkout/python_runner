import os

from python_runner import Runner
from python_runner.helpers import load_config

projects = [
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_1",
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_2",
    r"C:\Users\some_user\Desktop\Dev\python_runner\project_3",
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
        email_strategy="none",
        include_traceback=include_traceback,
    )
