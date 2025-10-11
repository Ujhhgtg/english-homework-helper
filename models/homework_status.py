from enum import Enum


class HomeworkStatus(Enum):
    COMPLETED = "已完成"
    IN_PROGRESS = "进行中"
    NOT_COMPLETED = "去完成"
    MAKE_UP = "补做"
