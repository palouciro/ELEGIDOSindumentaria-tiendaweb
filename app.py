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
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
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
@app.route('/')
def index():
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    return send_from_directory(template_dir, 'index.html')

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
