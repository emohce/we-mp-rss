from __future__ import annotations

from datetime import datetime

from sqlalchemy import inspect

from core.config import cfg
from core.db import DB
from core.intelligence.events import MqttPublisher, NullPublisher, RedisCoordinator
from core.intelligence.collector import CollectionWorker
from core.intelligence.jobs import JobRepository
from core.intelligence.outbox import OutboxDispatcher, OutboxRepository
from core.intelligence.providers import WeMpRssCollectorAdapter
from core.intelligence.rate_limit import RateLimitRepository
from core.intelligence.scheduling import SHANGHAI
from core.intelligence.settings import InfrastructureSettings, StorageProfile
from core.intelligence.workflow import (
    DailyAutomationScheduler,
    WorkflowJobRepository,
    WorkflowWorker,
)
from core.print import print_info, print_warning
from core.task import TaskScheduler


_scheduler = TaskScheduler()
_started = False
_publisher = None


def _runtime(settings: InfrastructureSettings, collector_enabled: bool):
    coordinator = RedisCoordinator(settings.redis_url) if settings.redis_url else None
    collection_jobs = JobRepository(DB.session_factory)
    workflow_jobs = WorkflowJobRepository(DB.session_factory)
    automation = DailyAutomationScheduler(
        session_factory=DB.session_factory,
        collection_jobs=collection_jobs,
        workflow_jobs=workflow_jobs,
    )
    workflow_worker = WorkflowWorker(
        session_factory=DB.session_factory,
        repository=workflow_jobs,
    )
    collection_worker = None
    if collector_enabled:
        collection_worker = CollectionWorker(
            session_factory=DB.session_factory,
            jobs=collection_jobs,
            rate_limits=RateLimitRepository(DB.session_factory, coordinator),
            adapters={
                "we-mp-rss": WeMpRssCollectorAdapter(session_factory=DB.session_factory),
            },
        )
    outbox_repository = OutboxRepository(DB.session_factory, coordinator)
    if settings.profile is StorageProfile.DISTRIBUTED:
        publisher = MqttPublisher(settings.mqtt_url, settings.mqtt_topic_prefix)
    else:
        publisher = NullPublisher()
    return (
        automation,
        collection_worker,
        workflow_worker,
        OutboxDispatcher(outbox_repository, publisher),
        publisher,
    )


def start_intelligence_jobs() -> bool:
    """Start idempotent job materialization and database-backed workers."""

    global _started, _publisher
    if _started:
        return True
    settings = InfrastructureSettings.from_env(cfg.get)
    settings_issues = settings.validate()
    if settings_issues:
        print_warning("智能聚合任务未启动：" + "；".join(settings_issues))
        return False
    required_tables = {
        "int_workspaces",
        "int_workspace_memberships",
        "int_collection_jobs",
        "int_workflow_jobs",
        "int_outbox_events",
    }
    available_tables = set(inspect(DB.get_engine()).get_table_names())
    missing = sorted(required_tables - available_tables)
    if missing:
        print_warning(
            "智能聚合任务未启动：请先执行 v2 数据库迁移，缺少表 " + ", ".join(missing)
        )
        return False

    collector_enabled = bool(cfg.get("intelligence.collector_enabled", False))
    automation, collection_worker, workflow_worker, outbox_dispatcher, _publisher = _runtime(
        settings, collector_enabled
    )

    def materialize_today() -> None:
        result = automation.schedule_day(
            datetime.now(SHANGHAI).date(),
            include_collection=collector_enabled,
        )
        print_info(f"智能聚合日程已物化: {result}")

    def drain_workflows() -> None:
        for _ in range(50):
            if workflow_worker.run_once() == "idle":
                break

    def drain_collection() -> None:
        if collection_worker is None:
            return
        for _ in range(10):
            if collection_worker.run_once() == "idle":
                break

    def drain_outbox() -> None:
        for _ in range(100):
            if not outbox_dispatcher.dispatch_once():
                break

    materialize_today()
    _scheduler.add_cron_job(
        materialize_today,
        cron_expr="7 * * * *",
        job_id="intelligence-materialize",
        tag="智能聚合日程",
    )
    _scheduler.add_cron_job(
        drain_workflows,
        cron_expr="* * * * *",
        job_id="intelligence-workflows",
        tag="智能聚合工作流",
    )
    if collection_worker is not None:
        _scheduler.add_cron_job(
            drain_collection,
            cron_expr="* * * * *",
            job_id="intelligence-collection",
            tag="智能聚合采集",
        )
    _scheduler.add_cron_job(
        drain_outbox,
        cron_expr="* * * * *",
        job_id="intelligence-outbox",
        tag="智能聚合事件箱",
    )
    _scheduler.start()
    _started = True
    print_info(
        "智能聚合后台任务已启动；采集器=" + ("启用" if collector_enabled else "关闭")
    )
    return True


def stop_intelligence_jobs() -> None:
    global _started, _publisher
    if not _started:
        return
    _scheduler.shutdown(wait=True)
    close = getattr(_publisher, "close", None)
    if callable(close):
        close()
    _publisher = None
    _started = False
