from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # hashed password

# --- Association Table for Tags ---
ticket_tags = db.Table('ticket_tags',
    db.Column('ticket_id', db.Integer, db.ForeignKey('repair_ticket.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

# --- Tag Model ---
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# --- Ticket Update Model ---
class TicketUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('repair_ticket.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    updated_by = db.Column(db.String(80), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Main Repair Ticket Model ---
class RepairTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    facility = db.Column(db.String(100))
    user = db.Column(db.String(100))
    device_type = db.Column(db.String(100))
    date_picked_up = db.Column(db.Date)
    issue = db.Column(db.Text)
    estimated_return_date = db.Column(db.Date)
    progress = db.Column(db.Text, default="")
    date_returned = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.String(80))
    updated_by = db.Column(db.String(80))

    # Relationships
    tags = db.relationship('Tag', secondary=ticket_tags, backref='tickets')
    updates = db.relationship('TicketUpdate', backref='ticket', cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "facility": self.facility,
            "user": self.user,
            "device_type": self.device_type,
            "date_picked_up": self.date_picked_up.strftime("%Y-%m-%d"),
            "issue": self.issue,
            "estimated_return_date": self.estimated_return_date.strftime("%Y-%m-%d"),
            "progress": self.progress,
            "date_returned": self.date_returned.strftime("%Y-%m-%d") if self.date_returned else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "tags": [tag.name for tag in self.tags]
        }
