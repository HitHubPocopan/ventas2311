from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date
import json
import os
import re
from urllib.parse import unquote
from functools import wraps
import pandas as pd

app = Flask(__name__)
app.secret_key = 'pocopan_secure_key_2024_vercel_fixed'

# Configuración específica para Vercel
app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    SECRET_KEY='pocopan_secure_key_2024_vercel_fixed'
)

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
        
        # Inicializar estructuras en memoria
        self.ventas_memory = {'POS1': [], 'POS2': [], 'POS3': [], 'TODAS': []}
        self.contadores_memory = {
            "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "TODAS": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
        }
        
        # Cargar catálogo desde Excel
        self.catalogo = []
        self.catalogo_cargado = False
        self.productos_disponibles = []
        
        self.cargar_catalogo_desde_excel()
        
        print("✅ Sistema POCOPAN inicializado correctamente")

    def cargar_catalogo_desde_excel(self):
        """Carga el catálogo desde el archivo Excel"""
        try:
            # Leer el archivo Excel
            df = pd.read_excel('catalogo.xlsx')
            
            # Limpiar y procesar los datos
            self.catalogo = []
            
            for _, row in df.iterrows():
                # Verificar que tenga los datos mínimos necesarios
                if pd.notna(row['Nombre']) and pd.notna(row['Precio Venta']):
                    producto = {
                        'Nombre': str(row['Nombre']).strip(),
                        'Categoría': str(row['Categoria']).strip() if pd.notna(row['Categoria']) else 'Sin Categoría',
                        'Subcategoría': str(row['SubCAT']).strip() if pd.notna(row['SubCAT']) else '',
                        'Precio Venta': float(row['Precio Venta']),
                        'Proveedor': str(row.get('Proveedor', '')).strip() if pd.notna(row.get('Proveedor', '')) else 'Sin Proveedor',
                        'Estado': 'Disponible'
                    }
                    self.catalogo.append(producto)
            
            self.catalogo_cargado = True
            self.productos_disponibles = [p['Nombre'] for p in self.catalogo]
            
            print(f"✅ Catálogo cargado: {len(self.catalogo)} productos")
            
        except Exception as e:
            print(f"❌ Error cargando catálogo: {str(e)}")
            # Si hay error, crear un catálogo mínimo de emergencia
            self.crear_catalogo_emergencia()

    def crear_catalogo_emergencia(self):
        """Crea un catálogo mínimo en caso de error"""
        self.catalogo = [
            {
                'Nombre': 'Cajas Verdes GRANJA ANIMALES DINOS',
                'Categoría': 'Ingenio', 
                'Subcategoría': 'Madera Ingenio',
                'Precio Venta': 25000, 
                'Proveedor': 'Proveedor A', 
                'Estado': 'Disponible'
            },
            {
                'Nombre': 'Pezca Gusanos', 
                'Categoría': 'Ingenio', 
                'Subcategoría': 'Madera Ingenio',
                'Precio Venta': 30800, 
                'Proveedor': 'Proveedor B', 
                'Estado': 'Disponible'
            }
        ]
        self.catalogo_cargado = True
        self.productos_disponibles = [p['Nombre'] for p in self.catalogo]
        print("⚠️ Catálogo de emergencia cargado")

    def obtener_detalles_producto(self, producto_nombre):
        if not self.catalogo_cargado or not producto_nombre:
            return None
        
        try:
            nombre_limpio = re.sub(r'\s+', ' ', producto_nombre).strip()
            
            # Búsqueda exacta
            for producto in self.catalogo:
                if producto['Nombre'] == nombre_limpio:
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            # Búsqueda case-insensitive
            for producto in self.catalogo:
                if producto['Nombre'].lower() == nombre_limpio.lower():
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            # Búsqueda parcial
            for producto in self.catalogo:
                if nombre_limpio.lower() in producto['Nombre'].lower():
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo detalles: {str(e)}")
            return None

    def buscar_productos(self, query, limit=10):
        if not self.catalogo_cargado or not query:
            return []
        
        query = query.lower().strip()
        if len(query) < 2:
            return []
        
        try:
            productos_filtrados = [
                producto['Nombre'] for producto in self.catalogo 
                if query in producto['Nombre'].lower()
            ][:limit]
            return productos_filtrados
        except Exception:
            return []

    def agregar_al_carrito(self, carrito_actual, producto_nombre, cantidad):
        try:
            # Validar límite del carrito
            if len(carrito_actual) >= 50:
                return False, "Límite de items en carrito alcanzado", carrito_actual

            detalles = self.obtener_detalles_producto(producto_nombre)
            if not detalles:
                return False, "Producto no encontrado", carrito_actual

            try:
                cantidad = int(cantidad)
                if cantidad <= 0:
                    return False, "La cantidad debe ser mayor a 0", carrito_actual
                if cantidad > 100:
                    return False, "Cantidad excede el límite permitido", carrito_actual
            except ValueError:
                return False, "Cantidad inválida", carrito_actual

            precio = float(detalles['precio'])
            if precio <= 0:
                return False, "El producto no tiene precio válido", carrito_actual

            item = {
                'producto': detalles['nombre'],
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': cantidad * precio,
                'proveedor': detalles['proveedor'],
                'categoria': detalles['categoria'],
                'timestamp': datetime.now().isoformat()
            }
            
            carrito_actual.append(item)
            return True, f"{detalles['nombre']} agregado al carrito", carrito_actual
            
        except Exception as e:
            return False, f"Error: {str(e)}", carrito_actual
    
    def eliminar_del_carrito(self, carrito_actual, index):
        try:
            index = int(index)
            if 0 <= index < len(carrito_actual):
                producto_eliminado = carrito_actual[index]['producto']
                carrito_actual.pop(index)
                return True, f"{producto_eliminado} eliminado", carrito_actual
            else:
                return False, "Índice inválido", carrito_actual
        except (ValueError, IndexError):
            return False, "Índice inválido", carrito_actual
    
    def limpiar_carrito(self, carrito_actual):
        carrito_actual.clear()
        return True, "Carrito limpiado", carrito_actual
    
    def calcular_totales(self, carrito_actual):
        try:
            subtotal = sum(item.get('subtotal', 0) for item in carrito_actual)
            iva_porcentaje = 21
            iva = subtotal * (iva_porcentaje / 100)
            total = subtotal + iva
            
            return {
                'subtotal': round(subtotal, 2),
                'iva': round(iva, 2),
                'total': round(total, 2),
                'porcentaje_iva': iva_porcentaje
            }
        except Exception:
            return {'subtotal': 0, 'iva': 0, 'total': 0, 'porcentaje_iva': 21}

    def finalizar_venta(self, carrito_actual, terminal_id):
        if not carrito_actual:
            return False, "El carrito está vacío"
        
        try:
            # Usar contadores específicos del terminal
            id_cliente = self.contadores_memory[terminal_id]["ultimo_cliente"] + 1
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            # Obtener último ID_Venta del terminal específico
            ventas_terminal = self.ventas_memory.get(terminal_id, [])
            if not ventas_terminal:
                id_venta = 1
            else:
                id_venta = max([venta['ID_Venta'] for venta in ventas_terminal]) + 1
            
            nuevas_ventas = []
            for item in carrito_actual:
                nueva_venta = {
                    'ID_Venta': id_venta,
                    'Fecha': fecha,
                    'Hora': hora,
                    'ID_Cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                    'Producto': item['producto'],
                    'Cantidad': item['cantidad'],
                    'Precio_Unitario': item['precio'],
                    'Total_Venta': item['subtotal'],
                    'Vendedor': f'POS {terminal_id}',
                    'ID_Terminal': terminal_id
                }
                nuevas_ventas.append(nueva_venta)
            
            # Guardar en memoria
            self.ventas_memory[terminal_id].extend(nuevas_ventas)
            self.ventas_memory['TODAS'].extend(nuevas_ventas)
            
            # Actualizar contadores
            self.contadores_memory[terminal_id]["ultimo_cliente"] = id_cliente
            self.contadores_memory[terminal_id]["ultima_venta"] = id_venta
            self.contadores_memory[terminal_id]["total_ventas"] += 1
            
            totales = self.calcular_totales(carrito_actual)
            
            return True, {
                'id_venta': id_venta,
                'id_cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                'total_productos': len(nuevas_ventas),
                'totales': totales,
                'fecha': fecha,
                'hora': hora
            }
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        try:
            if terminal_id == "TODAS" or terminal_id is None:
                # Estadísticas consolidadas
                ventas_consolidadas = []
                for sheet in ['POS1', 'POS2', 'POS3']:
                    ventas_consolidadas.extend(self.ventas_memory.get(sheet, []))
                ventas = ventas_consolidadas
                terminal_nombre = "General (Todas las Terminales)"
            else:
                # Estadísticas de terminal específico
                ventas = self.ventas_memory.get(terminal_id, [])
                terminal_nombre = f"Terminal {terminal_id}"
                
            if not ventas:
                return self._estadisticas_vacias(terminal_nombre)
            
            # Calcular métricas
            ids_venta_unicos = set(venta['ID_Venta'] for venta in ventas)
            total_ventas = len(ids_venta_unicos)
            ingresos_totales = sum(venta['Total_Venta'] for venta in ventas)
            
            ventas_hoy = [venta for venta in ventas if venta['Fecha'] == date.today().strftime("%Y-%m-%d")]
            ventas_hoy_ids = set(venta['ID_Venta'] for venta in ventas_hoy)
            ventas_hoy_count = len(ventas_hoy_ids)
            
            productos_disponibles = len(self.catalogo)
            
            return {
                'ventas_totales': total_ventas,
                'ingresos_totales': f"{self.config['moneda']}{ingresos_totales:,.2f}",
                'productos_catalogo': productos_disponibles,
                'usuarios_activos': 1,
                'ventas_hoy_count': ventas_hoy_count,
                'dashboard_nombre': f"Dashboard - {terminal_nombre}",
                'terminal_actual': terminal_id or "TODAS"
            }
        except Exception:
            return self._estadisticas_vacias(terminal_id or "TODAS")

    def _estadisticas_vacias(self, terminal_nombre):
        return {
            'ventas_totales': 0,
            'ingresos_totales': f"{self.config['moneda']}0.00",
            'productos_catalogo': len(self.catalogo),
            'usuarios_activos': 1,
            'ventas_hoy_count': 0,
            'dashboard_nombre': f"Dashboard - {terminal_nombre}",
            'terminal_actual': "TODAS"
        }

    def obtener_estadisticas_por_terminal(self):
        stats = {}
        for terminal in ['POS1', 'POS2', 'POS3']:
            stats[terminal] = self.obtener_estadisticas_dashboard(terminal)
        return stats

# Instancia global
try:
    sistema = SistemaPocopan()
    print("✅ Sistema POCOPAN listo en Vercel")
except Exception as e:
    print(f"❌ Error iniciando sistema: {e}")
    sistema = None

# --- DECORADORES DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session.get('rol') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS ---
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
                return redirect(url_for('index'))
        
        return render_template('login.html', error='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

@app.route('/')
@login_required
def index():
    if sistema is None:
        return render_template('error.html', mensaje="Sistema no disponible")
    
    usuario = session.get('usuario')
    rol = session.get('rol')
    terminal = session.get('terminal')
        
    carrito_actual = get_carrito()
    totales = sistema.calcular_totales(carrito_actual)
    
    contador_actual = sistema.contadores_memory[terminal]["ultimo_cliente"] + 1
    
    return render_template('pos.html', 
                           sistema=sistema,
                           carrito=carrito_actual, 
                           totales=totales,
                           usuario_actual=usuario,
                           rol_actual=rol,
                           terminal_actual=terminal,
                           id_cliente_actual=f"CLIENTE-{terminal}-{contador_actual:04d}")

@app.route('/dashboard')
@login_required
def dashboard():
    if sistema is None:
        return redirect(url_for('index'))
    
    rol = session.get('rol')
    terminal = session.get('terminal')
    
    if rol == 'admin':
        stats = sistema.obtener_estadisticas_dashboard("TODAS")
        stats_por_terminal = sistema.obtener_estadisticas_por_terminal()
    else:
        stats = sistema.obtener_estadisticas_dashboard(terminal)
        stats_por_terminal = {}
    
    return render_template('dashboard.html', 
                           stats=stats,
                           stats_por_terminal=stats_por_terminal,
                           empresa=sistema.config['empresa'],
                           sistema=sistema,
                           rol_actual=rol,
                           terminal_actual=terminal,
                           now=datetime.now())

@app.route('/dashboard/<terminal_id>')
@admin_required
def dashboard_terminal(terminal_id):
    if sistema is None:
        return redirect(url_for('index'))
        
    if terminal_id not in ['POS1', 'POS2', 'POS3', 'TODAS']:
        return redirect(url_for('dashboard'))
    
    stats = sistema.obtener_estadisticas_dashboard(terminal_id)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           stats_por_terminal={},
                           empresa=sistema.config['empresa'],
                           sistema=sistema,
                           rol_actual='admin',
                           terminal_actual=terminal_id,
                           now=datetime.now())

@app.route('/diagnostico')
def diagnostico():
    if sistema is None:
        return jsonify({
            'status': 'ERROR',
            'mensaje': 'Sistema POCOPAN no pudo inicializarse'
        }), 500
        
    return jsonify({
        'status': 'OK',
        'mensaje': 'Sistema POCOPAN operativo',
        'terminal': 'Vercel Serverless',
        'catalogo_cargado': sistema.catalogo_cargado,
        'productos_en_catalogo': len(sistema.productos_disponibles),
        'ventas_registradas': sum(len(ventas) for ventas in sistema.ventas_memory.values())
    })

@app.route('/buscar-productos')
def buscar_productos_route():
    if sistema is None:
        return jsonify([])
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
        
    productos = sistema.buscar_productos(query)
    return jsonify(productos)

@app.route('/detalles-producto/<path:producto_nombre>')
def detalles_producto(producto_nombre):
    if sistema is None:
        return jsonify({'error': 'Sistema no disponible'}), 500
        
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        
        detalles = sistema.obtener_detalles_producto(producto_limpio)
        if detalles:
            return jsonify(detalles)
        else:
            return jsonify({'error': f'Producto no encontrado: {producto_limpio}'}), 404
            
    except Exception as e:
        print(f"Error en detalles-producto: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/agregar-carrito', methods=['POST'])
@login_required
def agregar_carrito():
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
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
                'success': True,
                'message': message,
                'carrito': carrito_actual,
                'totales': sistema.calcular_totales(carrito_actual)
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        print(f"Error en agregar-carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
@login_required
def eliminar_carrito(index):
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.eliminar_del_carrito(carrito_actual, index)
    session[f'carrito_{session.get("usuario")}'] = carrito_actual
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/limpiar-carrito', methods=['DELETE'])
@login_required
def limpiar_carrito():
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.limpiar_carrito(carrito_actual)
    session[f'carrito_{session.get("usuario")}'] = carrito_actual
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/finalizar-venta', methods=['POST'])
@login_required
def finalizar_venta():
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    carrito_actual = get_carrito()
    terminal_id = session.get('terminal')
    success, result = sistema.finalizar_venta(carrito_actual, terminal_id)
    
    if success:
        usuario = session.get('usuario')
        session[f'carrito_{usuario}'] = []
        return jsonify({
            'success': True,
            'message': 'Venta finalizada exitosamente',
            'resumen': result,
            'id_cliente_actual': f"CLIENTE-{terminal_id}-{sistema.contadores_memory[terminal_id]['ultimo_cliente'] + 1:04d}"
        })
    else:
        return jsonify({'success': False, 'message': result}), 400

# Ruta para favicon para evitar errores 500
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "sistema": sistema is not None,
        "timestamp": datetime.now().isoformat()
    })

# ... (después de las rutas existentes, antes de los error handlers)

@app.route('/editor-catalogo')
@admin_required
def editor_catalogo():
    """Editor de catálogo solo para administradores"""
    if sistema is None:
        return render_template('error.html', mensaje="Sistema no disponible")
    
    return render_template('editor_catalogo.html', 
                         sistema=sistema,
                         catalogo=sistema.catalogo,
                         usuario_actual=session.get('usuario'),
                         rol_actual=session.get('rol'),
                         terminal_actual=session.get('terminal'))

@app.route('/obtener-producto/<path:producto_nombre>')
@admin_required
def obtener_producto(producto_nombre):
    """Obtener detalles completos de un producto para editar"""
    if sistema is None:
        return jsonify({'error': 'Sistema no disponible'}), 500
        
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        
        # Buscar producto en el catálogo
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_limpio:
                return jsonify(producto)
        
        return jsonify({'error': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error obteniendo producto: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/actualizar-producto', methods=['POST'])
@admin_required
def actualizar_producto():
    """Actualizar un producto en el catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        producto_original = data.get('producto_original', '').strip()
        nuevo_nombre = data.get('nombre', '').strip()
        nueva_categoria = data.get('categoria', '').strip()
        nueva_subcategoria = data.get('subcategoria', '').strip()
        nuevo_precio = data.get('precio_venta', 0)
        nuevo_proveedor = data.get('proveedor', '').strip()
        
        if not producto_original or not nuevo_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Buscar y actualizar el producto
        producto_encontrado = False
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_original:
                # Actualizar datos
                producto['Nombre'] = nuevo_nombre
                producto['Categoría'] = nueva_categoria
                producto['Subcategoría'] = nueva_subcategoria
                producto['Precio Venta'] = float(nuevo_precio)
                producto['Proveedor'] = nuevo_proveedor
                producto_encontrado = True
                break
        
        if producto_encontrado:
            # Actualizar también la lista de productos disponibles
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto actualizado correctamente',
                'producto_actualizado': {
                    'nombre': nuevo_nombre,
                    'categoria': nueva_categoria,
                    'subcategoria': nueva_subcategoria,
                    'precio_venta': float(nuevo_precio),
                    'proveedor': nuevo_proveedor
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error actualizando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/agregar-producto', methods=['POST'])
@admin_required
def agregar_producto():
    """Agregar un nuevo producto al catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        categoria = data.get('categoria', '').strip()
        subcategoria = data.get('subcategoria', '').strip()
        precio_venta = data.get('precio_venta', 0)
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Verificar si el producto ya existe
        for producto in sistema.catalogo:
            if producto['Nombre'].lower() == nombre.lower():
                return jsonify({'success': False, 'message': 'El producto ya existe'}), 400
        
        # Crear nuevo producto
        nuevo_producto = {
            'Nombre': nombre,
            'Categoría': categoria,
            'Subcategoría': subcategoria,
            'Precio Venta': float(precio_venta),
            'Proveedor': proveedor,
            'Estado': 'Disponible'
        }
        
        sistema.catalogo.append(nuevo_producto)
        sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado correctamente',
            'nuevo_producto': nuevo_producto
        })
            
    except Exception as e:
        print(f"Error agregando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-producto', methods=['POST'])
@admin_required
def eliminar_producto():
    """Eliminar un producto del catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        producto_nombre = data.get('producto_nombre', '').strip()
        
        if not producto_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Buscar y eliminar el producto
        producto_encontrado = False
        for i, producto in enumerate(sistema.catalogo):
            if producto['Nombre'] == producto_nombre:
                sistema.catalogo.pop(i)
                producto_encontrado = True
                break
        
        if producto_encontrado:
            # Actualizar también la lista de productos disponibles
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado correctamente'
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error eliminando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# ... (el resto del código se mantiene igual)
@app.route('/editor-catalogo')
@admin_required
def editor_catalogo():
    """Editor de catálogo solo para administradores"""
    if sistema is None:
        return render_template('error.html', mensaje="Sistema no disponible")
    
    return render_template('editor_catalogo.html', 
                         sistema=sistema,
                         catalogo=sistema.catalogo,
                         usuario_actual=session.get('usuario'),
                         rol_actual=session.get('rol'),
                         terminal_actual=session.get('terminal'))

@app.route('/obtener-producto/<path:producto_nombre>')
@admin_required
def obtener_producto(producto_nombre):
    """Obtener detalles completos de un producto para editar"""
    if sistema is None:
        return jsonify({'error': 'Sistema no disponible'}), 500
        
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        
        # Buscar producto en el catálogo
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_limpio:
                return jsonify(producto)
        
        return jsonify({'error': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error obteniendo producto: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/actualizar-producto', methods=['POST'])
@admin_required
def actualizar_producto():
    """Actualizar un producto en el catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        producto_original = data.get('producto_original', '').strip()
        nuevo_nombre = data.get('nombre', '').strip()
        nueva_categoria = data.get('categoria', '').strip()
        nueva_subcategoria = data.get('subcategoria', '').strip()
        nuevo_precio = data.get('precio_venta', 0)
        nuevo_proveedor = data.get('proveedor', '').strip()
        
        if not producto_original or not nuevo_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Buscar y actualizar el producto
        producto_encontrado = False
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_original:
                # Actualizar datos
                producto['Nombre'] = nuevo_nombre
                producto['Categoría'] = nueva_categoria
                producto['Subcategoría'] = nueva_subcategoria
                producto['Precio Venta'] = float(nuevo_precio)
                producto['Proveedor'] = nuevo_proveedor
                producto_encontrado = True
                break
        
        if producto_encontrado:
            # Actualizar también la lista de productos disponibles
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto actualizado correctamente',
                'producto_actualizado': {
                    'nombre': nuevo_nombre,
                    'categoria': nueva_categoria,
                    'subcategoria': nueva_subcategoria,
                    'precio_venta': float(nuevo_precio),
                    'proveedor': nuevo_proveedor
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error actualizando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/agregar-producto', methods=['POST'])
@admin_required
def agregar_producto():
    """Agregar un nuevo producto al catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        categoria = data.get('categoria', '').strip()
        subcategoria = data.get('subcategoria', '').strip()
        precio_venta = data.get('precio_venta', 0)
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Verificar si el producto ya existe
        for producto in sistema.catalogo:
            if producto['Nombre'].lower() == nombre.lower():
                return jsonify({'success': False, 'message': 'El producto ya existe'}), 400
        
        # Crear nuevo producto
        nuevo_producto = {
            'Nombre': nombre,
            'Categoría': categoria,
            'Subcategoría': subcategoria,
            'Precio Venta': float(precio_venta),
            'Proveedor': proveedor,
            'Estado': 'Disponible'
        }
        
        sistema.catalogo.append(nuevo_producto)
        sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado correctamente',
            'nuevo_producto': nuevo_producto
        })
            
    except Exception as e:
        print(f"Error agregando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-producto', methods=['POST'])
@admin_required
def eliminar_producto():
    """Eliminar un producto del catálogo"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        data = request.get_json()
        producto_nombre = data.get('producto_nombre', '').strip()
        
        if not producto_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Buscar y eliminar el producto
        producto_encontrado = False
        for i, producto in enumerate(sistema.catalogo):
            if producto['Nombre'] == producto_nombre:
                sistema.catalogo.pop(i)
                producto_encontrado = True
                break
        
        if producto_encontrado:
            # Actualizar también la lista de productos disponibles
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado correctamente'
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"Error eliminando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)