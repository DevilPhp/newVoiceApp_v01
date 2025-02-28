from app.extensions import db
from datetime import datetime
import uuid

class Chat(db.Model):
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    chatUuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    # userId = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255))
    createdAt = db.Column(db.DateTime, default=datetime.now)
    updatedAt = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    messages = db.relationship('Message', backref='chat', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Chat {self.id}: {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'chatUuid': self.chatUuid,
            'title': self.title,
            'createdAt': self.createdAt.isoformat(),
            'updatedAt': self.updatedAt.isoformat(),
            'messages': [message.to_dict() for message in self.messages],
        }