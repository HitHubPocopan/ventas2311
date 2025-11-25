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
        
        # Solo cargar catálogo desde Excel
        self.catalogo = []
        self.catalogo_cargado = False
        self.productos_disponibles = []
        
        self.cargar_catalogo_desde_excel()
        print("✅ Sistema POCOPAN inicializado - Solo Excel")

    def cargar_catalogo_desde_excel(self):
        """Carga el catálogo desde el archivo Excel"""
        try:
            df = pd.read_excel('catalogo.xlsx')
            self.catalogo = []

            for _, row in df.iterrows():
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

    def obtener_ventas_desde_excel(self, terminal_id=None):
        """Lee todas las ventas desde el archivo Excel"""
        try:
            df = pd.read_excel('ventas.xlsx')
            ventas = df.to_dict('records')
            
            if terminal_id and terminal_id != "TODAS":
                ventas = [v for v in ventas if v.get('ID_Terminal') == terminal_id]
                
            return ventas
        except Exception as e:
            print(f"❌ Error leyendo ventas: {str(e)}")
            return []

    def obtener_contadores_desde_json(self):
        """Lee los contadores desde el archivo JSON"""
        try:
            with open('contadores.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error leyendo contadores: {str(e)}")
            return {
                "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
                "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
                "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
            }

    def guardar_contadores_en_json(self, contadores):
        """Guarda los contadores en el archivo JSON"""
        try:
            with open('contadores.json', 'w') as f:
                json.dump(contadores, f, indent=4)
            return True
        except Exception as e:
            print(f"❌ Error guardando contadores: {str(e)}")
            return False

    def guardar_venta_en_excel(self, nueva_venta):
        """Guarda una nueva venta en el Excel"""
        try:
            # Leer ventas existentes
            try:
                df_existente = pd.read_excel('ventas.xlsx')
            except:
                df_existente = pd.DataFrame(columns=[
                    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto',
                    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
                ])
            
            # Agregar nueva venta
            df_nueva = pd.DataFrame([nueva_venta])
            df_final = pd.concat([df_existente, df_nueva], ignore_index=True)
            
            # Guardar
            df_final.to_excel('ventas.xlsx', index=False)
            return True
        except Exception as e:
            print(f"❌ Error guardando venta: {str(e)}")
            return False

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
            # Leer contadores actuales
            contadores = self.obtener_contadores_desde_json()
            
            # Actualizar contadores
            id_cliente = contadores[terminal_id]["ultimo_cliente"] + 1
            id_venta = contadores[terminal_id]["ultima_venta"] + 1
            
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            # Guardar cada item del carrito
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
                
                # Guardar en Excel
                if not self.guardar_venta_en_excel(nueva_venta):
                    return False, "Error al guardar la venta"
            
            # Actualizar contadores
            contadores[terminal_id]["ultimo_cliente"] = id_cliente
            contadores[terminal_id]["ultima_venta"] = id_venta
            contadores[terminal_id]["total_ventas"] += len(carrito_actual)
            
            # Guardar contadores actualizados
            if not self.guardar_contadores_en_json(contadores):
                return False, "Error al actualizar contadores"
            
            totales = self.calcular_totales(carrito_actual)
            
            return True, {
                'id_venta': id_venta,
                'id_cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                'total_productos': len(carrito_actual),
                'totales': totales,
                'fecha': fecha,
                'hora': hora
            }
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        try:
            ventas = self.obtener_ventas_desde_excel(terminal_id)
            
            if not ventas:
                return self._estadisticas_vacias(terminal_id or "TODAS")
            
            # Calcular métricas
            ids_venta_unicos = set(venta['ID_Venta'] for venta in ventas)
            total_ventas = len(ids_venta_unicos)
            ingresos_totales = sum(venta['Total_Venta'] for venta in ventas)
            
            ventas_hoy = [venta for venta in ventas if venta['Fecha'] == date.today().strftime("%Y-%m-%d")]
            ventas_hoy_ids = set(venta['ID_Venta'] for venta in ventas_hoy)
            ventas_hoy_count = len(ventas_hoy_ids)
            
            productos_disponibles = len(self.catalogo)
            
            if terminal_id == "TODAS" or terminal_id is None:
                terminal_nombre = "General (Todas las Terminales)"
            else:
                terminal_nombre = f"Terminal {terminal_id}"
            
            return {
                'ventas_totales': total_ventas,
                'ingresos_totales': f"{self.config['moneda']}{ingresos_totales:,.2f}",
                'productos_catalogo': productos_disponibles,
                'usuarios_activos': 1,
                'ventas_hoy_count': ventas_hoy_count,
                'dashboard_nombre': f"Dashboard - {terminal_nombre}",
                'terminal_actual': terminal_id or "TODAS"
            }
        except Exception as e:
            print(f"Error en estadísticas: {str(e)}")
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

    def obtener_estadisticas_avanzadas(self, terminal_id="TODAS"):
        """Obtiene estadísticas detalladas para el dashboard"""
        try:
            ventas = self.obtener_ventas_desde_excel(terminal_id)
            
            if not ventas:
                return self._estadisticas_avanzadas_vacias()
            
            fecha_hoy = date.today().strftime("%Y-%m-%d")
            ventas_hoy = [v for v in ventas if v['Fecha'] == fecha_hoy]
            
            # Calcular ingresos
            ingresos_hoy = sum(v['Total_Venta'] for v in ventas_hoy)
            monto_historico = sum(v['Total_Venta'] for v in ventas)
            
            # Productos vendidos hoy
            productos_vendidos_hoy = sum(v['Cantidad'] for v in ventas_hoy)
            
            # Productos más vendidos
            productos_ventas = {}
            for venta in ventas_hoy:
                producto = venta['Producto']
                if producto in productos_ventas:
                    productos_ventas[producto] += venta['Cantidad']
                else:
                    productos_ventas[producto] = venta['Cantidad']
            
            productos_mas_vendidos = sorted(
                [{'producto': k, 'cantidad': v} for k, v in productos_ventas.items()],
                key=lambda x: x['cantidad'],
                reverse=True
            )[:5]
            
            # Promedio diario
            dias_con_ventas = max(1, len(set(v['Fecha'] for v in ventas)))
            promedio_diario = monto_historico / dias_con_ventas
            
            return {
                'ingresos_hoy': ingresos_hoy,
                'productos_vendidos_hoy': productos_vendidos_hoy,
                'monto_historico': monto_historico,
                'promedio_diario': promedio_diario,
                'transacciones_hoy_count': len(ventas_hoy),
                'total_transacciones': len(set(v['ID_Venta'] for v in ventas)),
                'transacciones_hoy': ventas_hoy,
                'productos_mas_vendidos': productos_mas_vendidos
            }
            
        except Exception as e:
            print(f"Error en estadísticas avanzadas: {str(e)}")
            return self._estadisticas_avanzadas_vacias()

    def _estadisticas_avanzadas_vacias(self):
        return {
            'ingresos_hoy': 0,
            'productos_vendidos_hoy': 0,
            'monto_historico': 0,
            'promedio_diario': 0,
            'transacciones_hoy_count': 0,
            'total_transacciones': 0,
            'transacciones_hoy': [],
            'productos_mas_vendidos': []
        }

# Instancia global del sistema
sistema = SistemaPocopan()

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

# --- RUTAS PRINCIPALES ---
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Redirigir según el rol
    if session.get('rol') == 'admin':
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('punto_venta'))

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
                
                # Redirigir según rol
                if user_config['rol'] == 'admin':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('punto_venta'))
        
        return render_template('login.html', error='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/punto-venta')
@login_required
def punto_venta():
    if session.get('rol') == 'admin':
        return redirect(url_for('dashboard'))
    
    usuario = session.get('usuario')
    terminal = session.get('terminal')
    
    # Obtener carrito de la sesión
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    
    carrito_actual = session[f'carrito_{usuario}']
    totales = sistema.calcular_totales(carrito_actual)
    
    # Obtener contador actual
    contadores = sistema.obtener_contadores_desde_json()
    contador_actual = contadores[terminal]["ultimo_cliente"] + 1
    
    return render_template('pos.html', 
                           sistema=sistema,
                           carrito=carrito_actual, 
                           totales=totales,
                           usuario_actual=usuario,
                           rol_actual=session.get('rol'),
                           terminal_actual=terminal,
                           id_cliente_actual=f"CLIENTE-{terminal}-{contador_actual:04d}")

@app.route('/dashboard')
@login_required
def dashboard():
    rol = session.get('rol')
    terminal = session.get('terminal')
    
    if rol == 'admin':
        stats = sistema.obtener_estadisticas_dashboard("TODAS")
        stats_avanzadas = sistema.obtener_estadisticas_avanzadas("TODAS")
    else:
        stats = sistema.obtener_estadisticas_dashboard(terminal)
        stats_avanzadas = sistema.obtener_estadisticas_avanzadas(terminal)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           stats_avanzadas=stats_avanzadas,
                           empresa=sistema.config['empresa'],
                           sistema=sistema,
                           rol_actual=rol,
                           terminal_actual=terminal,
                           now=datetime.now())

@app.route('/dashboard/<terminal_id>')
@admin_required
def dashboard_terminal(terminal_id):
    if terminal_id not in ['POS1', 'POS2', 'POS3', 'TODAS']:
        return redirect(url_for('dashboard'))
    
    stats = sistema.obtener_estadisticas_dashboard(terminal_id)
    stats_avanzadas = sistema.obtener_estadisticas_avanzadas(terminal_id)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           stats_avanzadas=stats_avanzadas,
                           empresa=sistema.config['empresa'],
                           sistema=sistema,
                           rol_actual='admin',
                           terminal_actual=terminal_id,
                           now=datetime.now())

# ... (continuaría con las demás rutas del carrito, API, etc.)

# Rutas de API para el carrito
def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

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
                'success': True,
                'message': message,
                'carrito': carrito_actual,
                'totales': sistema.calcular_totales(carrito_actual)
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
@login_required
def eliminar_carrito(index):
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
    carrito_actual = get_carrito()
    terminal_id = session.get('terminal')
    success, result = sistema.finalizar_venta(carrito_actual, terminal_id)
    
    if success:
        usuario = session.get('usuario')
        session[f'carrito_{usuario}'] = []
        return jsonify({
            'success': True,
            'message': 'Venta finalizada exitosamente',
            'resumen': result
        })
    else:
        return jsonify({'success': False, 'message': result}), 400

# Rutas de API para productos
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
        detalles = sistema.obtener_detalles_producto(producto_decodificado)
        if detalles:
            return jsonify(detalles)
        else:
            return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor'}), 500

# Rutas del editor de catálogo (solo admin)
@app.route('/editor-catalogo')
@admin_required
def editor_catalogo():
    return render_template('editor_catalogo.html', 
                         sistema=sistema,
                         catalogo=sistema.catalogo,
                         usuario_actual=session.get('usuario'),
                         rol_actual=session.get('rol'),
                         terminal_actual=session.get('terminal'))

@app.route('/obtener-producto/<path:producto_nombre>')
@admin_required
def obtener_producto(producto_nombre):
    try:
        producto_decodificado = unquote(producto_nombre)
        
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_decodificado:
                return jsonify(producto)
        
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/actualizar-producto', methods=['POST'])
@admin_required
def actualizar_producto():
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
                producto['Nombre'] = nuevo_nombre
                producto['Categoría'] = nueva_categoria
                producto['Subcategoría'] = nueva_subcategoria
                producto['Precio Venta'] = float(nuevo_precio)
                producto['Proveedor'] = nuevo_proveedor
                producto_encontrado = True
                break
        
        if producto_encontrado:
            # Guardar cambios en Excel
            df_catalogo = pd.DataFrame(sistema.catalogo)
            df_catalogo.to_excel('catalogo.xlsx', index=False)
            
            # Actualizar lista de productos disponibles
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto actualizado correctamente'
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/agregar-producto', methods=['POST'])
@admin_required
def agregar_producto():
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
        
        # Guardar en Excel
        df_catalogo = pd.DataFrame(sistema.catalogo)
        df_catalogo.to_excel('catalogo.xlsx', index=False)
        
        sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado correctamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-producto', methods=['POST'])
@admin_required
def eliminar_producto():
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
            # Guardar en Excel
            df_catalogo = pd.DataFrame(sistema.catalogo)
            df_catalogo.to_excel('catalogo.xlsx', index=False)
            
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado correctamente'
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Ruta de diagnóstico
@app.route('/diagnostico')
def diagnostico():
    return jsonify({
        'status': 'OK',
        'mensaje': 'Sistema POCOPAN operativo',
        'catalogo_cargado': sistema.catalogo_cargado,
        'productos_en_catalogo': len(sistema.productos_disponibles),
        'ventas_registradas': len(sistema.obtener_ventas_desde_excel())
    })

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
    