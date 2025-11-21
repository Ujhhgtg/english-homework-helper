from enum import Enum


# TODO: figure out what the `None`s are
class HomeworkStatus(Enum):
    COMPLETED = (4, "已完成")
    IN_PROGRESS = (1, "进行中")
    NOT_COMPLETED = (0, "去完成")
    MAKE_UP = (None, "补做")
    UNKNOWN = (None, "未知")
