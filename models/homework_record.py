from dataclasses import dataclass

from models.homework_status import HomeworkStatus


@dataclass
class HomeworkRecord:
    """Represents a single record from the homework table."""

    title: str | None
    start_time: str | None
    end_time: str | None
    teacher: str | None
    pass_score: str | None
    current_score: str | None
    total_score: str | None
    is_pass: str | None
    teacher_comment: str | None
    status: HomeworkStatus | None
