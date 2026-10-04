from django.conf import settings
from django.core.management.base import BaseCommand
from packaging import version as pyver

from agents.models import Agent
from agents.tasks import send_agent_update_task
from core.utils import get_core_settings, token_is_valid
from tacticalrmm.constants import AGENT_DEFER


class Command(BaseCommand):
    help = "Triggers an agent update task to run"

    def handle(self, *args, **kwargs):
        core = get_core_settings()
        if not core.agent_auto_update:
            return

        q = Agent.objects.defer(*AGENT_DEFER).exclude(version=settings.LATEST_AGENT_VER)

        # pa.co.it: solo auto-actualizamos plataformas con agente propio firmado
        plats = list(getattr(settings, "SELF_SIGNED_AGENTS", {}).keys())
        if plats:
            q = q.filter(plat__in=plats)

        # pa.co.it: hosts excluidos del auto-update
        excludes = getattr(settings, "AUTO_UPDATE_EXCLUDE_HOSTS", [])
        if excludes:
            q = q.exclude(hostname__in=excludes)

        agent_ids: list[str] = [
            i.agent_id
            for i in q
            if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
        ]
        token, _ = token_is_valid()
        send_agent_update_task.delay(agent_ids=agent_ids, token=token, force=False)
