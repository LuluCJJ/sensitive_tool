"""脱敏日志记录模块"""
import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict

from config import LOG_DIR


@dataclass
class RedactionLogEntry:
    """单条脱敏记录"""
    rule_id: str
    rule_name: str
    original_text: str
    location: str  # 位置描述，如 "第3段" 或 "Sheet1!B5"
    match_type: str
    trigger: str = ''  # 新增字段：具体是由哪个正则表达式或标签触发的


@dataclass
class RedactionLog:
    """单个文件的脱敏日志"""
    filename: str
    file_type: str
    start_time: str = ''
    end_time: str = ''
    status: str = 'pending'  # pending, success, error
    error_message: str = ''
    entries: list = field(default_factory=list)
    output_path: str = ''

    def add_entry(self, entry: RedactionLogEntry):
        self.entries.append(entry)

    @property
    def redaction_count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> dict:
        return {
            'filename': self.filename,
            'file_type': self.file_type,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'error_message': self.error_message,
            'redaction_count': self.redaction_count,
            'output_path': self.output_path,
            'entries': [asdict(e) for e in self.entries],
        }


class RedactionLogger:
    """脱敏日志管理器"""

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        self.session_logs: list[RedactionLog] = []

    def create_log(self, filename: str, file_type: str) -> RedactionLog:
        """创建一个文件的脱敏日志"""
        log = RedactionLog(
            filename=filename,
            file_type=file_type,
            start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        self.session_logs.append(log)
        return log

    def finish_log(self, log: RedactionLog, status: str = 'success',
                   error_message: str = '', output_path: str = ''):
        """完成一个文件的脱敏日志"""
        log.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.status = status
        log.error_message = error_message
        log.output_path = output_path

    def save_session(self) -> str:
        """保存本次会话的所有日志到文件，返回文件路径"""
        if not self.session_logs:
            return ''

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(self.log_dir, f'redaction_log_{timestamp}.json')

        data = {
            'session_time': timestamp,
            'total_files': len(self.session_logs),
            'total_redactions': sum(log.redaction_count for log in self.session_logs),
            'files': [log.to_dict() for log in self.session_logs],
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return log_file

    def load_history(self) -> list[dict]:
        """加载历史日志文件列表"""
        logs = []
        if not os.path.exists(self.log_dir):
            return logs

        for fname in sorted(os.listdir(self.log_dir), reverse=True):
            if fname.startswith('redaction_log_') and fname.endswith('.json'):
                filepath = os.path.join(self.log_dir, fname)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    data['log_file'] = filepath
                    logs.append(data)
                except (json.JSONDecodeError, IOError):
                    pass
        return logs
