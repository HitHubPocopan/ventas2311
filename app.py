from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date
import json
import os
import re
from urllib.parse import unquote
from functools import wraps

app = Flask(__name__)
app.secret_key = 'pocopan_secure_key_2024_vercel'

class SistemaPocopan:
    def __init__(self):
        self.config = {
            "iva": 21.0, 
            "moneda": "$", 
            "empresa": "POCOPAN",
            "usuarios": {
                "admin": {"password": "admin123", "rol": "admin", "terminal": "TODAS"},
                "pos1": {"password": "pos1123", "rol": "pos", "terminal": "POS1"},
                "pos2": {"password": "pos2123", "rol": "pos", "terminal": "POS2"},
                "pos3": {"password": "pos3123", "rol": "pos", "terminal": "POS3"}
            }
        }
        
        self.ventas_memory = {'POS1': [], 'POS2': [], 'POS3': [], 'TODAS': []}
        self.contadores_memory = {
            "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "TODAS": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
        }
        
        self.catalogo = [
            {'Nombre': 'Cajas Verdes GRANJA ANIMALES', 'Categoría': 'Ingenio', 'Precio Venta': 25000, 'Proveedor': 'A', 'Estado': 'Disponible'},
            {'Nombre': 'Pezca Gusanos', 'Categoría': 'Ingenio', 'Precio Venta': 30800, 'Proveedor': 'B', 'Estado': 'Disponible'},
            {'Nombre': 'Rompecabezas 150 PIEZAS', 'Categoría': 'Ingenio', 'Precio Venta': 15000, 'Proveedor': 'C', 'Estado': 'Disponible'},
            {'Nombre': 'ABACO', 'Categoría': 'Ingenio', 'Precio Venta': 25000, 'Proveedor': 'A', 'Estado': 'Disponible'},
            {'Nombre': 'LIBRO MADERA', 'Categoría': 'Libros', 'Precio Venta': 15200, 'Proveedor': 'B', 'Estado': 'Disponible'}
        ]
        self.catalogo_cargado = True
        self.productos_disponibles = [p['Nombre'] for p in self.catalogo]
        
        print("✅ Sistema POCOPAN listo para Vercel")

    def obtener_detalles_producto(self, producto_nombre):
        if not producto_nombre:
            return None
        nombre_limpio = re.sub(r'\s+', ' ', producto_nombre).strip()
        for producto in self.catalogo:
            if producto['Nombre'] == nombre_limpio:
                return producto
        for producto in self.catalogo:
            if nombre_limpio.lower() in producto['Nombre'].lower():
                return producto
        return None

    def buscar_productos(self, query, limit=10):
        if not query or len(query) < 2:
            return []
        query = query.lower().strip()
        return [p['Nombre'] for p in self.catalogo if query in p['Nombre'].lower()][:limit]

    def agregar_al_carrito(self, carrito_actual, producto_nombre, cantidad):
        try:
            detalles = self.obtener_detalles_producto(producto_nombre)
            if not detalles:
                return False, "Producto no encontrado", carrito_actual

            cantidad = int(cantidad)
            if cantidad <= 0 or cantidad > 100:
                return False, "Cantidad inválida", carrito_actual

            precio = float(detalles['Precio Venta'])
            item = {
                'producto': producto_nombre,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': cantidad * precio,
                'proveedor': detalles['Proveedor'],
                'categoria': detalles['Categoría']
            }
            carrito_actual.append(item)
            return True, f"{producto_nombre} agregado", carrito_actual
        except Exception as e:
            return False, f"Error: {str(e)}", carrito_actual

    def eliminar_del_carrito(self, carrito_actual, index):
        try:
            index = int(index)
            if 0 <= index < len(carrito_actual):
                producto_eliminado = carrito_actual[index]['producto']
                carrito_actual.pop(index)
                return True, f"{producto_eliminado} eliminado", carrito_actual
            return False, "Índice inválido", carrito_actual
        except:
            return False, "Índice inválido", carrito_actual

    def limpiar_carrito(self, carrito_actual):
        carrito_actual.clear()
        return True, "Carrito limpiado", carrito_actual

    def calcular_totales(self, carrito_actual):
        try:
            subtotal = sum(item.get('subtotal', 0) for item in carrito_actual)
            iva = subtotal * 0.21
            total = subtotal + iva
            return {'subtotal': subtotal, 'iva': iva, 'total': total, 'porcentaje_iva': 21}
        except:
            return {'subtotal': 0, 'iva': 0, 'total': 0, 'porcentaje_iva': 21}

    def finalizar_venta(self, carrito_actual, terminal_id):
        if not carrito_actual:
            return False, "Carrito vacío"
        
        try:
            id_cliente = self.contadores_memory[terminal_id]["ultimo_cliente"] + 1
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            ventas_terminal = self.ventas_memory.get(terminal_id, [])
            id_venta = max([v['ID_Venta'] for v in ventas_terminal], default=0) + 1
            
            nuevas_ventas = []
            for item in carrito_actual:
                nueva_venta = {
                    'ID_Venta': id_venta,
                    'Fecha': fecha, 'Hora': hora,
                    'ID_Cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                    'Producto': item['producto'], 'Cantidad': item['cantidad'],
                    'Precio_Unitario': item['precio'], 'Total_Venta': item['subtotal'],
                    'Vendedor': f'POS {terminal_id}', 'ID_Terminal': terminal_id
                }
                nuevas_ventas.append(nueva_venta)
            
            self.ventas_memory[terminal_id].extend(nuevas_ventas)
            self.ventas_memory['TODAS'].extend(nuevas_ventas)
            self.contadores_memory[terminal_id]["ultimo_cliente"] = id_cliente
            self.contadores_memory[terminal_id]["ultima_venta"] = id_venta
            self.contadores_memory[terminal_id]["total_ventas"] += 1
            
            return True, {
                'id_venta': id_venta,
                'id_cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                'total_productos': len(nuevas_ventas),
                'totales': self.calcular_totales(carrito_actual),
                'fecha': fecha, 'hora': hora
            }
        except Exception as e:
            return False, f"Error: {str(e)}"

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        try:
            if terminal_id == "TODAS" or not terminal_id:
                ventas = []
                for term in ['POS1', 'POS2', 'POS3']:
                    ventas.extend(self.ventas_memory.get(term, []))
                terminal_nombre = "General"
            else:
                ventas = self.ventas_memory.get(terminal_id, [])
                terminal_nombre = f"Terminal {terminal_id}"
            
            if not ventas:
                return self._estadisticas_vacias(terminal_nombre)
            
            ids_venta_unicos = set(v['ID_Venta'] for v in ventas)
            total_ventas = len(ids_venta_unicos)
            ingresos_totales = sum(v['Total_Venta'] for v in ventas)
            ventas_hoy = [v for v in ventas if v['Fecha'] == date.today().strftime("%Y-%m-%d")]
            ventas_hoy_count = len(set(v['ID_Venta'] for v in ventas_hoy))
            
            return {
                'ventas_totales': total_ventas,
                'ingresos_totales': f"${ingresos_totales:,.2f}",
                'productos_catalogo': len(self.catalogo),
                'usuarios_activos': 1,
                'ventas_hoy_count': ventas_hoy_count,
                'dashboard_nombre': f"Dashboard - {terminal_nombre}",
                'terminal_actual': terminal_id or "TODAS"
            }
        except:
            return self._estadisticas_vacias(terminal_id or "TODAS")

    def _estadisticas_vacias(self, terminal_nombre):
        return {
            'ventas_totales': 0, 'ingresos_totales': "$0.00",
            'productos_catalogo': len(self.catalogo), 'usuarios_activos': 1,
            'ventas_hoy_count': 0, 'dashboard_nombre': f"Dashboard - {terminal_nombre}",
            'terminal_actual': "TODAS"
        }

    def obtener_estadisticas_por_terminal(self):
        return {term: self.obtener_estadisticas_dashboard(term) for term in ['POS1', 'POS2', 'POS3']}

sistema = SistemaPocopan()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session.get('rol') != 'admin':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        if usuario in sistema.config['usuarios']:
            user_config = sistema.config['usuarios'][usuario]
            if user_config['password'] == password:
                session['usuario'] = usuario
                session['rol'] = user_config['rol']
                session['terminal'] = user_config['terminal']
                return redirect('/')
        return render_template('login.html', error='Credenciales incorrectas')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

@app.route('/')
@login_required
def index():
    usuario = session.get('usuario')
    rol = session.get('rol')
    terminal = session.get('terminal')
    carrito_actual = get_carrito()
    totales = sistema.calcular_totales(carrito_actual)
    contador_actual = sistema.contadores_memory[terminal]["ultimo_cliente"] + 1
    
    return render_template('pos.html', 
        sistema=sistema, carrito=carrito_actual, totales=totales,
        usuario_actual=usuario, rol_actual=rol, terminal_actual=terminal,
        id_cliente_actual=f"CLIENTE-{terminal}-{contador_actual:04d}")

@app.route('/dashboard')
@login_required
def dashboard():
    rol = session.get('rol')
    terminal = session.get('terminal')
    if rol == 'admin':
        stats = sistema.obtener_estadisticas_dashboard("TODAS")
        stats_por_terminal = sistema.obtener_estadisticas_por_terminal()
    else:
        stats = sistema.obtener_estadisticas_dashboard(terminal)
        stats_por_terminal = {}
    
    return render_template('dashboard.html', 
        stats=stats, stats_por_terminal=stats_por_terminal,
        empresa=sistema.config['empresa'], sistema=sistema,
        rol_actual=rol, terminal_actual=terminal)

@app.route('/dashboard/<terminal_id>')
@admin_required
def dashboard_terminal(terminal_id):
    if terminal_id not in ['POS1', 'POS2', 'POS3', 'TODAS']:
        return redirect('/dashboard')
    stats = sistema.obtener_estadisticas_dashboard(terminal_id)
    return render_template('dashboard.html', 
        stats=stats, stats_por_terminal={},
        empresa=sistema.config['empresa'], sistema=sistema,
        rol_actual='admin', terminal_actual=terminal_id)

@app.route('/diagnostico')
def diagnostico():
    return jsonify({
        'status': 'OK', 'mensaje': 'Sistema POCOPAN operativo',
        'terminal': 'Vercel', 'catalogo_cargado': sistema.catalogo_cargado,
        'productos_en_catalogo': len(sistema.productos_disponibles),
        'ventas_registradas': sum(len(v) for v in sistema.ventas_memory.values())
    })

@app.route('/buscar-productos')
def buscar_productos_route():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    productos = sistema.buscar_productos(query)
    return jsonify(productos)

@app.route('/detalles-producto/<path:producto_nombre>')
def detalles_producto(producto_nombre):
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        detalles = sistema.obtener_detalles_producto(producto_limpio)
        if detalles:
            return jsonify(detalles)
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': 'Error interno'}), 500

@app.route('/agregar-carrito', methods=['POST'])
@login_required
def agregar_carrito():
    try:
        data = request.get_json()
        producto = data.get('producto', '').strip()
        cantidad = data.get('cantidad', 1)
        if not producto:
            return jsonify({'success': False, 'message': 'Producto requerido'}), 400
            
        carrito_actual = get_carrito()
        success, message, carrito_actual = sistema.agregar_al_carrito(carrito_actual, producto, cantidad)
        session[f'carrito_{session.get("usuario")}'] = carrito_actual
        
        if success:
            return jsonify({
                'success': True, 'message': message,
                'carrito': carrito_actual, 'totales': sistema.calcular_totales(carrito_actual)
            })
        return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error interno'}), 500

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
@login_required
def eliminar_carrito(index):
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.eliminar_del_carrito(carrito_actual, index)
    session[f'carrito_{session.get("usuario")}'] = carrito_actual
    if success:
        return jsonify({
            'success': True, 'message': message,
            'carrito': carrito_actual, 'totales': sistema.calcular_totales(carrito_actual)
        })
    return jsonify({'success': False, 'message': message}), 400

@app.route('/limpiar-carrito', methods=['DELETE'])
@login_required
def limpiar_carrito():
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.limpiar_carrito(carrito_actual)
    session[f'carrito_{session.get("usuario")}'] = carrito_actual
    if success:
        return jsonify({
            'success': True, 'message': message,
            'carrito': carrito_actual, 'totales': sistema.calcular_totales(carrito_actual)
        })
    return jsonify({'success': False, 'message': message}), 400

@app.route('/finalizar-venta', methods=['POST'])
@login_required
def finalizar_venta():
    carrito_actual = get_carrito()
    terminal_id = session.get('terminal')
    success, result = sistema.finalizar_venta(carrito_actual, terminal_id)
    if success:
        usuario = session.get('usuario')
        session[f'carrito_{usuario}'] = []
        return jsonify({
            'success': True, 'message': 'Venta finalizada',
            'resumen': result,
            'id_cliente_actual': f"CLIENTE-{terminal_id}-{sistema.contadores_memory[terminal_id]['ultimo_cliente'] + 1:04d}"
        })
    return jsonify({'success': False, 'message': result}), 400

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "sistema": sistema is not None})

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
    
    