from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date
import json
import os
import re
from urllib.parse import unquote
from functools import wraps
import pandas as pd
import numpy as np

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
        self.cargar_ventas_desde_excel()
        self.cargar_contadores_desde_json()
        
        print("✅ Sistema POCOPAN inicializado correctamente")

    def cargar_catalogo_desde_excel(self):
        """Carga el catálogo desde el archivo Excel - VERSIÓN REPARADA"""
        try:
            print("🔍 Intentando cargar catálogo desde Excel...")
            
            # Verificar si el archivo existe
            if not os.path.exists('catalogo.xlsx'):
                print("❌ Archivo catalogo.xlsx no encontrado")
                self.crear_catalogo_emergencia()
                return
            
            # Leer el archivo Excel
            df = pd.read_excel('catalogo.xlsx')
            print(f"✅ Archivo Excel leído. Columnas encontradas: {df.columns.tolist()}")
            print(f"✅ Número de filas: {len(df)}")
            
            # Limpiar DataFrame - reemplazar NaN por valores por defecto
            df = df.replace({np.nan: None})
            
            # Verificar columnas mínimas requeridas
            columnas_requeridas = ['Nombre', 'Precio Venta']
            for columna in columnas_requeridas:
                if columna not in df.columns:
                    print(f"❌ Columna requerida no encontrada: {columna}")
                    self.crear_catalogo_emergencia()
                    return

            # Limpiar y procesar los datos
            self.catalogo = []
            productos_cargados = 0

            for index, row in df.iterrows():
                try:
                    # Verificar que tenga los datos mínimos necesarios
                    nombre = row['Nombre']
                    precio_venta = row['Precio Venta']
                    
                    if nombre is None or precio_venta is None:
                        print(f"⚠️ Fila {index} saltada: nombre o precio vacío")
                        continue
                    
                    # Convertir y limpiar datos
                    nombre_limpio = str(nombre).strip()
                    if not nombre_limpio:
                        continue
                    
                    try:
                        precio_float = float(precio_venta)
                    except (ValueError, TypeError):
                        print(f"⚠️ Fila {index} saltada: precio inválido '{precio_venta}'")
                        continue
                    
                    # Construir producto con manejo seguro de columnas opcionales
                    producto = {
                        'Nombre': nombre_limpio,
                        'Categoría': str(row['Categoria']).strip() if 'Categoria' in df.columns and row['Categoria'] is not None else 'Sin Categoría',
                        'Subcategoría': str(row['SubCAT']).strip() if 'SubCAT' in df.columns and row['SubCAT'] is not None else '',
                        'Precio Venta': precio_float,
                        'Proveedor': str(row['Proveedor']).strip() if 'Proveedor' in df.columns and row['Proveedor'] is not None else 'Sin Proveedor',
                        'Estado': 'Disponible'
                    }
                    
                    self.catalogo.append(producto)
                    productos_cargados += 1
                    
                except Exception as e:
                    print(f"⚠️ Error procesando fila {index}: {str(e)}")
                    continue

            self.catalogo_cargado = True
            self.productos_disponibles = [p['Nombre'] for p in self.catalogo]

            print(f"✅ Catálogo cargado correctamente: {productos_cargados} productos de {len(df)} filas procesadas")

        except Exception as e:
            print(f"❌ Error crítico cargando catálogo: {str(e)}")
            import traceback
            traceback.print_exc()
            # Crear catálogo de emergencia
            self.crear_catalogo_emergencia()

    def crear_catalogo_emergencia(self):
        """Crea un catálogo mínimo en caso de error"""
        print("🆘 Creando catálogo de emergencia...")
        self.catalogo = [
            {
                'Nombre': 'Cajas Verdes GRANJA ANIMALES DINOS',
                'Categoría': 'Ingenio', 
                'Subcategoría': 'Madera Ingenio',
                'Precio Venta': 25000.0, 
                'Proveedor': 'Proveedor A', 
                'Estado': 'Disponible'
            },
            {
                'Nombre': 'Pezca Gusanos', 
                'Categoría': 'Ingenio', 
                'Subcategoría': 'Madera Ingenio',
                'Precio Venta': 30800.0, 
                'Proveedor': 'Proveedor B', 
                'Estado': 'Disponible'
            },
            {
                'Nombre': 'rompezabeza tubo 150 PIEZAS',
                'Categoría': 'Ingenio',
                'Subcategoría': 'RompeCabezas',
                'Precio Venta': 15000.0,
                'Proveedor': 'Proveedor C',
                'Estado': 'Disponible'
            }
        ]
        self.catalogo_cargado = True
        self.productos_disponibles = [p['Nombre'] for p in self.catalogo]
        print("✅ Catálogo de emergencia creado con 3 productos")

    def cargar_ventas_desde_excel(self):
        """Carga las ventas desde el archivo Excel a memoria"""
        try:
            if not os.path.exists('ventas.xlsx'):
                print("ℹ️ Archivo ventas.xlsx no encontrado, se creará vacío")
                return
                
            df = pd.read_excel('ventas.xlsx')
            df = df.replace({np.nan: None})
            ventas = df.to_dict('records')
            
            # Organizar ventas por terminal
            for venta in ventas:
                if venta:  # Verificar que no sea None
                    terminal = venta.get('ID_Terminal', 'TODAS')
                    if terminal in self.ventas_memory:
                        self.ventas_memory[terminal].append(venta)
                    self.ventas_memory['TODAS'].append(venta)
                
            print(f"✅ Ventas cargadas: {len(ventas)} registros")
        except Exception as e:
            print(f"❌ Error cargando ventas: {str(e)}")

    def cargar_contadores_desde_json(self):
        """Carga los contadores desde el archivo JSON"""
        try:
            if not os.path.exists('contadores.json'):
                print("ℹ️ Archivo contadores.json no encontrado, se usarán contadores por defecto")
                return
                
            with open('contadores.json', 'r') as f:
                self.contadores_memory = json.load(f)
            print("✅ Contadores cargados")
        except Exception as e:
            print(f"❌ Error cargando contadores: {str(e)}")

    def guardar_catalogo_en_excel(self):
        """Guarda el catálogo actual en el archivo Excel - VERSIÓN REPARADA"""
        try:
            if not self.catalogo:
                print("⚠️ No hay productos en el catálogo para guardar")
                return False

            print(f"💾 Guardando {len(self.catalogo)} productos en Excel...")
            
            # Crear DataFrame desde el catálogo en memoria
            datos_para_excel = []
            for producto in self.catalogo:
                datos_para_excel.append({
                    'Nombre': producto['Nombre'],
                    'Categoria': producto['Categoría'],
                    'SubCAT': producto['Subcategoría'],
                    'Precio Venta': producto['Precio Venta'],
                    'Proveedor': producto['Proveedor'],
                    'Estado': producto['Estado']
                })
            
            df_catalogo = pd.DataFrame(datos_para_excel)
            
            # Reemplazar None por strings vacíos para evitar NaN
            df_catalogo = df_catalogo.fillna('')
            
            # Guardar en Excel
            df_catalogo.to_excel('catalogo.xlsx', index=False, engine='openpyxl')
            print(f"✅ Catálogo guardado en Excel: {len(self.catalogo)} productos")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando catálogo en Excel: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def guardar_ventas_en_excel(self):
        """Guarda todas las ventas en el archivo Excel"""
        try:
            # Consolidar todas las ventas
            todas_las_ventas = []
            for terminal, ventas in self.ventas_memory.items():
                if terminal != 'TODAS':  # Evitar duplicados
                    todas_las_ventas.extend(ventas)

            if todas_las_ventas:
                # Crear DataFrame
                df_ventas = pd.DataFrame(todas_las_ventas)
                df_ventas = df_ventas.fillna('')  # Limpiar NaN

                # Guardar en Excel
                df_ventas.to_excel('ventas.xlsx', index=False, engine='openpyxl')
                print(f"✅ Ventas guardadas en Excel: {len(todas_las_ventas)} registros")
            else:
                print("ℹ️ No hay ventas para guardar")
            return True
        except Exception as e:
            print(f"❌ Error guardando ventas en Excel: {str(e)}")
            return False

    def guardar_contadores_en_json(self):
        """Guarda los contadores en el archivo JSON"""
        try:
            with open('contadores.json', 'w') as f:
                json.dump(self.contadores_memory, f, indent=4)
            print("✅ Contadores guardados")
            return True
        except Exception as e:
            print(f"❌ Error guardando contadores: {str(e)}")
            return False

    def obtener_detalles_producto(self, producto_nombre):
        """Obtiene detalles de un producto - VERSIÓN REPARADA"""
        if not self.catalogo_cargado or not producto_nombre:
            return None
        
        try:
            nombre_limpio = re.sub(r'\s+', ' ', producto_nombre).strip()
            print(f"🔍 Buscando producto en memoria: '{nombre_limpio}'")
            print(f"📦 Total de productos en memoria: {len(self.catalogo)}")
            
            # Primero: búsqueda exacta
            for producto in self.catalogo:
                if producto['Nombre'] == nombre_limpio:
                    print(f"✅ Producto encontrado (exacto): {producto['Nombre']}")
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            # Segundo: búsqueda case-insensitive
            for producto in self.catalogo:
                if producto['Nombre'].lower() == nombre_limpio.lower():
                    print(f"✅ Producto encontrado (case-insensitive): {producto['Nombre']}")
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            # Tercero: búsqueda parcial
            for producto in self.catalogo:
                if nombre_limpio.lower() in producto['Nombre'].lower():
                    print(f"✅ Producto encontrado (parcial): {producto['Nombre']}")
                    return {
                        'nombre': producto['Nombre'],
                        'precio': producto['Precio Venta'],
                        'categoria': producto['Categoría'],
                        'subcategoria': producto['Subcategoría'],
                        'proveedor': producto['Proveedor'],
                        'estado': producto['Estado']
                    }
            
            print(f"❌ Producto no encontrado en memoria: {nombre_limpio}")
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo detalles: {str(e)}")
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

    # ... (resto de los métodos se mantienen igual)
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
            
            # Guardar en archivos
            self.guardar_ventas_en_excel()
            self.guardar_contadores_en_json()
            
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

    def obtener_estadisticas_avanzadas(self, terminal_id="TODAS"):
        """Obtiene estadísticas detalladas para el dashboard"""
        try:
            if terminal_id == "TODAS":
                ventas = self.ventas_memory['TODAS']
            else:
                ventas = self.ventas_memory.get(terminal_id, [])
            
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

# Instancia global
try:
    sistema = SistemaPocopan()
    print("✅ Sistema POCOPAN listo")
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
            # Si es una AJAX request, devolver JSON en lugar de redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS ---
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

def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

@app.route('/punto-venta')
@login_required
def punto_venta():
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
    if sistema is None:
        return redirect(url_for('index'))
        
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

@app.route('/diagnostico-catalogo')
@admin_required
def diagnostico_catalogo():
    """Diagnóstico del catálogo - VERSIÓN REPARADA"""
    try:
        # Leer archivo directamente para diagnóstico
        df = pd.read_excel('catalogo.xlsx')
        
        # Limpiar NaN para JSON
        df_clean = df.replace({np.nan: None})
        
        # Convertir a diccionario de manera segura
        primeras_filas = []
        for index, row in df_clean.head(3).iterrows():
            fila_dict = {}
            for columna, valor in row.items():
                # Convertir valores que no son serializables
                if pd.isna(valor):
                    fila_dict[columna] = None
                elif isinstance(valor, (pd.Timestamp, datetime)):
                    fila_dict[columna] = valor.isoformat()
                else:
                    fila_dict[columna] = valor
            primeras_filas.append(fila_dict)
        
        info = {
            'columnas': df.columns.tolist(),
            'filas': len(df),
            'productos_en_memoria': len(sistema.catalogo),
            'catalogo_cargado': sistema.catalogo_cargado,
            'primeras_filas': primeras_filas
        }
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# === RUTAS DEL EDITOR DE CATÁLOGO - COMPLETAMENTE REPARADAS ===
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
    """Obtener detalles completos de un producto para editar - VERSIÓN REPARADA"""
    if sistema is None:
        return jsonify({'error': 'Sistema no disponible'}), 500
        
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        
        print(f"🔍 Buscando producto: '{producto_limpio}'")
        
        # Buscar producto en el catálogo
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_limpio:
                print(f"✅ Producto encontrado: {producto['Nombre']}")
                return jsonify(producto)
        
        # Búsqueda case-insensitive si no se encuentra exacto
        for producto in sistema.catalogo:
            if producto['Nombre'].lower() == producto_limpio.lower():
                print(f"✅ Producto encontrado (case-insensitive): {producto['Nombre']}")
                return jsonify(producto)
        
        print(f"❌ Producto no encontrado: {producto_limpio}")
        return jsonify({'error': 'Producto no encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error obteniendo producto: {str(e)}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/actualizar-producto', methods=['POST'])
@admin_required
def actualizar_producto():
    """Actualizar un producto en el catálogo - VERSIÓN REPARADA"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        # Verificar que los datos son JSON
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        print(f"📝 Datos recibidos para actualizar: {data}")
        
        producto_original = data.get('producto_original', '').strip()
        nuevo_nombre = data.get('nombre', '').strip()
        nueva_categoria = data.get('categoria', '').strip()
        nueva_subcategoria = data.get('subcategoria', '').strip()
        nuevo_precio = data.get('precio_venta', 0)
        nuevo_proveedor = data.get('proveedor', '').strip()
        
        if not producto_original or not nuevo_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Validar precio
        try:
            precio_float = float(nuevo_precio)
            if precio_float <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Precio inválido'}), 400
        
        # Buscar y actualizar el producto
        producto_encontrado = False
        for producto in sistema.catalogo:
            if producto['Nombre'] == producto_original:
                # Actualizar datos
                producto['Nombre'] = nuevo_nombre
                producto['Categoría'] = nueva_categoria
                producto['Subcategoría'] = nueva_subcategoria
                producto['Precio Venta'] = precio_float
                producto['Proveedor'] = nuevo_proveedor
                producto_encontrado = True
                print(f"✅ Producto actualizado en memoria: {nuevo_nombre}")
                break
        
        if producto_encontrado:
            # Guardar cambios en Excel
            if sistema.guardar_catalogo_en_excel():
                # Actualizar también la lista de productos disponibles
                sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
                
                return jsonify({
                    'success': True,
                    'message': f'Producto "{nuevo_nombre}" actualizado correctamente'
                })
            else:
                return jsonify({'success': False, 'message': 'Error al guardar en Excel'}), 500
        else:
            return jsonify({'success': False, 'message': f'Producto no encontrado: {producto_original}'}), 404
            
    except Exception as e:
        print(f"❌ Error actualizando producto: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/agregar-producto', methods=['POST'])
@admin_required
def agregar_producto():
    """Agregar un nuevo producto al catálogo - VERSIÓN REPARADA"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        # Verificar que los datos son JSON
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        print(f"📝 Datos recibidos para agregar: {data}")
        
        nombre = data.get('nombre', '').strip()
        categoria = data.get('categoria', '').strip()
        subcategoria = data.get('subcategoria', '').strip()
        precio_venta = data.get('precio_venta', 0)
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        # Validar precio
        try:
            precio_float = float(precio_venta)
            if precio_float <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Precio inválido'}), 400
        
        # Verificar si el producto ya existe
        for producto in sistema.catalogo:
            if producto['Nombre'].lower() == nombre.lower():
                return jsonify({'success': False, 'message': f'El producto "{nombre}" ya existe'}), 400
        
        # Crear nuevo producto
        nuevo_producto = {
            'Nombre': nombre,
            'Categoría': categoria or 'Sin Categoría',
            'Subcategoría': subcategoria,
            'Precio Venta': precio_float,
            'Proveedor': proveedor or 'Sin Proveedor',
            'Estado': 'Disponible'
        }
        
        sistema.catalogo.append(nuevo_producto)
        print(f"✅ Producto agregado en memoria: {nombre}")
        
        # Guardar en Excel
        if sistema.guardar_catalogo_en_excel():
            sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
            
            return jsonify({
                'success': True,
                'message': f'Producto "{nombre}" agregado correctamente'
            })
        else:
            return jsonify({'success': False, 'message': 'Error al guardar en Excel'}), 500
            
    except Exception as e:
        print(f"❌ Error agregando producto: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-producto', methods=['POST'])
@admin_required
def eliminar_producto():
    """Eliminar un producto del catálogo - VERSIÓN REPARADA"""
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
    try:
        # Verificar que los datos son JSON
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        producto_nombre = data.get('producto_nombre', '').strip()
        
        if not producto_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        print(f"🗑️ Intentando eliminar producto: {producto_nombre}")
        
        # Buscar y eliminar el producto
        producto_encontrado = False
        for i, producto in enumerate(sistema.catalogo):
            if producto['Nombre'] == producto_nombre:
                sistema.catalogo.pop(i)
                producto_encontrado = True
                print(f"✅ Producto eliminado de memoria: {producto_nombre}")
                break
        
        if producto_encontrado:
            # Guardar en Excel
            if sistema.guardar_catalogo_en_excel():
                # Actualizar también la lista de productos disponibles
                sistema.productos_disponibles = [p['Nombre'] for p in sistema.catalogo]
                
                return jsonify({
                    'success': True,
                    'message': f'Producto "{producto_nombre}" eliminado correctamente'
                })
            else:
                return jsonify({'success': False, 'message': 'Error al guardar en Excel'}), 500
        else:
            return jsonify({'success': False, 'message': f'Producto no encontrado: {producto_nombre}'}), 404
            
    except Exception as e:
        print(f"❌ Error eliminando producto: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)