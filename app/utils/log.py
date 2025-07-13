from database.database import TableModel, connect_db
from sqlalchemy import Column, String
import logging
import os
from datetime import datetime
from utils.config import config
from logging.handlers import TimedRotatingFileHandler

PROJECT_NAME = config["project_name"]

# 定义日志模型
class LogEntry(TableModel):
    level = Column(String(10))
    message = Column(String(1000))
    project_name = Column(String(30))

# 自定义日志处理器
class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        message = self.format(record)

        message = ''.join(c for c in message if ord(c) <= 0xFFFF)
        
        if len(message) > 1000:
            ellipsis = " [...] "
            max_content_len = 1000 - len(ellipsis)
            
            head_len = int(max_content_len * 0.6)
            tail_len = max_content_len - head_len
            
            head_part = message[:head_len]
            tail_part = message[-tail_len:] if tail_len > 0 else ""
            
            message = head_part + ellipsis + tail_part
        
        message = message[:1000]
        
        # 创建日志条目
        LogEntry.create(
            level=record.levelname,
            message=message,
            project_name=PROJECT_NAME
        )

# 配置日志记录
def get_log():
    log_path = os.path.join(os.path.dirname(__file__), '..', '..', config['data_dir'], 'server.log')
    data_dir = os.path.dirname(log_path)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    level = logging.INFO if config['log_level'] == 'info' else logging.DEBUG

    # 创建一个logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # 创建一个TimedRotatingFileHandler，按天滚动日志
    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when='midnight',
        interval=1,
        backupCount=7,  # 保留最近7天的日志
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'))

    # 添加自定义的日志处理器
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(level)
    db_handler.setFormatter(logging.Formatter('%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'))

    # 将处理器添加到logger
    logger.addHandler(file_handler)
    logger.addHandler(db_handler)

    return logger

log = get_log()

if __name__ == '__main__':
    connect_db()

    log.info('test')

    for _log in LogEntry.query_all():
        level = _log.level
        message = _log.message
        timestamp = _log.create_time
        print(f'level: {level}, message: {message}, timestamp: {timestamp}')