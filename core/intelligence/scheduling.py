from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class DailySchedule:
    collect_at: time = time(6, 30)
    cutoff_at: time = time(7, 50)
    digest_at: time = time(8, 0)
    timezone: ZoneInfo = SHANGHAI

    def moments(self, day: date) -> dict[str, datetime]:
        return {
            "collect": datetime.combine(day, self.collect_at, self.timezone),
            "cutoff": datetime.combine(day, self.cutoff_at, self.timezone),
            "digest": datetime.combine(day, self.digest_at, self.timezone),
        }

    def article_window(self, day: date) -> tuple[int, int]:
        previous_day = day - timedelta(days=1)
        start = datetime.combine(previous_day, self.cutoff_at, self.timezone)
        cutoff = datetime.combine(day, self.cutoff_at, self.timezone)
        return int(start.timestamp()) + 1, int(cutoff.timestamp())

    def next_run(self, now: datetime | None = None) -> dict[str, datetime]:
        now = (now or datetime.now(self.timezone)).astimezone(self.timezone)
        result: dict[str, datetime] = {}
        for name, moment in self.moments(now.date()).items():
            result[name] = moment if moment > now else moment + timedelta(days=1)
        return result


DEFAULT_SCHEDULE = DailySchedule()
