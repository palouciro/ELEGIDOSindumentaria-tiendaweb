import os, json
from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, Numeric, Boolean
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'elegidos-secret-2024')
CORS(app, supports_credentials=True)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///elegidos.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── MODELOS ──────────────────────────────────────────────
class Producto(db.Model):
    __tablename__ = 'productos'
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, default='')
    precio      = db.Column(db.Numeric, nullable=False)
    talles      = db.Column(db.Text, default='[]')   # JSON string
    link_pago   = db.Column(db.Text, default='')
    foto        = db.Column(db.Text, default='')
    emoji       = db.Column(db.String(10), default='👕')
    creado_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'nombre':      self.nombre,
            'descripcion': self.descripcion,
            'precio':      float(self.precio),
            'talles':      json.loads(self.talles),
            'link_pago':   self.link_pago,
            'foto':        self.foto,
            'emoji':       self.emoji,
        }

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id           = db.Column(db.String(50), primary_key=True)
    fecha        = db.Column(db.String(50), nullable=False)
    nombre       = db.Column(db.String(100))
    apellido     = db.Column(db.String(100))
    email        = db.Column(db.String(200))
    telefono     = db.Column(db.String(50))
    direccion    = db.Column(db.String(200))
    localidad    = db.Column(db.String(100))
    provincia    = db.Column(db.String(100), default='')
    cp           = db.Column(db.String(20), default='')
    notas        = db.Column(db.Text, default='')
    items        = db.Column(db.Text, default='[]')  # JSON string
    total        = db.Column(db.Numeric, default=0)
    estado       = db.Column(db.String(100), default='Pendiente')
    entregado    = db.Column(db.Boolean, default=False)
    monto_pagado = db.Column(db.Numeric, nullable=True)
    estado_monto = db.Column(db.String(50), default='')
    payment_id   = db.Column(db.String(100), default='')
    creado_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'fecha':        self.fecha,
            'nombre':       self.nombre,
            'apellido':     self.apellido,
            'email':        self.email,
            'telefono':     self.telefono,
            'direccion':    self.direccion,
            'localidad':    self.localidad,
            'provincia':    self.provincia,
            'cp':           self.cp,
            'notas':        self.notas,
            'items':        json.loads(self.items),
            'total':        float(self.total) if self.total else 0,
            'estado':       self.estado,
            'entregado':    self.entregado,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else None,
            'estado_monto': self.estado_monto,
            'payment_id':   self.payment_id,
        }

class Config(db.Model):
    __tablename__ = 'config'
    clave = db.Column(db.String(50), primary_key=True)
    valor = db.Column(db.Text, default='')

def init_db():
    db.create_all()
    # Valores por defecto
    if not Config.query.get('admin_pass'):
        db.session.add(Config(clave='admin_pass', valor='Elegidos#2024!Ropa'))
    if not Config.query.get('mp_token'):
        db.session.add(Config(clave='mp_token', valor=''))
    db.session.commit()

# ── PÁGINA PRINCIPAL ─────────────────────────────────────
_HTML = '<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>ELEGIDOS.Indumentaria</title>\n<style>\n  :root {\n    --celeste: #4FC3F7; --celeste-dark: #0288D1; --celeste-light: #E1F5FE;\n    --celeste-mid: #29B6F6; --blanco: #ffffff; --gris-fondo: #f0f4f8;\n    --gris-borde: #dde3ea; --gris-texto: #5a6475; --negro-suave: #1a2332;\n    --rojo: #e53935; --font: \'Segoe UI\', system-ui, sans-serif;\n  }\n  * { box-sizing: border-box; margin: 0; padding: 0; }\n  body { font-family: var(--font); background: var(--gris-fondo); color: var(--negro-suave); }\n  header { background: linear-gradient(135deg, var(--celeste-dark) 0%, var(--celeste-mid) 60%, var(--celeste) 100%); position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 12px rgba(2,136,209,0.18); }\n  .header-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 14px 24px; }\n  .logo-wrap { display: flex; align-items: center; gap: 14px; }\n  .logo-circle { width: 52px; height: 52px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.15); flex-shrink: 0; }\n  .logo-circle svg { width: 36px; height: 36px; }\n  .logo-text h1 { font-size: 22px; font-weight: 700; color: white; letter-spacing: 1px; }\n  .logo-text p { font-size: 11px; color: rgba(255,255,255,0.82); letter-spacing: 2px; text-transform: uppercase; }\n  .header-actions { display: flex; gap: 10px; align-items: center; }\n  .btn-header { background: rgba(255,255,255,0.18); border: 1.5px solid rgba(255,255,255,0.5); color: white; padding: 8px 16px; border-radius: 22px; cursor: pointer; font-size: 13px; font-weight: 600; transition: background .2s; display: flex; align-items: center; gap: 6px; }\n  .btn-header:hover { background: rgba(255,255,255,0.3); }\n  .btn-cart { background: white; border: none; color: var(--celeste-dark); padding: 8px 18px; border-radius: 22px; cursor: pointer; font-size: 13px; font-weight: 700; transition: all .2s; display: flex; align-items: center; gap: 7px; }\n  .btn-cart:hover { background: var(--celeste-light); }\n  .cart-badge { background: var(--rojo); color: white; border-radius: 50%; width: 20px; height: 20px; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; }\n  nav { background: var(--blanco); border-bottom: 1.5px solid var(--gris-borde); display: flex; justify-content: center; gap: 6px; padding: 10px 24px; }\n  .nav-btn { background: none; border: 1.5px solid transparent; padding: 7px 20px; border-radius: 20px; cursor: pointer; font-size: 13px; font-weight: 600; color: var(--gris-texto); transition: all .2s; }\n  .nav-btn.active, .nav-btn:hover { background: var(--celeste-light); color: var(--celeste-dark); border-color: var(--celeste); }\n  .page { display: none; max-width: 1200px; margin: 0 auto; padding: 28px 24px; }\n  .page.active { display: block; }\n  .hero { background: linear-gradient(120deg, var(--celeste-dark), var(--celeste)); border-radius: 18px; padding: 48px 40px; color: white; margin-bottom: 32px; display: flex; align-items: center; justify-content: space-between; overflow: hidden; position: relative; }\n  .hero::after { content: \'\'; position: absolute; right: -60px; top: -60px; width: 300px; height: 300px; border-radius: 50%; background: rgba(255,255,255,0.07); }\n  .hero h2 { font-size: 36px; font-weight: 800; margin-bottom: 10px; }\n  .hero p { font-size: 16px; opacity: .88; max-width: 400px; line-height: 1.6; }\n  .section-title { font-size: 20px; font-weight: 700; margin-bottom: 20px; color: var(--negro-suave); display: flex; align-items: center; gap: 10px; }\n  .section-title::before { content: \'\'; display: block; width: 4px; height: 22px; background: var(--celeste); border-radius: 4px; }\n  .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }\n  .product-card { background: white; border-radius: 14px; overflow: hidden; border: 1.5px solid var(--gris-borde); transition: all .22s; cursor: pointer; }\n  .product-card:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(2,136,209,0.13); border-color: var(--celeste); }\n  .product-img { width: 100%; height: 220px; background: var(--celeste-light); display: flex; align-items: center; justify-content: center; font-size: 64px; overflow: hidden; }\n  .product-img img { width: 100%; height: 100%; object-fit: cover; }\n  .product-info { padding: 14px 16px; }\n  .product-name { font-size: 15px; font-weight: 700; margin-bottom: 4px; }\n  .product-desc { font-size: 12px; color: var(--gris-texto); margin-bottom: 10px; line-height: 1.5; }\n  .product-price { font-size: 22px; font-weight: 800; color: var(--celeste-dark); margin-bottom: 12px; }\n  .talles-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }\n  .talle-btn { border: 1.5px solid var(--gris-borde); background: white; padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s; color: var(--gris-texto); }\n  .talle-btn.selected { background: var(--celeste-dark); border-color: var(--celeste-dark); color: white; }\n  .btn-agregar { width: 100%; background: var(--celeste-dark); color: white; border: none; border-radius: 10px; padding: 11px; font-size: 14px; font-weight: 700; cursor: pointer; transition: background .2s; }\n  .btn-agregar:hover { background: var(--celeste-mid); }\n  .cart-panel { display: none; position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: white; z-index: 200; box-shadow: -4px 0 24px rgba(0,0,0,0.14); flex-direction: column; }\n  .cart-panel.open { display: flex; }\n  .cart-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 199; }\n  .cart-overlay.open { display: block; }\n  .cart-header { background: var(--celeste-dark); color: white; padding: 18px 20px; display: flex; justify-content: space-between; align-items: center; }\n  .cart-header h3 { font-size: 17px; font-weight: 700; }\n  .cart-close { background: none; border: none; color: white; font-size: 22px; cursor: pointer; }\n  .cart-body { flex: 1; overflow-y: auto; padding: 16px; }\n  .cart-empty { text-align: center; color: var(--gris-texto); padding: 40px 20px; font-size: 15px; }\n  .cart-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--gris-borde); align-items: flex-start; }\n  .cart-item-img { width: 60px; height: 60px; border-radius: 8px; background: var(--celeste-light); display: flex; align-items: center; justify-content: center; font-size: 28px; flex-shrink: 0; overflow: hidden; }\n  .cart-item-img img { width: 100%; height: 100%; object-fit: cover; }\n  .cart-item-info { flex: 1; }\n  .cart-item-name { font-size: 14px; font-weight: 700; margin-bottom: 2px; }\n  .cart-item-talle { font-size: 12px; color: var(--gris-texto); margin-bottom: 4px; }\n  .cart-item-price { font-size: 15px; font-weight: 800; color: var(--celeste-dark); }\n  .cart-item-qty { display: flex; align-items: center; gap: 8px; margin-top: 6px; }\n  .qty-btn { background: var(--gris-fondo); border: 1px solid var(--gris-borde); width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; }\n  .cart-item-del { background: none; border: none; cursor: pointer; color: var(--rojo); font-size: 18px; }\n  .cart-footer { padding: 16px 20px; border-top: 2px solid var(--gris-borde); }\n  .cart-total { display: flex; justify-content: space-between; font-size: 18px; font-weight: 800; margin-bottom: 14px; }\n  .btn-comprar { width: 100%; background: #00b900; color: white; border: none; border-radius: 12px; padding: 15px; font-size: 16px; font-weight: 800; cursor: pointer; transition: background .2s; }\n  .btn-comprar:hover { background: #009900; }\n  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 300; align-items: center; justify-content: center; }\n  .modal-overlay.open { display: flex; }\n  .modal { background: white; border-radius: 18px; padding: 32px; width: 94%; max-width: 480px; max-height: 90vh; overflow-y: auto; }\n  .modal h3 { font-size: 20px; font-weight: 800; margin-bottom: 6px; }\n  .modal-sub { color: var(--gris-texto); font-size: 13px; margin-bottom: 24px; }\n  .form-group { margin-bottom: 16px; }\n  .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--gris-texto); }\n  .form-group input, .form-group textarea { width: 100%; border: 1.5px solid var(--gris-borde); border-radius: 10px; padding: 11px 14px; font-size: 14px; font-family: var(--font); transition: border .2s; background: white; color: var(--negro-suave); }\n  .form-group input:focus, .form-group textarea:focus { outline: none; border-color: var(--celeste-dark); }\n  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }\n  .resumen-compra { background: var(--celeste-light); border-radius: 12px; padding: 16px; margin-bottom: 20px; }\n  .resumen-compra h4 { font-size: 14px; font-weight: 700; margin-bottom: 10px; color: var(--celeste-dark); }\n  .resumen-item { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }\n  .resumen-total { display: flex; justify-content: space-between; font-size: 16px; font-weight: 800; border-top: 1.5px solid var(--celeste); padding-top: 10px; margin-top: 10px; color: var(--celeste-dark); }\n  .btn-mp { width: 100%; background: #009EE3; color: white; border: none; border-radius: 12px; padding: 15px; font-size: 16px; font-weight: 800; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; }\n  .btn-mp:hover { background: #007db3; }\n  .btn-cancelar { width: 100%; background: none; border: 1.5px solid var(--gris-borde); border-radius: 12px; padding: 12px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 10px; color: var(--gris-texto); }\n  .btn-cancelar:hover { background: var(--gris-fondo); }\n  .admin-grid { display: grid; grid-template-columns: 340px 1fr; gap: 24px; }\n  .admin-card { background: white; border-radius: 14px; padding: 24px; border: 1.5px solid var(--gris-borde); }\n  .admin-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }\n  .admin-product-item { display: flex; align-items: center; gap: 12px; padding: 10px; border: 1px solid var(--gris-borde); border-radius: 10px; margin-bottom: 10px; overflow: hidden; }\n  .orders-list { display: flex; flex-direction: column; gap: 14px; }\n  .order-card { background: white; border-radius: 12px; border: 1.5px solid var(--gris-borde); overflow: hidden; }\n  .order-header { background: var(--celeste-light); padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; }\n  .order-header strong { font-size: 14px; color: var(--celeste-dark); }\n  .order-status { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 12px; background: #e8f5e9; color: #2e7d32; }\n  .order-body { padding: 14px 16px; }\n  .order-body p { font-size: 13px; margin-bottom: 4px; }\n  .order-body .label { color: var(--gris-texto); font-weight: 600; }\n  .order-items { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--gris-borde); }\n  .order-item-row { font-size: 13px; display: flex; justify-content: space-between; padding: 3px 0; }\n  .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--negro-suave); color: white; padding: 12px 24px; border-radius: 30px; font-size: 14px; font-weight: 600; z-index: 999; opacity: 0; pointer-events: none; transition: opacity .3s; white-space: nowrap; }\n  .toast.show { opacity: 1; }\n  .login-box { background: white; border-radius: 18px; padding: 40px; max-width: 360px; margin: 60px auto; border: 1.5px solid var(--gris-borde); text-align: center; }\n  .mp-config-box { background: var(--celeste-light); border: 1.5px solid var(--celeste); border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; font-size: 13px; color: var(--celeste-dark); }\n  .mp-config-box strong { display: block; margin-bottom: 6px; font-size: 14px; }\n  .btn-save { background: var(--celeste-dark); color: white; border: none; border-radius: 10px; padding: 11px 22px; font-size: 14px; font-weight: 700; cursor: pointer; }\n  .btn-save:hover { background: var(--celeste-mid); }\n  .empty-orders { text-align: center; padding: 60px 20px; color: var(--gris-texto); }\n  .empty-orders .ico { font-size: 48px; margin-bottom: 12px; }\n  @media (max-width: 700px) { .admin-grid { grid-template-columns: 1fr; } .hero h2 { font-size: 24px; } .cart-panel { width: 100%; } .form-row { grid-template-columns: 1fr; } }\n</style>\n</head>\n<body>\n\n<header>\n  <div class="header-inner">\n    <div class="logo-wrap">\n      <div class="logo-circle">\n        <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">\n          <circle cx="18" cy="18" r="17" fill="#4FC3F7"/>\n          <text x="18" y="14" text-anchor="middle" font-size="7" font-weight="800" font-family="Segoe UI,sans-serif" fill="white">ELEGIDOS</text>\n          <text x="18" y="23" text-anchor="middle" font-size="5" font-family="Segoe UI,sans-serif" fill="rgba(255,255,255,0.85)">Indumentaria</text>\n          <path d="M11 26V20l-3-3 3-4h3c0 2 8 2 8 0h3l3 4-3 3v6H11z" fill="none" stroke="white" stroke-width="1.3" stroke-linejoin="round"/>\n        </svg>\n      </div>\n      <div class="logo-text"><h1>ELEGIDOS</h1><p>Indumentaria</p></div>\n    </div>\n    <div class="header-actions">\n      <button class="btn-header" onclick="showPage(\'tienda\')">🏪 Tienda</button>\n      <button class="btn-header" onclick="showAdminLogin()">⚙️ Admin</button>\n      <button class="btn-cart" onclick="toggleCart()">🛒 Carrito <span class="cart-badge" id="cart-count">0</span></button>\n    </div>\n  </div>\n</header>\n\n<nav>\n  <button class="nav-btn active" onclick="showPage(\'tienda\')">🏠 Inicio</button>\n  <button class="nav-btn" onclick="showPage(\'productos\')">👕 Productos</button>\n  <button class="nav-btn" onclick="showPage(\'pedidos\')">📦 Mis Pedidos</button>\n</nav>\n\n<div class="cart-overlay" id="cart-overlay" onclick="toggleCart()"></div>\n<div class="cart-panel" id="cart-panel">\n  <div class="cart-header"><h3>🛒 Tu Carrito</h3><button class="cart-close" onclick="toggleCart()">✕</button></div>\n  <div class="cart-body" id="cart-body"><div class="cart-empty">Tu carrito está vacío 🛍️</div></div>\n  <div class="cart-footer">\n    <div class="cart-total"><span>Total</span><span id="cart-total-price">$0</span></div>\n    <button class="btn-comprar" onclick="abrirCheckout()">✅ Confirmar y Pagar</button>\n  </div>\n</div>\n\n<div class="page active" id="page-tienda">\n  <div class="hero">\n    <div><h2>Lo mejor en moda 💙</h2><p>Talles para todos, calidad garantizada. Pagá con Mercado Pago de forma segura.</p></div>\n    <div style="font-size:80px;opacity:.18;position:relative;z-index:1;">👗</div>\n  </div>\n  <div class="section-title">Destacados</div>\n  <div class="products-grid" id="grid-tienda"></div>\n</div>\n\n<div class="page" id="page-productos">\n  <div class="section-title">Todos los productos</div>\n  <div class="products-grid" id="grid-productos"></div>\n</div>\n\n<div class="page" id="page-pedidos">\n  <div class="section-title">Mis Pedidos</div>\n  <div id="pedidos-lista"></div>\n</div>\n\n<div class="page" id="page-admin">\n  <div class="section-title">Panel de Administración</div>\n  <!-- Admin se renderiza dinámicamente -->\n</div>\n\n<div class="modal-overlay" id="modal-checkout">\n  <div class="modal">\n    <h3>📦 Finalizar compra</h3>\n    <p class="modal-sub">Completá tus datos para recibir el pedido</p>\n    <div class="resumen-compra"><h4>🛒 Resumen</h4><div id="resumen-items"></div><div class="resumen-total"><span>Total</span><span id="resumen-total"></span></div></div>\n    <div class="form-row">\n      <div class="form-group"><label>Nombre *</label><input type="text" id="ch-nombre" placeholder="Tu nombre"/></div>\n      <div class="form-group"><label>Apellido *</label><input type="text" id="ch-apellido" placeholder="Tu apellido"/></div>\n    </div>\n    <div class="form-group"><label>Email *</label><input type="email" id="ch-email" placeholder="tu@email.com"/></div>\n    <div class="form-group"><label>Teléfono *</label><input type="tel" id="ch-telefono" placeholder="Ej: 3462 123456"/></div>\n    <div class="form-group"><label>Dirección *</label><input type="text" id="ch-direccion" placeholder="Ej: San Martín 450"/></div>\n    <div class="form-row">\n      <div class="form-group"><label>Localidad *</label><input type="text" id="ch-localidad" placeholder="Ej: Totoras"/></div>\n      <div class="form-group"><label>Provincia</label><input type="text" id="ch-provincia" placeholder="Santa Fe"/></div>\n    </div>\n    <div class="form-row">\n      <div class="form-group"><label>Código postal</label><input type="text" id="ch-cp" placeholder="2144"/></div>\n      <div class="form-group"><label>Notas</label><input type="text" id="ch-notas" placeholder="Instrucciones de entrega"/></div>\n    </div>\n    <button class="btn-mp" onclick="procesarPago()">💳 Pagar con Mercado Pago</button>\n    <button class="btn-cancelar" onclick="cerrarCheckout()">Cancelar</button>\n  </div>\n</div>\n\n<div class="toast" id="toast"></div>\n\n<script>\n// ── STATE ────────────────────────────────────────────────\nlet productos = [];\nlet carrito = JSON.parse(sessionStorage.getItem(\'carrito\') || \'[]\');\nlet adminLogueado = false;\nlet tallesSeleccionados = {};\n\nconst API = \'\';  // mismo origen que Flask\n\n// ── UTILS ────────────────────────────────────────────────\nfunction showToast(msg) {\n  const t = document.getElementById(\'toast\');\n  t.textContent = msg; t.classList.add(\'show\');\n  setTimeout(() => t.classList.remove(\'show\'), 2800);\n}\n\nfunction guardarCarrito() { sessionStorage.setItem(\'carrito\', JSON.stringify(carrito)); }\n\nfunction actualizarCartCount() {\n  document.getElementById(\'cart-count\').textContent = carrito.reduce((s,c) => s+c.cantidad, 0);\n}\n\nasync function api(path, method=\'GET\', body=null) {\n  const opts = { method, headers: {\'Content-Type\':\'application/json\'}, credentials: \'include\' };\n  if (body) opts.body = JSON.stringify(body);\n  const r = await fetch(API + path, opts);\n  return r.json();\n}\n\n// ── PAGES ────────────────────────────────────────────────\nfunction showPage(page) {\n  document.querySelectorAll(\'.page\').forEach(p => p.classList.remove(\'active\'));\n  document.getElementById(\'page-\' + page).classList.add(\'active\');\n  document.querySelectorAll(\'.nav-btn\').forEach(b => b.classList.remove(\'active\'));\n  const navMap = {tienda:0, productos:1, pedidos:2};\n  if (navMap[page] !== undefined) document.querySelectorAll(\'.nav-btn\')[navMap[page]].classList.add(\'active\');\n  if (page === \'tienda\' || page === \'productos\') cargarProductos();\n  if (page === \'pedidos\') renderPedidosCliente();\n  if (page === \'admin\') renderAdminPage();\n}\n\n// ── PRODUCTOS ────────────────────────────────────────────\nasync function cargarProductos() {\n  productos = await api(\'/api/productos\');\n  renderGrid(\'grid-tienda\');\n  renderGrid(\'grid-productos\');\n}\n\nfunction renderGrid(containerId) {\n  const c = document.getElementById(containerId);\n  if (!c) return;\n  if (!productos.length) { c.innerHTML = \'<p style="color:var(--gris-texto);padding:24px;">No hay productos publicados aún.</p>\'; return; }\n  c.innerHTML = productos.map(p => `\n    <div class="product-card">\n      <div class="product-img">${p.foto ? `<img src="${p.foto}" alt="${p.nombre}"/>` : (p.emoji||\'👕\')}</div>\n      <div class="product-info">\n        <div class="product-name">${p.nombre}</div>\n        <div class="product-desc">${p.descripcion||\'\'}</div>\n        <div class="product-price">$${Number(p.precio).toLocaleString(\'es-AR\')}</div>\n        <div class="talles-row" id="talles-${p.id}">\n          ${p.talles.map(t=>`<button class="talle-btn" onclick="selTalle(${p.id},\'${t}\',this)">${t}</button>`).join(\'\')}\n        </div>\n        <button class="btn-agregar" onclick="agregarAlCarrito(${p.id})">🛒 Agregar al carrito</button>\n      </div>\n    </div>`).join(\'\');\n}\n\nfunction selTalle(prodId, talle, btn) {\n  document.querySelectorAll(`#talles-${prodId} .talle-btn`).forEach(b=>b.classList.remove(\'selected\'));\n  btn.classList.add(\'selected\');\n  tallesSeleccionados[prodId] = talle;\n}\n\nfunction agregarAlCarrito(prodId) {\n  const talle = tallesSeleccionados[prodId];\n  if (!talle) { showToast(\'⚠️ Seleccioná un talle primero\'); return; }\n  const prod = productos.find(p=>p.id===prodId);\n  const key = `${prodId}-${talle}`;\n  const existe = carrito.find(c=>c.key===key);\n  if (existe) { existe.cantidad++; }\n  else { carrito.push({key, prodId, nombre:prod.nombre, precio:prod.precio, talle, cantidad:1, foto:prod.foto, emoji:prod.emoji||\'👕\', linkPago:prod.link_pago}); }\n  guardarCarrito(); actualizarCartCount();\n  showToast(`✅ ${prod.nombre} (Talle ${talle}) agregado`);\n  delete tallesSeleccionados[prodId];\n  document.querySelectorAll(`#talles-${prodId} .talle-btn`).forEach(b=>b.classList.remove(\'selected\'));\n}\n\n// ── CARRITO ──────────────────────────────────────────────\nfunction toggleCart() {\n  document.getElementById(\'cart-panel\').classList.toggle(\'open\');\n  document.getElementById(\'cart-overlay\').classList.toggle(\'open\');\n  renderCart();\n}\n\nfunction renderCart() {\n  const body = document.getElementById(\'cart-body\');\n  if (!carrito.length) { body.innerHTML=\'<div class="cart-empty">Tu carrito está vacío 🛍️</div>\'; document.getElementById(\'cart-total-price\').textContent=\'$0\'; return; }\n  body.innerHTML = carrito.map((c,i)=>`\n    <div class="cart-item">\n      <div class="cart-item-img">${c.foto?`<img src="${c.foto}"/>`:(c.emoji||\'👕\')}</div>\n      <div class="cart-item-info">\n        <div class="cart-item-name">${c.nombre}</div>\n        <div class="cart-item-talle">Talle: ${c.talle}</div>\n        <div class="cart-item-price">$${Number(c.precio).toLocaleString(\'es-AR\')}</div>\n        <div class="cart-item-qty">\n          <button class="qty-btn" onclick="cambiarCantidad(${i},-1)">−</button>\n          <span>${c.cantidad}</span>\n          <button class="qty-btn" onclick="cambiarCantidad(${i},1)">+</button>\n          <button class="cart-item-del" onclick="eliminarDelCarrito(${i})">🗑️</button>\n        </div>\n      </div>\n    </div>`).join(\'\');\n  const total = carrito.reduce((s,c)=>s+c.precio*c.cantidad,0);\n  document.getElementById(\'cart-total-price\').textContent=`$${total.toLocaleString(\'es-AR\')}`;\n}\n\nfunction cambiarCantidad(idx, delta) {\n  carrito[idx].cantidad += delta;\n  if (carrito[idx].cantidad <= 0) carrito.splice(idx,1);\n  guardarCarrito(); actualizarCartCount(); renderCart();\n}\n\nfunction eliminarDelCarrito(idx) { carrito.splice(idx,1); guardarCarrito(); actualizarCartCount(); renderCart(); }\n\n// ── CHECKOUT ─────────────────────────────────────────────\nfunction abrirCheckout() {\n  if (!carrito.length) { showToast(\'❌ Tu carrito está vacío\'); return; }\n  toggleCart();\n  document.getElementById(\'resumen-items\').innerHTML = carrito.map(c=>`\n    <div class="resumen-item"><span>${c.nombre} (T.${c.talle}) x${c.cantidad}</span><span>$${(c.precio*c.cantidad).toLocaleString(\'es-AR\')}</span></div>`).join(\'\');\n  const total = carrito.reduce((s,c)=>s+c.precio*c.cantidad,0);\n  document.getElementById(\'resumen-total\').textContent=`$${total.toLocaleString(\'es-AR\')}`;\n  document.getElementById(\'modal-checkout\').classList.add(\'open\');\n}\n\nfunction cerrarCheckout() { document.getElementById(\'modal-checkout\').classList.remove(\'open\'); }\n\nasync function procesarPago() {\n  const nombre   = document.getElementById(\'ch-nombre\').value.trim();\n  const apellido = document.getElementById(\'ch-apellido\').value.trim();\n  const email    = document.getElementById(\'ch-email\').value.trim();\n  const telefono = document.getElementById(\'ch-telefono\').value.trim();\n  const direccion= document.getElementById(\'ch-direccion\').value.trim();\n  const localidad= document.getElementById(\'ch-localidad\').value.trim();\n  const provincia= document.getElementById(\'ch-provincia\').value.trim();\n  const cp       = document.getElementById(\'ch-cp\').value.trim();\n  const notas    = document.getElementById(\'ch-notas\').value.trim();\n\n  if (!nombre||!apellido||!email||!telefono||!direccion||!localidad) { showToast(\'⚠️ Completá los campos obligatorios (*)\'); return; }\n  if (!/\\S+@\\S+\\.\\S+/.test(email)) { showToast(\'⚠️ Email inválido\'); return; }\n\n  const total = carrito.reduce((s,c)=>s+c.precio*c.cantidad,0);\n  const pedidoId = \'PED-\'+Date.now();\n\n  // Guardar pedido temporal en sessionStorage (no en DB todavía)\n  const pedidoTemp = { id:pedidoId, fecha:new Date().toLocaleString(\'es-AR\'), _ts:Date.now(),\n    nombre, apellido, email, telefono, direccion, localidad, provincia, cp, notas,\n    items:[...carrito], total };\n  sessionStorage.setItem(\'pedido_pendiente\', JSON.stringify(pedidoTemp));\n\n  // Buscar link de pago del producto\n  const linkPago = carrito[0]?.linkPago;\n  const todosIgual = carrito.every(c=>c.prodId===carrito[0].prodId);\n  const linkFinal = (carrito.length===1||todosIgual) && linkPago ? linkPago : null;\n\n  if (linkFinal) {\n    cerrarCheckout();\n    showToast(\'✅ Redirigiendo a Mercado Pago...\');\n    setTimeout(() => { window.location.href = linkFinal; }, 700);\n    return;\n  }\n\n  // Varios links distintos\n  const links = [...new Set(carrito.map(c=>c.linkPago).filter(Boolean))];\n  if (links.length) {\n    cerrarCheckout(); showToast(\'✅ Redirigiendo a Mercado Pago...\');\n    setTimeout(()=>{ window.location.href=links[0]; },700);\n    links.slice(1).forEach((l,i)=>setTimeout(()=>window.open(l,\'_blank\'),1400+i*600));\n    return;\n  }\n\n  cerrarCheckout();\n  showToast(\'⚠️ Este producto no tiene link de pago configurado. Contactá al vendedor.\');\n}\n\n// ── RETORNO DE MP ────────────────────────────────────────\nasync function verificarRetornoMP() {\n  const params = new URLSearchParams(window.location.search);\n  const status = params.get(\'status\') || params.get(\'collection_status\');\n  const paymentId = params.get(\'payment_id\') || params.get(\'collection_id\');\n  if (params.toString()) window.history.replaceState({}, \'\', window.location.pathname);\n\n  const pendienteRaw = sessionStorage.getItem(\'pedido_pendiente\');\n  if (!pendienteRaw) return;\n  const p = JSON.parse(pendienteRaw);\n\n  if (status === \'approved\') {\n    let estado = \'✅ Pagado\', montoPagado = null, estadoMonto = \'sin_verificar\';\n    // Verificar monto vía backend\n    if (paymentId) {\n      const res = await api(\'/api/verificar-pago\', \'POST\', {paymentId, totalEsperado: p.total});\n      if (res.ok) { estado=res.estadoLabel; montoPagado=res.montoPagado; estadoMonto=res.estadoMonto; }\n    }\n    // Guardar pedido en DB\n    await api(\'/api/pedidos\', \'POST\', {...p, estado});\n    await api(`/api/pedidos/${p.id}/confirmar`, \'POST\', {estado, montoPagado, estadoMonto, paymentId});\n    sessionStorage.removeItem(\'pedido_pendiente\');\n    carrito = []; guardarCarrito(); actualizarCartCount();\n    if (estadoMonto===\'parcial\') showToast(\'⚠️ Pago incompleto. Revisá con el vendedor.\');\n    else showToast(\'✅ ¡Pago confirmado! Pedido registrado.\');\n    setTimeout(()=>showPage(\'pedidos\'), 1000);\n\n  } else if (status===\'pending\') {\n    await api(\'/api/pedidos\', \'POST\', {...p, estado:\'⏳ Pago pendiente de acreditación\'});\n    sessionStorage.removeItem(\'pedido_pendiente\');\n    carrito=[]; guardarCarrito(); actualizarCartCount();\n    showToast(\'⏳ Pago pendiente. Te avisaremos cuando se acredite.\');\n\n  } else if (status===\'failure\'||status===\'rejected\') {\n    sessionStorage.removeItem(\'pedido_pendiente\');\n    showToast(\'❌ Pago rechazado. El pedido no fue registrado.\');\n\n  } else {\n    // Limpiar pendientes viejos (>2h)\n    if (p._ts && Date.now()-p._ts > 7200000) sessionStorage.removeItem(\'pedido_pendiente\');\n  }\n}\n\n// ── PEDIDOS CLIENTE ──────────────────────────────────────\nfunction renderPedidosCliente() {\n  const email = sessionStorage.getItem(\'ultimo_email\') || \'\';\n  document.getElementById(\'pedidos-lista\').innerHTML = `\n    <div style="background:white;border-radius:14px;border:1.5px solid var(--gris-borde);padding:24px;max-width:500px;margin:0 auto;">\n      <p style="font-size:14px;color:var(--gris-texto);margin-bottom:12px;">Ingresá tu email para ver tus pedidos:</p>\n      <div style="display:flex;gap:8px;">\n        <input type="email" id="email-buscar" value="${email}" placeholder="tu@email.com"\n          style="flex:1;padding:10px 14px;border:1.5px solid var(--gris-borde);border-radius:10px;font-size:14px;font-family:var(--font);"\n          onkeydown="if(event.key===\'Enter\')buscarPedidos()"/>\n        <button class="btn-save" onclick="buscarPedidos()">Buscar</button>\n      </div>\n    </div>\n    <div id="resultado-pedidos" style="margin-top:20px;"></div>`;\n}\n\nasync function buscarPedidos() {\n  const email = document.getElementById(\'email-buscar\').value.trim();\n  if (!email) return;\n  sessionStorage.setItem(\'ultimo_email\', email);\n  const todos = await api(\'/api/pedidos\').catch(()=>[]);\n  // Filtrar por email del cliente (solo si admin; si no, pedir desde endpoint público)\n  // Por ahora mostramos los del sessionStorage\n  const container = document.getElementById(\'resultado-pedidos\');\n  const mios = (Array.isArray(todos)?todos:[]).filter(p=>p.email===email);\n  if (!mios.length) { container.innerHTML=\'<div class="empty-orders"><div class="ico">📭</div><p>No encontramos pedidos con ese email.</p></div>\'; return; }\n  container.innerHTML = `<div class="orders-list">${mios.map(p=>renderOrderCard(p, false)).join(\'\')}</div>`;\n}\n\n// ── ADMIN ────────────────────────────────────────────────\nasync function showAdminLogin() {\n  const check = await api(\'/api/admin/check\');\n  if (check.ok) { adminLogueado=true; showPage(\'admin\'); return; }\n  document.querySelectorAll(\'.page\').forEach(p=>p.classList.remove(\'active\'));\n  document.getElementById(\'page-admin\').innerHTML = `\n    <div class="login-box">\n      <div style="font-size:48px;margin-bottom:12px;">🔐</div>\n      <h2 style="font-size:20px;font-weight:800;margin-bottom:6px;">Panel de Admin</h2>\n      <p style="color:var(--gris-texto);font-size:13px;margin-bottom:24px;">Ingresá tu contraseña</p>\n      <div class="form-group" style="text-align:left;">\n        <label>Contraseña</label>\n        <input type="password" id="admin-pass" placeholder="••••••••" onkeydown="if(event.key===\'Enter\')loginAdmin()"/>\n      </div>\n      <button class="btn-save" style="width:100%;padding:13px;" onclick="loginAdmin()">Ingresar</button>\n    </div>`;\n  document.getElementById(\'page-admin\').classList.add(\'active\');\n}\n\nasync function loginAdmin() {\n  const pass = document.getElementById(\'admin-pass\')?.value;\n  const res = await api(\'/api/admin/login\',\'POST\',{password:pass});\n  if (res.ok) { adminLogueado=true; showPage(\'admin\'); }\n  else showToast(\'❌ \'+(res.msg||\'Contraseña incorrecta\'));\n}\n\nasync function renderAdminPage() {\n  if (!adminLogueado) { showAdminLogin(); return; }\n  const tokenRes = await api(\'/api/config/mp-token\');\n  const tokenVal = tokenRes.valor||\'\';\n  document.getElementById(\'page-admin\').innerHTML = `\n  <div class="section-title">Panel de Administración</div>\n\n  <div class="mp-config-box" style="background:#fff3e0;border-color:#ff9800;">\n    <strong>🔑 Cambiar contraseña de Admin</strong>\n    <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">\n      <input type="password" id="new-pass1" placeholder="Nueva contraseña" style="flex:1;min-width:140px;padding:8px 12px;border:1.5px solid #ff9800;border-radius:8px;font-size:13px;"/>\n      <input type="password" id="new-pass2" placeholder="Repetir contraseña" style="flex:1;min-width:140px;padding:8px 12px;border:1.5px solid #ff9800;border-radius:8px;font-size:13px;"/>\n      <button class="btn-save" style="background:#e65100;" onclick="cambiarPassword()">Cambiar</button>\n    </div>\n    <div id="pass-status" style="margin-top:6px;font-size:12px;"></div>\n  </div>\n\n  <div class="mp-config-box">\n    <strong>⚙️ Mercado Pago — Access Token</strong>\n    <div style="display:flex;gap:8px;margin-top:8px;">\n      <input type="text" id="mp-token" value="${tokenVal}" placeholder="APP_USR-..." style="flex:1;padding:8px 12px;border:1.5px solid var(--celeste);border-radius:8px;font-size:13px;"/>\n      <button class="btn-save" onclick="guardarToken()">Guardar</button>\n    </div>\n    <div id="token-status" style="margin-top:6px;font-size:12px;"></div>\n  </div>\n\n  <div class="admin-grid">\n    <div class="admin-card">\n      <h3>➕ Agregar producto</h3>\n      <div class="form-group"><label>Nombre *</label><input type="text" id="ad-nombre" placeholder="Ej: Remera Básica"/></div>\n      <div class="form-group"><label>Descripción</label><textarea id="ad-desc" rows="2" placeholder="Material, estilo..."></textarea></div>\n      <div class="form-group"><label>Precio (ARS) *</label><input type="number" id="ad-precio" placeholder="15000"/></div>\n      <div class="form-group"><label>Talles (separados por coma) *</label><input type="text" id="ad-talles" placeholder="XS,S,M,L,XL"/></div>\n      <div class="form-group">\n        <label>🔗 Link de pago Mercado Pago</label>\n        <input type="url" id="ad-link" placeholder="https://mpago.la/..."/>\n        <div style="font-size:11px;color:var(--gris-texto);margin-top:4px;">Pegá el link de cobro de MP. El cliente será redirigido ahí.</div>\n      </div>\n      <div class="form-group"><label>Foto</label><input type="file" id="ad-foto" accept="image/*" onchange="previewFoto(this)"/></div>\n      <div id="preview-foto" style="margin-bottom:12px;"></div>\n      <button class="btn-save" style="width:100%;padding:13px;" onclick="agregarProducto()">✅ Publicar Producto</button>\n    </div>\n\n    <div>\n      <div class="admin-card" style="margin-bottom:20px;">\n        <h3>\n          🗂️ Gestionar publicaciones\n          <button onclick="confirmarBorrarTodos()" style="background:var(--rojo);color:white;border:none;border-radius:8px;padding:5px 12px;font-size:12px;font-weight:700;cursor:pointer;">🗑️ Borrar todas</button>\n        </h3>\n        <div id="admin-product-list" style="max-height:360px;overflow-y:auto;"></div>\n      </div>\n      <div class="admin-card">\n        <h3>🧾 Registro de compras</h3>\n        <div id="admin-orders-list"></div>\n      </div>\n    </div>\n  </div>`;\n\n  await renderAdminProductos();\n  await renderAdminPedidos();\n}\n\nasync function renderAdminProductos() {\n  productos = await api(\'/api/productos\');\n  const el = document.getElementById(\'admin-product-list\');\n  if (!el) return;\n  if (!productos.length) { el.innerHTML=\'<div style="color:var(--gris-texto);font-size:13px;text-align:center;padding:24px 0;">📭 No hay productos publicados.</div>\'; return; }\n  el.innerHTML = productos.map(p=>`\n    <div class="admin-product-item" id="aprod-${p.id}">\n      <div style="width:56px;height:56px;border-radius:10px;overflow:hidden;flex-shrink:0;background:var(--celeste-light);display:flex;align-items:center;justify-content:center;font-size:26px;">\n        ${p.foto?`<img src="${p.foto}" style="width:100%;height:100%;object-fit:cover;"/>`:(p.emoji||\'👕\')}\n      </div>\n      <div style="flex:1;min-width:0;">\n        <div style="font-size:14px;font-weight:700;margin-bottom:2px;">${p.nombre}</div>\n        <div style="font-size:12px;color:var(--gris-texto);margin-bottom:2px;">${p.descripcion||\'\'}</div>\n        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">\n          <span style="font-size:13px;font-weight:800;color:var(--celeste-dark);">$${Number(p.precio).toLocaleString(\'es-AR\')}</span>\n          <span style="font-size:11px;background:var(--celeste-light);color:var(--celeste-dark);padding:2px 8px;border-radius:10px;">${p.talles.join(\' · \')}</span>\n          ${p.link_pago?`<span style="font-size:11px;background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;">🔗 Link ✓</span>`:`<span style="font-size:11px;background:#fff3e0;color:#e65100;padding:2px 8px;border-radius:10px;">⚠️ Sin link</span>`}\n        </div>\n      </div>\n      <button onclick="eliminarProducto(${p.id})" style="background:var(--rojo);color:white;border:none;border-radius:8px;padding:7px 10px;cursor:pointer;font-size:15px;flex-shrink:0;">🗑️</button>\n    </div>`).join(\'\');\n}\n\nasync function renderAdminPedidos() {\n  const el = document.getElementById(\'admin-orders-list\');\n  if (!el) return;\n  const pedidos = await api(\'/api/pedidos\');\n  if (!Array.isArray(pedidos)||!pedidos.length) { el.innerHTML=\'<p style="color:var(--gris-texto);font-size:13px;text-align:center;padding:20px 0;">No hay compras registradas todavía.</p>\'; return; }\n  el.innerHTML=`<div class="orders-list" style="max-height:500px;overflow-y:auto;">${pedidos.map(p=>renderOrderCard(p,true)).join(\'\')}</div>`;\n}\n\nfunction renderOrderCard(p, isAdmin) {\n  const entregado = p.entregado===true||p.entregado===\'true\';\n  const items = Array.isArray(p.items)?p.items:[];\n  const total = Number(p.total||0);\n  const montoPagado = p.monto_pagado!=null?Number(p.monto_pagado):null;\n  const estadoMonto = p.estado_monto||\'\';\n  const colores = {exacto:\'#e8f5e9,#2e7d32,#a5d6a7\', parcial:\'#ffebee,#c62828,#ef9a9a\', exceso:\'#fffde7,#f57f17,#ffe082\'};\n  const [bg,fg,border] = (colores[estadoMonto]||\'#e8f5e9,#2e7d32,#a5d6a7\').split(\',\');\n  return `\n  <div class="order-card" id="order-card-${p.id}" style="${entregado?\'opacity:0.7;\':\'\'}">\n    <div class="order-header" style="${entregado?\'background:#e8f5e9;\':\'\'}">\n      <div>\n        <strong style="color:${entregado?\'#2e7d32\':\'var(--celeste-dark)\'};">#${p.id}</strong>\n        <span class="order-status" style="${entregado?\'background:#c8e6c9;color:#1b5e20;\':\'\'}">${entregado?\'✅ Entregado\':(p.estado||\'Pendiente\')}</span>\n      </div>\n      ${isAdmin?`<div style="display:flex;gap:8px;">\n        <button onclick="toggleEntregado(\'${p.id}\',${!entregado})" title="${entregado?\'Desmarcar\':\'Marcar entregado\'}"\n          style="background:${entregado?\'#a5d6a7\':\'#43a047\'};color:white;border:none;border-radius:8px;padding:7px 11px;cursor:pointer;font-size:16px;">\n          ${entregado?\'↩️\':\'✔️\'}\n        </button>\n        <button onclick="borrarPedido(\'${p.id}\')" style="background:var(--rojo);color:white;border:none;border-radius:8px;padding:7px 10px;cursor:pointer;font-size:15px;">🗑️</button>\n      </div>`:\'\'}\n    </div>\n    <div class="order-body">\n      <p><span class="label">Fecha: </span>${p.fecha}</p>\n      <p><span class="label">Cliente: </span>${p.nombre||\'\'} ${p.apellido||\'\'}</p>\n      <p><span class="label">Email: </span>${p.email||\'\'}</p>\n      <p><span class="label">Tel: </span>${p.telefono||\'\'}</p>\n      <p><span class="label">Dirección: </span>${p.direccion||\'\'}, ${p.localidad||\'\'}${p.provincia?\', \'+p.provincia:\'\'} ${p.cp?\'(CP: \'+p.cp+\')\':\'\'}</p>\n      ${p.notas?`<p><span class="label">Notas: </span>${p.notas}</p>`:\'\'}\n      ${montoPagado!=null?`\n      <div style="margin-top:10px;padding:10px 12px;border-radius:10px;border:1.5px solid ${border};background:${bg};">\n        <div style="font-size:12px;font-weight:700;color:${fg};margin-bottom:6px;">💰 Verificación de pago</div>\n        <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px;">\n          <span><span style="color:var(--gris-texto);font-weight:600;">Debía:</span> <strong>$${total.toLocaleString(\'es-AR\')}</strong></span>\n          <span><span style="color:var(--gris-texto);font-weight:600;">Pagó:</span> <strong style="color:${fg};">$${montoPagado.toLocaleString(\'es-AR\')}</strong></span>\n          ${estadoMonto===\'parcial\'?`<span style="color:${fg};font-weight:700;">⚠️ Falta $${(total-montoPagado).toLocaleString(\'es-AR\')}</span>`:\'\'}\n          ${estadoMonto===\'exceso\'?`<span style="color:${fg};font-weight:700;">⬆️ Exceso $${(montoPagado-total).toLocaleString(\'es-AR\')}</span>`:\'\'}\n          ${estadoMonto===\'exacto\'?`<span style="color:${fg};font-weight:700;">✔ Monto exacto</span>`:\'\'}\n        </div>\n        ${p.payment_id?`<div style="font-size:11px;color:var(--gris-texto);margin-top:4px;">ID MP: ${p.payment_id}</div>`:\'\'}\n      </div>`:\'\'}\n      <div class="order-items">\n        ${items.map(i=>`<div class="order-item-row"><span>${i.nombre} T.${i.talle} x${i.cantidad}</span><span>$${(i.precio*i.cantidad).toLocaleString(\'es-AR\')}</span></div>`).join(\'\')}\n        <div class="order-item-row" style="font-weight:800;border-top:1px solid var(--gris-borde);padding-top:6px;margin-top:4px;"><span>Total</span><span>$${total.toLocaleString(\'es-AR\')}</span></div>\n      </div>\n    </div>\n  </div>`;\n}\n\n// ── ADMIN ACCIONES ───────────────────────────────────────\nasync function cambiarPassword() {\n  const p1=document.getElementById(\'new-pass1\').value;\n  const p2=document.getElementById(\'new-pass2\').value;\n  const status=document.getElementById(\'pass-status\');\n  if (p1.length<8){status.textContent=\'❌ Mínimo 8 caracteres\';status.style.color=\'var(--rojo)\';return;}\n  if (p1!==p2){status.textContent=\'❌ No coinciden\';status.style.color=\'var(--rojo)\';return;}\n  const res=await api(\'/api/admin/cambiar-pass\',\'POST\',{password:p1});\n  if(res.ok){status.textContent=\'✅ Contraseña actualizada\';status.style.color=\'green\';document.getElementById(\'new-pass1\').value=\'\';document.getElementById(\'new-pass2\').value=\'\';}\n  else{status.textContent=\'❌ \'+(res.msg||\'Error\');status.style.color=\'var(--rojo)\';}\n}\n\nasync function guardarToken() {\n  const t=document.getElementById(\'mp-token\').value.trim();\n  const res=await api(\'/api/config/mp-token\',\'POST\',{token:t});\n  document.getElementById(\'token-status\').textContent=res.ok?\'✅ Token guardado\':\'❌ Error\';\n  if(res.ok) showToast(\'✅ Token de MP guardado\');\n}\n\nlet fotoBase64=null;\nfunction previewFoto(input){\n  const file=input.files[0]; if(!file)return;\n  const reader=new FileReader();\n  reader.onload=e=>{fotoBase64=e.target.result;document.getElementById(\'preview-foto\').innerHTML=`<img src="${fotoBase64}" style="width:100%;max-height:160px;object-fit:cover;border-radius:10px;border:1.5px solid var(--gris-borde)"/>`;};\n  reader.readAsDataURL(file);\n}\n\nasync function agregarProducto(){\n  const nombre=document.getElementById(\'ad-nombre\').value.trim();\n  const desc=document.getElementById(\'ad-desc\').value.trim();\n  const precio=parseFloat(document.getElementById(\'ad-precio\').value);\n  const tallesStr=document.getElementById(\'ad-talles\').value.trim();\n  const linkPago=document.getElementById(\'ad-link\').value.trim();\n  if(!nombre||!precio||!tallesStr){showToast(\'⚠️ Completá nombre, precio y talles\');return;}\n  const talles=tallesStr.split(\',\').map(t=>t.trim()).filter(Boolean);\n  const res=await api(\'/api/productos\',\'POST\',{nombre,desc,precio,talles,linkPago,foto:fotoBase64||\'\',emoji:\'👕\'});\n  if(res.ok){\n    fotoBase64=null;\n    [\'ad-nombre\',\'ad-desc\',\'ad-precio\',\'ad-talles\',\'ad-link\'].forEach(id=>document.getElementById(id).value=\'\');\n    document.getElementById(\'ad-foto\').value=\'\'; document.getElementById(\'preview-foto\').innerHTML=\'\';\n    showToast(`✅ "${nombre}" publicado`);\n    await renderAdminProductos(); renderGrid(\'grid-tienda\'); renderGrid(\'grid-productos\');\n  } else showToast(\'❌ Error al publicar\');\n}\n\nfunction animarYEliminar(el, callback) {\n  el.style.transition=\'transform 0.38s cubic-bezier(.6,0,1,.6),opacity 0.3s,max-height 0.32s ease 0.22s,margin-bottom 0.32s ease 0.22s\';\n  el.style.overflow=\'hidden\'; el.style.maxHeight=el.offsetHeight+\'px\';\n  el.style.transform=\'translateX(120%)\'; el.style.opacity=\'0\';\n  setTimeout(()=>{el.style.maxHeight=\'0\';el.style.marginBottom=\'0\';},300);\n  setTimeout(callback,660);\n}\n\nasync function eliminarProducto(pid){\n  const prod=productos.find(p=>p.id===pid);\n  if(!confirm(`¿Eliminar "${prod?.nombre||\'este producto\'}"?`))return;\n  const el=document.getElementById(`aprod-${pid}`);\n  const doDelete=async()=>{\n    await api(`/api/productos/${pid}`,\'DELETE\');\n    showToast(\'🗑️ Producto eliminado\');\n    await renderAdminProductos(); renderGrid(\'grid-tienda\'); renderGrid(\'grid-productos\');\n  };\n  if(el) animarYEliminar(el, doDelete); else await doDelete();\n}\n\nasync function confirmarBorrarTodos(){\n  if(!productos.length){showToast(\'No hay productos\');return;}\n  if(!confirm(`¿Borrar los ${productos.length} productos?`))return;\n  const items=Array.from(document.querySelectorAll(\'.admin-product-item\'));\n  items.forEach((el,i)=>setTimeout(()=>{\n    el.style.transition=\'transform 0.38s cubic-bezier(.6,0,1,.6),opacity 0.3s,max-height 0.32s ease 0.22s,margin-bottom 0.32s ease 0.22s\';\n    el.style.overflow=\'hidden\'; el.style.maxHeight=el.offsetHeight+\'px\';\n    el.style.transform=\'translateX(120%)\'; el.style.opacity=\'0\';\n    setTimeout(()=>{el.style.maxHeight=\'0\';el.style.marginBottom=\'0\';},300);\n  },i*55));\n  setTimeout(async()=>{\n    await api(\'/api/productos/todos\',\'DELETE\');\n    showToast(\'🗑️ Todos los productos eliminados\');\n    await renderAdminProductos(); renderGrid(\'grid-tienda\'); renderGrid(\'grid-productos\');\n  },items.length*55+680);\n}\n\nasync function toggleEntregado(pid, nuevoEstado){\n  await api(`/api/pedidos/${pid}/entregado`,\'POST\',{entregado:nuevoEstado});\n  showToast(nuevoEstado?\'✅ Marcado como entregado\':\'↩️ Desmarcado\');\n  await renderAdminPedidos();\n}\n\nasync function borrarPedido(pid){\n  if(!confirm(\'¿Borrar este registro? No se puede deshacer.\'))return;\n  const el=document.getElementById(`order-card-${pid}`);\n  const doDelete=async()=>{\n    await api(`/api/pedidos/${pid}`,\'DELETE\');\n    showToast(\'🗑️ Registro eliminado\');\n    await renderAdminPedidos();\n  };\n  if(el) animarYEliminar(el,doDelete); else await doDelete();\n}\n\n// ── INIT ─────────────────────────────────────────────────\nactualizarCartCount();\ncargarProductos();\nverificarRetornoMP();\n</script>\n</body>\n</html>\n'

@app.route('/')
def index():
    from flask import Response
    return Response(_HTML, mimetype='text/html')

# ── ADMIN AUTH ───────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    cfg = Config.query.get('admin_pass')
    if cfg and cfg.valor == data.get('password', ''):
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Contraseña incorrecta'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'ok': True})

@app.route('/api/admin/check')
def admin_check():
    return jsonify({'ok': bool(session.get('admin'))})

@app.route('/api/admin/cambiar-pass', methods=['POST'])
def cambiar_pass():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    data = request.json or {}
    nueva = data.get('password', '')
    if len(nueva) < 8:
        return jsonify({'ok': False, 'msg': 'Mínimo 8 caracteres'})
    cfg = Config.query.get('admin_pass')
    cfg.valor = nueva
    db.session.commit()
    return jsonify({'ok': True})

# ── CONFIG MP ────────────────────────────────────────────
@app.route('/api/config/mp-token')
def get_mp_token():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    cfg = Config.query.get('mp_token')
    return jsonify({'ok': True, 'valor': cfg.valor if cfg else ''})

@app.route('/api/config/mp-token', methods=['POST'])
def set_mp_token():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    token = (request.json or {}).get('token', '')
    cfg = Config.query.get('mp_token')
    if cfg:
        cfg.valor = token
    else:
        db.session.add(Config(clave='mp_token', valor=token))
    db.session.commit()
    return jsonify({'ok': True})

# ── PRODUCTOS ────────────────────────────────────────────
@app.route('/api/productos')
def get_productos():
    prods = Producto.query.order_by(Producto.creado_at.desc()).all()
    return jsonify([p.to_dict() for p in prods])

@app.route('/api/productos', methods=['POST'])
def crear_producto():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    data = request.json or {}
    p = Producto(
        nombre      = data.get('nombre'),
        descripcion = data.get('desc', ''),
        precio      = float(data.get('precio', 0)),
        talles      = json.dumps(data.get('talles', [])),
        link_pago   = data.get('linkPago', ''),
        foto        = data.get('foto', ''),
        emoji       = data.get('emoji', '👕'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'id': p.id})

@app.route('/api/productos/<int:pid>', methods=['DELETE'])
def eliminar_producto(pid):
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    p = Producto.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/productos/todos', methods=['DELETE'])
def eliminar_todos():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    Producto.query.delete()
    db.session.commit()
    return jsonify({'ok': True})

# ── PEDIDOS ──────────────────────────────────────────────
@app.route('/api/pedidos')
def get_pedidos():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    pedidos = Pedido.query.order_by(Pedido.creado_at.desc()).all()
    return jsonify([p.to_dict() for p in pedidos])

@app.route('/api/pedidos', methods=['POST'])
def crear_pedido():
    data = request.json or {}
    if Pedido.query.get(data['id']):
        return jsonify({'ok': True})  # ya existe, ignorar
    p = Pedido(
        id        = data['id'],
        fecha     = data['fecha'],
        nombre    = data.get('nombre'),
        apellido  = data.get('apellido'),
        email     = data.get('email'),
        telefono  = data.get('telefono'),
        direccion = data.get('direccion'),
        localidad = data.get('localidad'),
        provincia = data.get('provincia', ''),
        cp        = data.get('cp', ''),
        notas     = data.get('notas', ''),
        items     = json.dumps(data.get('items', [])),
        total     = float(data.get('total', 0)),
        estado    = data.get('estado', 'Pendiente'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/pedidos/<pid>/confirmar', methods=['POST'])
def confirmar_pedido(pid):
    data = request.json or {}
    p = Pedido.query.get_or_404(pid)
    p.estado       = data.get('estado', p.estado)
    p.monto_pagado = data.get('montoPagado')
    p.estado_monto = data.get('estadoMonto', '')
    p.payment_id   = data.get('paymentId', '')
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/pedidos/<pid>/entregado', methods=['POST'])
def toggle_entregado(pid):
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    p = Pedido.query.get_or_404(pid)
    p.entregado = (request.json or {}).get('entregado', False)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/pedidos/<pid>', methods=['DELETE'])
def eliminar_pedido(pid):
    if not session.get('admin'):
        return jsonify({'ok': False}), 403
    p = Pedido.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})

# ── VERIFICAR PAGO MP ────────────────────────────────────
@app.route('/api/verificar-pago', methods=['POST'])
def verificar_pago():
    data = request.json or {}
    payment_id     = data.get('paymentId')
    total_esperado = float(data.get('totalEsperado', 0))
    cfg = Config.query.get('mp_token')
    token = cfg.valor if cfg else ''
    if not token:
        return jsonify({'ok': False, 'msg': 'Sin token MP'})
    try:
        resp = requests.get(
            f'https://api.mercadopago.com/v1/payments/{payment_id}',
            headers={'Authorization': f'Bearer {token}'}, timeout=10
        )
        if not resp.ok:
            return jsonify({'ok': False, 'msg': 'Error consultando MP'})
        pago          = resp.json()
        monto_pagado  = float(pago.get('transaction_amount', 0))
        diferencia    = monto_pagado - total_esperado
        if abs(diferencia) <= 1:
            estado_monto, label = 'exacto',  '✅ Pagado — monto correcto'
        elif diferencia > 1:
            estado_monto, label = 'exceso',  f'⚠️ Pagó de más (+${diferencia:,.0f})'
        else:
            estado_monto, label = 'parcial', f'❌ Pago incompleto (falta ${abs(diferencia):,.0f})'
        return jsonify({'ok': True, 'montoPagado': monto_pagado,
                        'estadoMonto': estado_monto, 'estadoLabel': label,
                        'paymentId': payment_id})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)})

# ── ARRANQUE ─────────────────────────────────────────────
with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
