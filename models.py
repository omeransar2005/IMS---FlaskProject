from flask_login import UserMixin
from app import db
from datetime import datetime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Relationships
    inventory_items = db.relationship('InventoryItem', backref='created_by', lazy=True)
    sales = db.relationship('Sale', backref='recorded_by', lazy=True)

    # Specify which foreign key to use for the relationship
    low_stock_alerts = db.relationship('LowStock',
                                       foreign_keys='LowStock.user_id',
                                       backref='notified_to',
                                       lazy=True)

    # Add a new relationship for alerts resolved by this user
    resolved_alerts = db.relationship('LowStock',
                                      foreign_keys='LowStock.resolved_by',
                                      backref='resolved_by_user',
                                      lazy=True)


class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    sales = db.relationship('Sale', backref='item', lazy=True)
    low_stock_alerts = db.relationship('LowStock', backref='item', lazy=True)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    price_at_sale = db.Column(db.Float, nullable=False)
    discount_at_sale = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class LowStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    threshold = db.Column(db.Integer, nullable=False, default=10)
    alert_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_date = db.Column(db.DateTime, nullable=True)