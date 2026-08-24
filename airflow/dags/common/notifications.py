"""
Gestion centralisée des notifications Airflow.

Notifications :
    - Échec d'une tâche
    - Succès d'un DAG
    - Échec d'un DAG
"""

from airflow.utils.email import send_email
from airflow.utils.log.logging_mixin import LoggingMixin

from common.constants import DEFAULT_ARGS


logger = LoggingMixin().log


# Email destinataire
EMAIL_TO = DEFAULT_ARGS["email"]


# ============================================================
# ÉCHEC D'UNE TÂCHE
# ============================================================

def task_failure_callback(context):
    """
    Callback appelé lorsqu'une tâche échoue.
    """

    task_instance = context.get("task_instance")
    dag = context.get("dag")
    exception = context.get("exception")

    dag_id = dag.dag_id if dag else "N/A"
    task_id = task_instance.task_id if task_instance else "N/A"

    logical_date = context.get("logical_date")

    log_url = task_instance.log_url if task_instance else ""

    message = f"""
     ÉCHEC DE TÂCHE AIRFLOW

    DAG        : {dag_id}
    Tâche      : {task_id}
    Date       : {logical_date}
    Erreur     : {str(exception)[:1000]}
    Logs       : {log_url}
    """

    logger.error(message)

    # Email
    send_email(
        to=EMAIL_TO,
        subject=f" Airflow - Échec tâche : {dag_id}.{task_id}",
        html_content=f"""
        <html>
        <body>

            <h2 style="color:red;">
                 Échec d'une tâche Airflow
            </h2>

            <p>
                <strong>DAG :</strong> {dag_id}
            </p>

            <p>
                <strong>Tâche :</strong> {task_id}
            </p>

            <p>
                <strong>Date :</strong> {logical_date}
            </p>

            <p>
                <strong>Erreur :</strong>
            </p>

            <pre>{str(exception)[:1000]}</pre>

            <p>
                <a href="{log_url}">
                     Consulter les logs Airflow
                </a>
            </p>

            <hr>

            <p>
                <strong>SRM Souss-Massa - Data Platform</strong>
            </p>

        </body>
        </html>
        """
    )


# ============================================================
# SUCCÈS D'UNE TÂCHE
# ============================================================

def task_success_callback(context):
    """
    Callback appelé lorsqu'une tâche réussit.

    Attention :
    Ce callback n'envoie PAS d'email pour éviter
    de recevoir un email pour chaque tâche.
    """

    task_instance = context.get("task_instance")
    dag = context.get("dag")

    dag_id = dag.dag_id if dag else "N/A"
    task_id = task_instance.task_id if task_instance else "N/A"

    duration = task_instance.duration if task_instance else None

    logger.info(
        f" Tâche réussie : {dag_id}.{task_id} "
        f"(durée: {duration}s)"
    )


# ============================================================
# SUCCÈS DU DAG
# ============================================================

def dag_success_callback(context):
    """
    Callback appelé lorsqu'un DAG entier réussit.
    Envoie un email.
    """

    dag = context.get("dag")
    dag_run = context.get("dag_run")

    dag_id = dag.dag_id if dag else "N/A"

    logical_date = (
        dag_run.logical_date
        if dag_run
        else context.get("logical_date")
    )

    run_id = dag_run.run_id if dag_run else "N/A"

    logger.info(
        f" DAG '{dag_id}' terminé avec succès "
        f"à {logical_date}"
    )

    send_email(
        to=EMAIL_TO,
        subject=f" Airflow - DAG réussi : {dag_id}",
        html_content=f"""
        <html>
        <body>

            <h2 style="color:green;">
                 DAG exécuté avec succès
            </h2>

            <p>
                <strong>DAG :</strong> {dag_id}
            </p>

            <p>
                <strong>Run ID :</strong> {run_id}
            </p>

            <p>
                <strong>Date :</strong> {logical_date}
            </p>

            <p>
                <strong>État :</strong>
                <span style="color:green;">
                    SUCCESS
                </span>
            </p>

            <hr>

            <p>
                 Le pipeline ETL s'est terminé
                correctement.
            </p>

            <p>
                <strong>
                    SRM Souss-Massa - Data Platform
                </strong>
            </p>

        </body>
        </html>
        """
    )

# ============================================================
# ÉCHEC DU DAG
# ============================================================

def dag_failure_callback(context):
    """
    Callback appelé lorsqu'un DAG entier échoue.
    Envoie un email.
    """

    dag = context.get("dag")
    dag_run = context.get("dag_run")
    task_instance = context.get("task_instance")

    dag_id = dag.dag_id if dag else "N/A"

    logical_date = (
        dag_run.logical_date
        if dag_run
        else context.get("logical_date")
    )

    run_id = dag_run.run_id if dag_run else "N/A"
    task_id = (
        task_instance.task_id
        if task_instance
        else "N/A"
    )

    exception = context.get("exception")

    log_url = (
        task_instance.log_url
        if task_instance
        else ""
    )

    logger.error(
        f" DAG '{dag_id}' a échoué "
        f"à {logical_date}"
    )

    send_email(
        to=EMAIL_TO,
        subject=f" Airflow - DAG échoué : {dag_id}",
        html_content=f"""
        <html>
        <body>
            <h2 style="color:red;">
                 ÉCHEC DU DAG
            </h2>

            <p>
                <strong>DAG :</strong> {dag_id}
            </p>

            <p>
                <strong>Tâche en erreur :</strong> {task_id}
            </p>

            <p>
                <strong>Run ID :</strong> {run_id}
            </p>

            <p>
                <strong>Date :</strong> {logical_date}
            </p>

            <p>
                <strong>État :</strong>
                <span style="color:red;">
                    FAILED
                </span>
            </p>

            <hr>

            <p>
                <strong>Erreur :</strong>
            </p>

            <pre>{str(exception)[:1500]}</pre>

            <p>
                <a href="{log_url}">
                     Consulter les logs Airflow
                </a>
            </p>

            <hr>

            <p>
                 Une intervention peut être nécessaire.
            </p>

            <p>
                <strong>
                    SRM Souss-Massa - Data Platform
                </strong>
            </p>

        </body>
        </html>
        """
    )

