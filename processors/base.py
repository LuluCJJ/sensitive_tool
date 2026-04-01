"""处理器基类"""
from abc import ABC, abstractmethod

from core.scanner import Scanner
from core.logger import RedactionLog, RedactionLogEntry


class BaseProcessor(ABC):
    """文件处理器基类"""

    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    @abstractmethod
    def process(self, input_path: str, output_path: str, log: RedactionLog) -> bool:
        """处理文件，执行脱敏

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            log: 脱敏日志对象

        Returns:
            是否成功
        """
        pass

    def _add_log_entry(self, log: RedactionLog, rule_id: str, rule_name: str,
                       original_text: str, location: str, match_type: str,
                       trigger: str = ''):
        """添加一条脱敏日志"""
        log.add_entry(RedactionLogEntry(
            rule_id=rule_id,
            rule_name=rule_name,
            original_text=original_text,
            location=location,
            match_type=match_type,
            trigger=trigger,
        ))
