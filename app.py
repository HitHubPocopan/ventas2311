# [file name]: app.py
# [file content begin]
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
from datetime import datetime, date
import json
import os
from werkzeug.utils import secure_filename
import numpy as np
from urllib.parse import unquote
import re
from functools import wraps

# --- CONFIGURACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pocopan_secure_key_2024')

class Config:
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    ARCHIVO_VENTAS = 'ventas.xlsx' 
    ARCHIVO_CONFIG = 'config.json'
    ARCHIVO_CONTADORES = 'contadores.json'
    MAX_CARRITO_ITEMS = 50

app.config.from_object(Config)

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

# --- SISTEMA PRINCIPAL ---
class SistemaPocopan:
    def __init__(self):
        self.contador_clientes = 1
        self.df_catalogo = None
        self.catalogo_cargado = False
        self.productos_disponibles = []
        self._lock = False
        
        self.cargar_config()
        self.cargar_contadores()
        self.cargar_ventas()
        self.cargar_catalogo_automatico()
        print("Sistema POCOPAN inicializado")
    
    def _wait_for_unlock(self):
        import time
        timeout = 5
        start_time = time.time()
        while self._lock and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        if self._lock:
            raise Exception("Timeout: Sistema ocupado")
        self._lock = True
    
    def _release_lock(self):
        self._lock = False

    def cargar_config(self):
        config_default = {
            "iva": 21.0, 
            "moneda": "$", 
            "empresa": "POCOPAN",
            "backup_automatico": False, 
            "mostrar_estadisticas_inicio": True,
            "max_items_carrito": 50,
            "usuarios": {
                "admin": {"password": "admin123", "rol": "admin", "terminal": "TODAS"},
                "pos1": {"password": "pos1123", "rol": "pos", "terminal": "POS1"},
                "pos2": {"password": "pos2123", "rol": "pos", "terminal": "POS2"},
                "pos3": {"password": "pos3123", "rol": "pos", "terminal": "POS3"}
            }
        }
        try:
            if os.path.exists(app.config['ARCHIVO_CONFIG']):
                with open(app.config['ARCHIVO_CONFIG'], 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config = {**config_default, **loaded_config}
            else:
                self.config = config_default
        except Exception as e:
            print(f"Error cargando config: {e}")
            self.config = config_default

    def cargar_contadores(self):
        contadores_default = {
            "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
            "TODAS": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
        }
        try:
            if os.path.exists(app.config['ARCHIVO_CONTADORES']):
                with open(app.config['ARCHIVO_CONTADORES'], 'r', encoding='utf-8') as f:
                    self.contadores = json.load(f)
            else:
                self.contadores = contadores_default
        except Exception as e:
            print(f"Error cargando contadores: {e}")
            self.contadores = contadores_default

    def cargar_ventas(self):
        try:
            if os.path.exists(app.config['ARCHIVO_VENTAS']):
                # Cargar todas las hojas
                self.df_ventas = {}
                xl_file = pd.ExcelFile(app.config['ARCHIVO_VENTAS'])
                for sheet_name in xl_file.sheet_names:
                    self.df_ventas[sheet_name] = pd.read_excel(app.config['ARCHIVO_VENTAS'], sheet_name=sheet_name)
                    
                    columnas_requeridas = ['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                                           'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal']
                    for col in columnas_requeridas:
                        if col not in self.df_ventas[sheet_name].columns:
                            self.df_ventas[sheet_name][col] = ''
            else:
                # Inicializar con hojas vacías
                self.df_ventas = {}
                columnas = ['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                            'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal']
                for sheet in ['POS1', 'POS2', 'POS3', 'TODAS']:
                    self.df_ventas[sheet] = pd.DataFrame(columns=columnas)
        except Exception as e:
            print(f"Error cargando ventas: {e}")
            self.df_ventas = {}
            columnas = ['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                        'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal']
            for sheet in ['POS1', 'POS2', 'POS3', 'TODAS']:
                self.df_ventas[sheet] = pd.DataFrame(columns=columnas)
    
    def cargar_catalogo_automatico(self):
        archivos_posibles = ["catalogo.xlsx", "Pocopan.xlsx", "Pocopan (1).xlsx"]
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                success, message = self.cargar_catalogo(archivo)
                if success:
                    print(f"Catálogo cargado: {message}")
                    return
        print("No se encontró archivo de catálogo")

    # ... (mantener todos los métodos existentes de cargar_catalogo, obtener_detalles_producto, buscar_productos, etc.)

    def finalizar_venta(self, carrito_actual, terminal_id):
        if not carrito_actual:
            return False, "El carrito está vacío"
        
        try:
            self._wait_for_unlock()
            
            # Usar contadores específicos del terminal
            id_cliente = self.contadores[terminal_id]["ultimo_cliente"] + 1
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            # Obtener último ID_Venta del terminal específico
            df_terminal = self.df_ventas.get(terminal_id, pd.DataFrame())
            if df_terminal.empty or 'ID_Venta' not in df_terminal.columns:
                id_venta = 1
            else:
                id_venta = int(df_terminal['ID_Venta'].max() or 0) + 1
            
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
            
            nuevas_ventas_df = pd.DataFrame(nuevas_ventas)
            
            # Guardar en la hoja del terminal específico
            self.df_ventas[terminal_id] = pd.concat([self.df_ventas[terminal_id], nuevas_ventas_df], ignore_index=True)
            
            # También guardar en la hoja TODAS
            self.df_ventas['TODAS'] = pd.concat([self.df_ventas['TODAS'], nuevas_ventas_df], ignore_index=True)
            
            self.guardar_ventas()
            
            # Actualizar contadores del terminal
            self.contadores[terminal_id]["ultimo_cliente"] = id_cliente
            self.contadores[terminal_id]["ultima_venta"] = id_venta
            self.contadores[terminal_id]["total_ventas"] += 1
            self.guardar_contadores()
            
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
        finally:
            self._release_lock()
    
    def guardar_ventas(self):
        try:
            if os.environ.get('VERCEL') != '1':
                with pd.ExcelWriter(app.config['ARCHIVO_VENTAS'], engine='openpyxl') as writer:
                    for sheet_name, df in self.df_ventas.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        except Exception as e:
            print(f"Error guardando ventas: {e}")
            return True

    def guardar_contadores(self):
        try:
            if os.environ.get('VERCEL') != '1':
                with open(app.config['ARCHIVO_CONTADORES'], 'w', encoding='utf-8') as f:
                    json.dump(self.contadores, f, indent=4)
            return True
        except Exception as e:
            print(f"Error guardando contadores: {e}")
            return True

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        try:
            if terminal_id == "TODAS" or terminal_id is None:
                # Estadísticas consolidadas
                ventas_consolidadas = pd.DataFrame()
                for sheet in ['POS1', 'POS2', 'POS3']:
                    if sheet in self.df_ventas:
                        ventas_consolidadas = pd.concat([ventas_consolidadas, self.df_ventas[sheet]])
                ventas = ventas_consolidadas
                terminal_nombre = "General (Todas las Terminales)"
            else:
                # Estadísticas de terminal específico
                ventas = self.df_ventas.get(terminal_id, pd.DataFrame())
                terminal_nombre = f"Terminal {terminal_id}"
                
            if ventas.empty:
                return self._estadisticas_vacias(terminal_nombre)
                
            ventas['Total_Venta'] = pd.to_numeric(ventas['Total_Venta'], errors='coerce').fillna(0)
            
            ventas_hoy = ventas[
                ventas['Fecha'] == date.today().strftime("%Y-%m-%d")
            ]
            
            total_ventas = len(ventas.drop_duplicates(subset=['ID_Venta']))
            ingresos_totales = ventas['Total_Venta'].sum()
            ventas_hoy_count = len(ventas_hoy.drop_duplicates(subset=['ID_Venta']))
            
            productos_disponibles = len(self.df_catalogo) if self.df_catalogo is not None else 0
            
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
            'productos_catalogo': len(self.df_catalogo) if self.df_catalogo is not None else 0,
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
    print("Sistema POCOPAN listo")
except Exception as e:
    print(f"Error iniciando sistema: {e}")
    sistema = None

# --- RUTAS DE AUTENTICACIÓN ---

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

# --- RUTAS PROTEGIDAS ---

def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

@app.route('/')
@login_required
def index():
    if sistema is None:
        return render_template('error.html', 
                             mensaje="Sistema no disponible. Contacte al administrador.")
    
    usuario = session.get('usuario')
    rol = session.get('rol')
    terminal = session.get('terminal')
        
    carrito_actual = get_carrito()
    totales = sistema.calcular_totales(carrito_actual)
    
    # Obtener contador específico del terminal
    contador_actual = sistema.contadores[terminal]["ultimo_cliente"] + 1 if terminal in sistema.contadores else 1
    
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
                           terminal_actual=terminal)

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
                           terminal_actual=terminal_id)

# ... (mantener todas las otras rutas existentes, pero actualizar get_carrito() y finalizar_venta())

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
            'id_cliente_actual': f"CLIENTE-{terminal_id}-{sistema.contadores[terminal_id]['ultimo_cliente'] + 1:04d}"
        })
    else:
        return jsonify({'success': False, 'message': result}), 400

# ... (mantener el resto de rutas igual pero con @login_required)

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
# [file content end]
