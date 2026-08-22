"""
Gestion des notifications Airflow.
Alertes en cas d'échec des tâches.
"""
from airflow.utils.log.logging_mixin import LoggingMixin

logger = LoggingMixin().log


def task_failure_callback(context):
    """
    Callback appelé lorsqu'une tâche échoue.
    Log l'erreur et prépare l'envoi d'alerte (email/Slack à configurer).
    """
    task_instance = context.get("task_instance")
    dag_id = context.get("dag").dag_id
    task_id = task_instance.task_id
    execution_date = context.get("execution_date")
    exception = context.get("exception")
    log_url = task_instance.log_url
    
    message = f"""
    ❌ ÉCHEC DE TÂCHE AIRFLOW
    ═══════════════════════════════════════════
    DAG           : {dag_id}
    Tâche         : {task_id}
    Date exec     : {execution_date}
    Erreur        : {str(exception)[:500]}
    Lien logs     : {log_url}
    ═══════════════════════════════════════════
    """
    
    logger.error(message)
    
    # TODO : Configurer l'envoi d'email quand SMTP prêt
    # TODO : Ajouter notification Slack si besoin
    return message


def task_success_callback(context):
    """
    Callback appelé lorsqu'une tâche réussit.
    Utile pour logger le succès des tâches critiques.
    """
    task_instance = context.get("task_instance")
    dag_id = context.get("dag").dag_id
    task_id = task_instance.task_id
    duration = task_instance.duration
    
    logger.info(
        f"✅ Tâche réussie : {dag_id}.{task_id} "
        f"(durée: {duration:.1f}s)"
    )


def dag_success_callback(context):
    """Callback appelé lorsqu'un DAG entier réussit."""
    dag_id = context.get("dag").dag_id
    execution_date = context.get("execution_date")
    logger.info(f"🎉 DAG '{dag_id}' terminé avec succès à {execution_date}")


def dag_failure_callback(context):
    """Callback appelé lorsqu'un DAG entier échoue."""
    dag_id = context.get("dag").dag_id
    execution_date = context.get("execution_date")
    logger.error(f"💥 DAG '{dag_id}' a échoué à {execution_date}")