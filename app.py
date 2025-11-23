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
# ¡IMPORTANTE! Cambia esto en producción por una clave segura de verdad
app.secret_key = os.environ.get('SECRET_KEY', 'pocopan_secret_key_2024') 

class Config:
    # Directorios
    UPLOAD_FOLDER = 'data'
    ARCHIVO_VENTAS = 'data/ventas.xlsx'
    ARCHIVO_CONFIG = 'data/config.json'
    ARCHIVO_CONTADORES = 'data/contadores.json'
    
    # Nuevo: Identificación de esta instancia de la App (Esta es la TERMINAL)
    ID_TERMINAL_ACTUAL = os.environ.get('TERMINAL_ID', 'TERMINAL_1') 

app.config.from_object(Config)

# Crear directorios si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- CLASE PRINCIPAL ---
class SistemaPocopan:   
    def __init__(self):
        # El carrito ya NO es parte de la clase, se gestiona por 'session'
        self.contador_clientes = 1
        self.df_catalogo = None
        self.catalogo_cargado = False
        self.productos_disponibles = []
        
        self.cargar_config()
        self.cargar_contadores()
        self.cargar_ventas()
        self.cargar_catalogo_automatico()
    
        
    def cargar_config(self):
        # ... (Carga de configuración sin cambios)
        config_default = {
            "iva": 0.0,
            "moneda": "$",
            "empresa": "POCOPAN",
            "backup_automatico": True,
            "mostrar_estadisticas_inicio": True
        }
        try:
            if os.path.exists(app.config['ARCHIVO_CONFIG']):
                with open(app.config['ARCHIVO_CONFIG'], 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = config_default
                with open(app.config['ARCHIVO_CONFIG'], 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error cargando config: {e}")
            self.config = config_default

    def cargar_contadores(self):
        # ... (Carga de contadores sin cambios)
        contadores_default = {
            "ultimo_cliente": 0,
            "ultima_venta": 0,
            "total_ventas": 0
        }
        try:
            if os.path.exists(app.config['ARCHIVO_CONTADORES']):
                with open(app.config['ARCHIVO_CONTADORES'], 'r', encoding='utf-8') as f:
                    contadores = json.load(f)
                    self.contador_clientes = contadores.get("ultimo_cliente", 0) + 1
            else:
                self.contador_clientes = 1
                with open(app.config['ARCHIVO_CONTADORES'], 'w', encoding='utf-8') as f:
                    json.dump(contadores_default, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error cargando contadores: {e}")
            self.contador_clientes = 1

    def cargar_ventas(self):
        try:
            if os.path.exists(app.config['ARCHIVO_VENTAS']):
                self.df_ventas = pd.read_excel(app.config['ARCHIVO_VENTAS'])
                print(f"Cargadas {len(self.df_ventas)} ventas existentes")
                
                # AÑADIDO: ID_Terminal en la lista de columnas requeridas
                columnas_requeridas = [
                    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor',
                    'ID_Terminal' 
                ]
                
                for col in columnas_requeridas:
                    if col not in self.df_ventas.columns:
                        self.df_ventas[col] = ''
            else:
                # AÑADIDO: ID_Terminal en el DataFrame nuevo
                self.df_ventas = pd.DataFrame(columns=[
                    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 
                    'ID_Terminal'
                ])
        except Exception as e:
            print(f"Error cargando ventas: {e}")
            # Asegurar que el DataFrame se cree incluso con error
            self.df_ventas = pd.DataFrame(columns=[
                'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 
                'ID_Terminal'
            ])
    
    # Métodos cargar_catalogo_automatico, cargar_catalogo, buscar_productos, obtener_detalles_producto (sin cambios)
    def cargar_catalogo_automatico(self):
        archivos_posibles = ["Pocopan (1).xlsx", "Pocopan.xlsx", "catalogo.xlsx"]
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                self.cargar_catalogo(archivo)
                return
        print("No se encontró archivo de catálogo automáticamente")
    
    def cargar_catalogo(self, archivo_path):
        try:
            self.df_catalogo = pd.read_excel(archivo_path, sheet_name=0)
            self.df_catalogo.columns = [col.strip() for col in self.df_catalogo.columns]
            
            columnas_requeridas = ['Nombre', 'Precio Venta', 'Estado', 'Proveedor', 'Categoría']
            for col in columnas_requeridas:
                if col not in self.df_catalogo.columns:
                    self.df_catalogo[col] = ''
            
            if 'Precio Venta' in self.df_catalogo.columns:
                self.df_catalogo['Precio Venta'] = pd.to_numeric(
                    self.df_catalogo['Precio Venta'], errors='coerce'
                )
            
            self.catalogo_cargado = True
            self.productos_disponibles = self.df_catalogo[
                (self.df_catalogo['Estado'] == 'Disponible') | 
                (self.df_catalogo['Estado'].isna())
            ]['Nombre'].dropna().unique().tolist()
            
            return True, f"Catálogo cargado: {len(self.df_catalogo)} productos"
            
        except Exception as e:
            return False, f"Error cargando catálogo: {str(e)}"
    
    def buscar_productos(self, query):
        if not self.catalogo_cargado or not query:
            return []
        productos_filtrados = [
            producto for producto in self.productos_disponibles 
            if query.lower() in producto.lower()
        ][:10]
        return productos_filtrados
    
    def obtener_detalles_producto(self, producto_nombre):
        if not self.catalogo_cargado or not producto_nombre:
            return None
        
        producto = self.df_catalogo[self.df_catalogo['Nombre'] == producto_nombre]
        if not producto.empty:
            producto = producto.iloc[0]
            return {
                'nombre': producto_nombre,
                'precio': producto.get('Precio Venta', 0),
                'proveedor': producto.get('Proveedor', ''),
                'categoria': producto.get('Categoría', ''),
                'estado': producto.get('Estado', 'Disponible')
            }
        return None

    # MODIFICADO: Ahora recibe el carrito de la sesión
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
        
        subtotal = cantidad * precio
        
        item = {
            'producto': producto_nombre,
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': subtotal,
            'proveedor': detalles['proveedor'],
            'categoria': detalles['categoria']
        }
        
        carrito_actual.append(item)
        return True, "Producto agregado al carrito", carrito_actual
    
    # MODIFICADO: Ahora recibe el carrito de la sesión
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
    
    # MODIFICADO: Ahora recibe el carrito de la sesión
    def limpiar_carrito(self, carrito_actual):
        carrito_actual.clear()
        return True, "Carrito limpiado", carrito_actual
    
    # MODIFICADO: Ahora recibe el carrito de la sesión
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
    
    # MODIFICADO: Ahora recibe el carrito de la sesión
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
                    'ID_Terminal': app.config['ID_TERMINAL_ACTUAL'] # <--- CLAVE MULTI-TERMINAL
                }
                nuevas_ventas.append(nueva_venta)
            
            nuevas_ventas_df = pd.DataFrame(nuevas_ventas)
            self.df_ventas = pd.concat([self.df_ventas, nuevas_ventas_df], ignore_index=True)
            
            self.guardar_ventas()
            self.guardar_contadores()
            
            totales = self.calcular_totales(carrito_actual)
            
            # El carrito se limpia en la ruta después de que la función retorna True
            self.contador_clientes += 1
            
            return True, {
                'id_venta': id_venta,
                'id_cliente': f"CLIENTE-{id_cliente:04d}",
                'total_productos': len(nuevas_ventas),
                'totales': totales
            }
            
        except Exception as e:
            return False, f"Error al guardar la venta: {str(e)}"
    
    # Métodos guardar_ventas y guardar_contadores (sin cambios)
    def guardar_ventas(self):
        try:
            self.df_ventas.to_excel(app.config['ARCHIVO_VENTAS'], index=False)
            return True
        except Exception as e:
            print(f"Error guardando ventas: {e}")
            return False
    
    def guardar_contadores(self):
        try:
            contadores = {
                "ultimo_cliente": self.contador_clientes,
                "ultima_venta": self.df_ventas['ID_Venta'].max() if not self.df_ventas.empty else 0,
                "total_ventas": len(self.df_ventas)
            }
            with open(app.config['ARCHIVO_CONTADORES'], 'w', encoding='utf-8') as f:
                json.dump(contadores, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando contadores: {e}")
            return False
    
    # Dentro de la clase SistemaPocopan:

def obtener_estadisticas_dashboard(self, terminal_id=None):
    # Asegurar que los datos numéricos sean float, ignorando errores
    ventas = self.df_ventas.copy()
    ventas['Total_Venta'] = pd.to_numeric(ventas['Total_Venta'], errors='coerce').fillna(0)
    
    # 1. Filtro por Terminal (si terminal_id es None, se usa todo el DataFrame)
    if terminal_id:
        ventas_filtradas = ventas[ventas['ID_Terminal'] == terminal_id]
        terminal_nombre = terminal_id # Aquí deberías mapear ID a Nombre
    else:
        ventas_filtradas = ventas
        terminal_nombre = "General" # Para el Dashboard Administrador
        
    # 2. Cálculos
    ventas_hoy = ventas_filtradas[
        ventas_filtradas['Fecha'] == date.today().strftime("%Y-%m-%d")
    ]
    
    total_ventas = len(ventas_filtradas.drop_duplicates(subset=['ID_Venta']))
    ingresos_totales = ventas_filtradas['Total_Venta'].sum()
    ventas_hoy_count = len(ventas_hoy.drop_duplicates(subset=['ID_Venta']))
    
    # 3. Productos y Usuarios
    productos_disponibles = len(self.df_catalogo) if self.df_catalogo is not None else 0
    # Nota: El cálculo de usuarios es una simulación ya que no hay DB de usuarios.
    usuarios_activos = 4 # SIMULADO. Debería venir de una base de datos.
    
    return {
        'ventas_totales': total_ventas,
        'ingresos_totales': f"{self.config['moneda']}{ingresos_totales:,.2f}",
        'productos_catalogo': productos_disponibles,
        'usuarios_activos': usuarios_activos,
        'ventas_hoy_count': ventas_hoy_count,
        'dashboard_nombre': f"Dashboard - Pocopan {terminal_nombre}"
    }

# Y asegúrate de que el método 'cargar_ventas' incluya 'ID_Terminal' como se corrigió antes.

# Instancia global del sistema (los datos del catálogo y ventas son comunes a todas las terminales)
sistema = SistemaPocopan()

# --- FUNCIONES AUXILIARES ---
def get_carrito():
    """Inicializa o recupera el carrito de la sesión."""
    if 'carrito' not in session:
        session['carrito'] = []
    return session['carrito']

def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- RUTAS DE LA APLICACIÓN ---
@app.route('/')
def index():
    # Obtener el carrito de la sesión
    carrito_actual = get_carrito()
    totales = sistema.calcular_totales(carrito_actual)
    
    return render_template('index.html', 
                           sistema=sistema,
                           carrito=carrito_actual, # Pasa el carrito de la sesión al template
                           totales=totales,
                           id_cliente_actual=f"CLIENTE-{sistema.contador_clientes:04d}")

@app.route('/buscar-productos')
def buscar_productos():
    # Sin cambios, solo usa el método de la clase
    query = request.args.get('q', '')
    productos = sistema.buscar_productos(query)
    return jsonify(productos)

@app.route('/detalles-producto/<producto_nombre>')
def detalles_producto(producto_nombre):
    # Sin cambios
    detalles = sistema.obtener_detalles_producto(producto_nombre)
    if detalles:
        return jsonify(detalles)
    else:
        return jsonify({'error': 'Producto no encontrado'}), 404

@app.route('/agregar-carrito', methods=['POST'])
def agregar_carrito():
    producto = request.json.get('producto')
    cantidad = request.json.get('cantidad', 1)
    
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.agregar_al_carrito(carrito_actual, producto, cantidad)
    session['carrito'] = carrito_actual # Guardar el carrito modificado en la sesión
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
def eliminar_carrito(index):
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.eliminar_del_carrito(carrito_actual, index)
    session['carrito'] = carrito_actual # Guardar el carrito modificado en la sesión
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400

@app.route('/limpiar-carrito', methods=['DELETE'])
def limpiar_carrito():
    carrito_actual = get_carrito()
    success, message, carrito_actual = sistema.limpiar_carrito(carrito_actual)
    session['carrito'] = carrito_actual # Guardar el carrito limpio en la sesión
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'carrito': carrito_actual,
            'totales': sistema.calcular_totales(carrito_actual)
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400

@app.route('/finalizar-venta', methods=['POST'])
def finalizar_venta():
    carrito_actual = get_carrito()
    success, result = sistema.finalizar_venta(carrito_actual)
    
    if success:
        # Limpiar el carrito de la sesión SOLO si la venta fue exitosa
        session['carrito'] = [] 
        
        return jsonify({
            'success': True,
            'message': 'Venta finalizada exitosamente',
            'resumen': result,
            'id_cliente_actual': f"CLIENTE-{sistema.contador_clientes:04d}"
        })
    else:
        return jsonify({
            'success': False,
            'message': result
        }), 400
@app.route('/dashboard')
def dashboard():
    # Para el Dashboard General (Admin), no pasamos ID_Terminal
    stats = sistema.obtener_estadisticas_dashboard(terminal_id=None)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           empresa=sistema.config['empresa'])
    
@app.route('/cargar-catalogo', methods=['POST'])
def cargar_catalogo():
    # Sin cambios significativos
    if 'archivo' not in request.files:
        return jsonify({'success': False, 'message': 'No se seleccionó archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'success': False, 'message': 'No se seleccionó archivo'}), 400
    
    if archivo and allowed_file(archivo.filename):
        # La función allowed_file ya fue definida arriba
        filename = secure_filename(archivo.filename)
        # Aquí puedes decidir si quieres guardar el archivo con el nombre de la terminal:
        # filename_terminal = f"{app.config['ID_TERMINAL_ACTUAL']}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(filepath)
        
        success, message = sistema.cargar_catalogo(filepath)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'total_productos': len(sistema.df_catalogo),
                'productos_disponibles': len(sistema.productos_disponibles)
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    