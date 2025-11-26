from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False, index=True)
    categoria = db.Column(db.String(100), nullable=False, default='Sin Categoría')
    subcategoria = db.Column(db.String(100), nullable=True)
    precio_venta = db.Column(db.Float, nullable=False)
    proveedor = db.Column(db.String(100), default='Sin Proveedor')
    estado = db.Column(db.String(50), default='Disponible')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'Nombre': self.nombre,
            'Categoria': self.categoria,
            'SubCAT': self.subcategoria,
            'Precio Venta': self.precio_venta,
            'Proveedor': self.proveedor,
            'Estado': self.estado
        }
    
    def __repr__(self):
        return f'<Producto {self.nombre}>'

class Venta(db.Model):
    __tablename__ = 'ventas'
    
    id = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora = db.Column(db.Time, nullable=False)
    id_cliente = db.Column(db.String(50), nullable=False)
    producto_nombre = db.Column(db.String(255), nullable=False, index=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    total_venta = db.Column(db.Float, nullable=False)
    vendedor = db.Column(db.String(50), nullable=False)
    id_terminal = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'ID_Venta': self.id_venta,
            'Fecha': str(self.fecha),
            'Hora': str(self.hora),
            'ID_Cliente': self.id_cliente,
            'Producto': self.producto_nombre,
            'Cantidad': self.cantidad,
            'Precio_Unitario': self.precio_unitario,
            'Total_Venta': self.total_venta,
            'Vendedor': self.vendedor,
            'ID_Terminal': self.id_terminal
        }
    
    def __repr__(self):
        return f'<Venta {self.id_venta} - {self.producto_nombre}>'

class Contador(db.Model):
    __tablename__ = 'contadores'
    
    id = db.Column(db.Integer, primary_key=True)
    terminal = db.Column(db.String(10), unique=True, nullable=False)
    ultimo_cliente = db.Column(db.Integer, default=0)
    ultima_venta = db.Column(db.Integer, default=0)
    total_ventas = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'ultimo_cliente': self.ultimo_cliente,
            'ultima_venta': self.ultima_venta,
            'total_ventas': self.total_ventas
        }
    
    def __repr__(self):
        return f'<Contador {self.terminal}>'
