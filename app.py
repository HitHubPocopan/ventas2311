from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import pandas as pd
from datetime import datetime, date
import json
import os
from werkzeug.utils import secure_filename
import numpy as np
import io

# --- CONFIGURACIÓN BASE ---
app = Flask(__name__)
# Usar clave segura en producción
app.secret_key = os.environ.get('SECRET_KEY', 'pocopan_secret_key_2024') 

class Config:
    # Rutas corregidas a la raíz del proyecto para Vercel
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    ARCHIVO_VENTAS = 'ventas.xlsx' 
    ARCHIVO_CONFIG = 'config.json'
    ARCHIVO_CONTADORES = 'contadores.json'
    
    ID_TERMINAL_ACTUAL = os.environ.get('TERMINAL_ID', 'TERMINAL_1') 

app.config.from_object(Config)

# --- CLASE PRINCIPAL ---
class SistemaPocopan:
    def __init__(self):
        self.contador_clientes = 1
        self.df_catalogo = None
        self.catalogo_cargado = False
        self.productos_disponibles = []
        
        # Carga tolerante a fallos
        self.cargar_config()
        self.cargar_contadores()
        self.cargar_ventas()
        self.cargar_catalogo_automatico()
    
    def cargar_config(self):
        config_default = {
            "iva": 21.0, "moneda": "$", "empresa": "POCOPAN",
            "backup_automatico": False, "mostrar_estadisticas_inicio": True
        }
        try:
            if os.path.exists(app.config['ARCHIVO_CONFIG']):
                with open(app.config['ARCHIVO_CONFIG'], 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = config_default
        except Exception as e:
            print(f"Error cargando config (usando default): {e}")
            self.config = config_default

    def cargar_contadores(self):
        contadores_default = {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
        try:
            if os.path.exists(app.config['ARCHIVO_CONTADORES']):
                with open(app.config['ARCHIVO_CONTADORES'], 'r', encoding='utf-8') as f:
                    contadores = json.load(f)
                    self.contador_clientes = contadores.get("ultimo_cliente", 0) + 1
            else:
                self.contador_clientes = 1
        except Exception as e:
            print(f"Error cargando contadores (usando default): {e}")
            self.contador_clientes = 1

    def cargar_ventas(self):
        try:
            if os.path.exists(app.config['ARCHIVO_VENTAS']):
                self.df_ventas = pd.read_excel(app.config['ARCHIVO_VENTAS'])
                columnas_requeridas = ['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                                       'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal']
                for col in columnas_requeridas:
                    if col not in self.df_ventas.columns:
                        self.df_ventas[col] = ''
            else:
                self.df_ventas = pd.DataFrame(columns=['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                                                       'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'])
        except Exception as e:
            print(f"Error fatal cargando ventas (creando DF vacío): {e}")
            self.df_ventas = pd.DataFrame(columns=['ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                                                   'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'])
    
    def cargar_catalogo_automatico(self):
        archivos_posibles = ["Pocopan (1).xlsx", "Pocopan.xlsx", "catalogo.xlsx"]
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                success, message = self.cargar_catalogo(archivo)
                if success:
                    return
        print("ADVERTENCIA: No se encontró ningún archivo de catálogo válido.")

    def cargar_catalogo(self, archivo_path):
        try:
            self.df_catalogo = pd.read_excel(archivo_path, sheet_name=0)
            self.df_catalogo.columns = [col.strip() for col in self.df_catalogo.columns]
            
            # --- CORRECCIÓN CRÍTICA DE COLUMNAS ---
            rename_map = {}
            
            # 1. Renombrar "Categoria" (la tuya) a "Categoría" (la que espera el POS)
            if 'Categoria' in self.df_catalogo.columns:
                rename_map['Categoria'] = 'Categoría'
            
            # 2. Renombrar "SubCAT" a "Subcategoría" (para claridad en el dashboard)
            if 'SubCAT' in self.df_catalogo.columns:
                rename_map['SubCAT'] = 'Subcategoría'
            
            if rename_map:
                self.df_catalogo.rename(columns=rename_map, inplace=True)
            
            # 3. Asegurar columnas clave del POS (Proveedor y Estado no están en tu lista)
            columnas_requeridas_pos = ['Nombre', 'Precio Venta', 'Categoría', 'Proveedor', 'Estado', 'Subcategoría']
            for col in columnas_requeridas_pos:
                if col not in self.df_catalogo.columns:
                    self.df_catalogo[col] = ''
            # --- FIN CORRECCIÓN DE COLUMNAS ---

            if 'Precio Venta' in self.df_catalogo.columns:
                self.df_catalogo['Precio Venta'] = pd.to_numeric(self.df_catalogo['Precio Venta'], errors='coerce').fillna(0)
            
            self.catalogo_cargado = True
            self.productos_disponibles = self.df_catalogo[
                (self.df_catalogo['Estado'] == 'Disponible') | 
                (self.df_catalogo['Estado'].isna())
            ]['Nombre'].dropna().unique().tolist()
            
            return True, f"Catálogo cargado: {len(self.df_catalogo)} productos"
            
        except Exception as e:
            self.df_catalogo = None
            self.catalogo_cargado = False
            self.productos_disponibles = []
            return False, f"Error cargando catálogo {archivo_path}: {str(e)}"
    
    # --- Métodos del Sistema y POS (sin cambios en la lógica) ---

    def buscar_productos(self, query):
        if not self.catalogo_cargado or not query or self.df_catalogo is None:
            return []
        productos_filtrados = [
            producto for producto in self.productos_disponibles 
            if query.lower() in producto.lower()
        ][:10]
        return productos_filtrados
    
    def obtener_detalles_producto(self, producto_nombre):
        if not self.catalogo_cargado or not producto_nombre or self.df_catalogo is None:
            return None
        
        producto = self.df_catalogo[self.df_catalogo['Nombre'] == producto_nombre]
        if not producto.empty:
            producto = producto.iloc[0]
            return {
                'nombre': producto_nombre,
                'precio': producto.get('Precio Venta', 0),
                'proveedor': producto.get('Proveedor', ''),
                'categoria': producto.get('Categoría', ''), # Usa 'Categoría' (renombrada)
                'estado': producto.get('Estado', 'Disponible')
            }
        return None

    def agregar_al_carrito(self, carrito_actual, producto_nombre, cantidad):
        detalles = self.obtener_detalles_producto(producto_nombre)
        if not detalles:
            return False, "Producto no encontrado", carrito_actual
        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                return False, "La cantidad debe ser mayor a 0", carrito_actual
        except ValueError:
            return False, "Cantidad inválida", carrito_actual
        precio = float(detalles['precio'])
        if precio <= 0:
            return False, "El producto no tiene precio válido", carrito_actual
        
        item = {
            'producto': producto_nombre,
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': cantidad * precio,
            'proveedor': detalles['proveedor'],
            'categoria': detalles['categoria']
        }
        carrito_actual.append(item)
        return True, "Producto agregado al carrito", carrito_actual
    
    def eliminar_del_carrito(self, carrito_actual, index):
        try:
            index = int(index)
            if 0 <= index < len(carrito_actual):
                carrito_actual.pop(index)
                return True, "Item eliminado", carrito_actual
            else:
                return False, "Índice inválido", carrito_actual
        except ValueError:
            return False, "Índice inválido", carrito_actual
    
    def limpiar_carrito(self, carrito_actual):
        carrito_actual.clear()
        return True, "Carrito limpiado", carrito_actual
    
    def calcular_totales(self, carrito_actual):
        subtotal = sum(item['subtotal'] for item in carrito_actual)
        iva = subtotal * (self.config.get('iva', 21) / 100)
        total = subtotal + iva
        return {
            'subtotal': subtotal,
            'iva': iva,
            'total': total,
            'porcentaje_iva': self.config.get('iva', 21)
        }

    def finalizar_venta(self, carrito_actual):
        if not carrito_actual:
            return False, "El carrito está vacío"
        
        try:
            id_cliente = self.contador_clientes
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            if self.df_ventas.empty:
                id_venta = 1
            else:
                id_venta = self.df_ventas['ID_Venta'].max() + 1
            
            nuevas_ventas = []
            for item in carrito_actual:
                nueva_venta = {
                    'ID_Venta': id_venta,
                    'Fecha': fecha,
                    'Hora': hora,
                    'ID_Cliente': f"CLIENTE-{id_cliente:04d}",
                    'Producto': item['producto'],
                    'Cantidad': item['cantidad'],
                    'Precio_Unitario': item['precio'],
                    'Total_Venta': item['subtotal'],
                    'Vendedor': 'Sistema Web',
                    'ID_Terminal': app.config['ID_TERMINAL_ACTUAL']
                }
                nuevas_ventas.append(nueva_venta)
            
            nuevas_ventas_df = pd.DataFrame(nuevas_ventas)
            self.df_ventas = pd.concat([self.df_ventas, nuevas_ventas_df], ignore_index=True)
            
            self.guardar_ventas()
            self.guardar_contadores()
            
            totales = self.calcular_totales(carrito_actual)
            self.contador_clientes += 1
            
            return True, {
                'id_venta': id_venta,
                'id_cliente': f"CLIENTE-{id_cliente:04d}",
                'total_productos': len(nuevas_ventas),
                'totales': totales
            }
            
        except Exception as e:
            return False, f"Error al guardar la venta: {str(e)}"
    
    def guardar_ventas(self):
        return True
    
    def guardar_contadores(self):
        return True

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        if self.df_ventas.empty:
            return {
                'ventas_totales': 0,
                'ingresos_totales': f"{self.config['moneda']}0.00",
                'productos_catalogo': len(self.df_catalogo) if self.df_catalogo is not None else 0,
                'usuarios_activos': 4, 
                'ventas_hoy_count': 0,
                'dashboard_nombre': f"Dashboard - Pocopan General"
            }
            
        ventas = self.df_ventas.copy()
        ventas['Total_Venta'] = pd.to_numeric(ventas['Total_Venta'], errors='coerce').fillna(0)
        
        if terminal_id:
            ventas_filtradas = ventas[ventas['ID_Terminal'] == terminal_id]
            terminal_nombre = terminal_id 
        else:
            ventas_filtradas = ventas
            terminal_nombre = "General" 
            
        ventas_hoy = ventas_filtradas[
            ventas_filtradas['Fecha'] == date.today().strftime("%Y-%m-%d")
        ]
        
        total_ventas = len(ventas_filtradas.drop_duplicates(subset=['ID_Venta']))
        ingresos_totales = ventas_filtradas['Total_Venta'].sum() 
        ventas_hoy_count = len(ventas_hoy.drop_duplicates(subset=['ID_Venta']))
        
        productos_disponibles = len(self.df_catalogo) if self.df_catalogo is not None else 0
        usuarios_activos = 4 
        
        return {
            'ventas_totales': total_ventas,
            'ingresos_totales': f"{self.config['moneda']}{ingresos_totales:,.2f}",
            'productos_catalogo': productos_disponibles,
            'usuarios_activos': usuarios_activos,
            'ventas_hoy_count': ventas_hoy_count,
            'dashboard_nombre': f"Dashboard - Pocopan {terminal_nombre}"
        }


# Instancia global del sistema 
try:
    sistema = SistemaPocopan()
except Exception as e:
    print(f"ERROR CRÍTICO AL INICIAR SISTEMA: {e}")
    sistema = None 

# --- RUTAS DE LA APLICACIÓN ---

def get_carrito():
    if 'carrito' not in session:
        session['carrito'] = []
    return session['carrito']

@app.route('/diagnostico')
def diagnostico():
    if sistema is None:
        return jsonify({
            'status': 'FAIL',
            'mensaje': 'La inicialización del SistemaPocopan falló. Revise los archivos de datos (en la raíz).',
            'error_detalle': 'Error no capturado al iniciar SistemaPocopan. Probable falla de lectura de Pandas.'
        }), 500
    return jsonify({
        'status': 'OK',
        'mensaje': 'Flask y el SistemaPocopan se iniciaron correctamente.',
        'terminal': app.config['ID_TERMINAL_ACTUAL'],
        'catalogo_cargado': sistema.catalogo_cargado,
        'productos_en_catalogo': len(sistema.productos_disponibles)
    })

@app.route('/')
def index():
    if sistema is None:
        return redirect(url_for('diagnostico'))
        
    carrito_actual = get_carrito()
    totales = sistema.calcular_totales(carrito_actual)
    
    return render_template('pos.html', 
                           sistema=sistema,
                           carrito=carrito_actual, 
                           totales=totales,
                           id_cliente_actual=f"CLIENTE-{sistema.contador_clientes:04d}")

@app.route('/dashboard')
def dashboard():
    if sistema is None:
        return redirect(url_for('diagnostico'))
        
    stats = sistema.obtener_estadisticas_dashboard(terminal_id=None)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           empresa=sistema.config['empresa'],
                           sistema=sistema) 

@app.route('/buscar-productos')
def buscar_productos_route():
    if sistema is None: return jsonify([])
    query = request.args.get('q', '')
    productos = sistema.buscar_productos(query)
    return jsonify(productos)

@app.route('/detalles-producto/<producto_nombre>')
def detalles_producto(producto_nombre):
    if sistema is None: return jsonify({'error': 'Sistema no inicializado'}), 500
    detalles = sistema.obtener_detalles_producto(producto_nombre)
    if detalles:
        return jsonify(detalles)
    else:
        return jsonify({'error': 'Producto no encontrado'}), 404

@app.route('/agregar-carrito', methods=['POST'])
def agregar_carrito():
    if sistema is None: return jsonify({'success': False, 'message': 'Sistema no inicializado'}), 500
    producto = request.json.get('producto')
    cantidad = request.json.get('cantidad', 1)
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.agregar_al_carrito(carrito_actual, producto, cantidad)
    session['carrito'] = carrito_actual
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
def eliminar_carrito(index):
    if sistema is None: return jsonify({'success': False, 'message': 'Sistema no inicializado'}), 500
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.eliminar_del_carrito(carrito_actual, index)
    session['carrito'] = carrito_actual
    
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
def limpiar_carrito():
    if sistema is None: return jsonify({'success': False, 'message': 'Sistema no inicializado'}), 500
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.limpiar_carrito(carrito_actual)
    session['carrito'] = carrito_actual
    
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
def finalizar_venta():
    if sistema is None: return jsonify({'success': False, 'message': 'Sistema no inicializado'}), 500
    carrito_actual = get_carrito()
    success, result = sistema.finalizar_venta(carrito_actual)
    
    if success:
        session['carrito'] = [] 
        return jsonify({
            'success': True,
            'message': 'Venta finalizada exitosamente',
            'resumen': result,
            'id_cliente_actual': f"CLIENTE-{sistema.contador_clientes:04d}"
        })
    else:
        return jsonify({'success': False, 'message': result}), 400

@app.route('/cargar-catalogo', methods=['POST'])
def cargar_catalogo():
    return jsonify({'success': False, 'message': 'La carga de catálogo por archivo no es soportada en el entorno web Serverless.'}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)