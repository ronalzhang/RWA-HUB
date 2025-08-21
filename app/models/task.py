from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
import enum

class TaskStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class TaskQueue(db.Model):
    __tablename__ = 'task_queue'

    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(128), nullable=False)
    task_args = db.Column(JSONB, nullable=True)
    status = db.Column(db.String(32), nullable=False, default=TaskStatus.PENDING.value, index=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def __repr__(self):
        return f'<TaskQueue {self.id} [{self.task_name}] - {self.status}>'
