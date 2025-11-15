from dataclasses import dataclass

from models.homework_status import HomeworkStatus


@dataclass
class HomeworkRecord:
    title: str
    publish_time: str | None
    teacher_name: str
    pass_score: float | None
    current_score: float | None
    total_score: float
    is_pass: bool | None
    teacher_comment: str | None
    status: HomeworkStatus | None
    due_time: str | None
    api_id: str | None = None
    api_task_id: str | None = None
    api_task_paper_id: str | None = None
    api_batch_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
