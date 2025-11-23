from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
from datetime import datetime, date
import json
import os
from werkzeug.utils import secure_filename
import numpy as np
from urllib.parse import unquote
import re

# --- CONFIGURACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pocopan_secure_key_2024')

class Config:
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    ARCHIVO_VENTAS = 'ventas.xlsx' 
    ARCHIVO_CONFIG = 'config.json'
    ARCHIVO_CONTADORES = 'contadores.json'
    ID_TERMINAL_ACTUAL = os.environ.get('TERMINAL_ID', 'TERMINAL_1')
    MAX_CARRITO_ITEMS = 50

app.config.from_object(Config)

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
            "max_items_carrito": 50
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
        contadores_default = {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
        try:
            if os.path.exists(app.config['ARCHIVO_CONTADORES']):
                with open(app.config['ARCHIVO_CONTADORES'], 'r', encoding='utf-8') as f:
                    contadores = json.load(f)
                    self.contador_clientes = contadores.get("ultimo_cliente", 0) + 1
            else:
                self.contador_clientes = 1
        except Exception as e:
            print(f"Error cargando contadores: {e}")
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
                self.df_ventas = pd.DataFrame(columns=[
                    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
                ])
        except Exception as e:
            print(f"Error cargando ventas: {e}")
            self.df_ventas = pd.DataFrame(columns=[
                'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
                'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
            ])
    
    def cargar_catalogo_automatico(self):
        archivos_posibles = ["catalogo.xlsx", "Pocopan.xlsx", "Pocopan (1).xlsx"]
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                success, message = self.cargar_catalogo(archivo)
                if success:
                    print(f"Catálogo cargado: {message}")
                    return
        print("No se encontró archivo de catálogo")

    def cargar_catalogo(self, archivo_path):
        try:
            self.df_catalogo = pd.read_excel(archivo_path, sheet_name=0)
            self.df_catalogo.columns = [str(col).strip() for col in self.df_catalogo.columns]
            
            rename_map = {}
            if 'Categoria' in self.df_catalogo.columns:
                rename_map['Categoria'] = 'Categoría'
            if 'SubCAT' in self.df_catalogo.columns:
                rename_map['SubCAT'] = 'Subcategoría'
            if 'Precio Venta' not in self.df_catalogo.columns and 'Precio_Venta' in self.df_catalogo.columns:
                rename_map['Precio_Venta'] = 'Precio Venta'
            
            if rename_map:
                self.df_catalogo.rename(columns=rename_map, inplace=True)
            
            columnas_requeridas = ['Nombre', 'Precio Venta', 'Categoría', 'Proveedor', 'Estado', 'Subcategoría']
            for col in columnas_requeridas:
                if col not in self.df_catalogo.columns:
                    self.df_catalogo[col] = ''

            if 'Precio Venta' in self.df_catalogo.columns:
                self.df_catalogo['Precio Venta'] = pd.to_numeric(
                    self.df_catalogo['Precio Venta'], errors='coerce'
                ).fillna(0)
            
            self.catalogo_cargado = True
            self.productos_disponibles = self.df_catalogo[
                (self.df_catalogo['Estado'] == 'Disponible') | 
                (self.df_catalogo['Estado'].isna())
            ]['Nombre'].dropna().unique().tolist()
            
            return True, f"{len(self.df_catalogo)} productos cargados"
            
        except Exception as e:
            self.df_catalogo = None
            self.catalogo_cargado = False
            self.productos_disponibles = []
            return False, f"Error: {str(e)}"
    
    def obtener_detalles_producto(self, producto_nombre):
        if not self.catalogo_cargado or not producto_nombre or self.df_catalogo is None:
            return None
        
        try:
            nombre_limpio = re.sub(r'\s+', ' ', producto_nombre).strip()
            
            producto_exacto = self.df_catalogo[self.df_catalogo['Nombre'] == nombre_limpio]
            
            if not producto_exacto.empty:
                producto = producto_exacto.iloc[0]
            else:
                producto_insensitive = self.df_catalogo[
                    self.df_catalogo['Nombre'].str.strip().str.lower() == nombre_limpio.lower()
                ]
                
                if not producto_insensitive.empty:
                    producto = producto_insensitive.iloc[0]
                else:
                    producto_parcial = self.df_catalogo[
                        self.df_catalogo['Nombre'].str.contains(nombre_limpio, case=False, na=False)
                    ]
                    
                    if not producto_parcial.empty:
                        producto = producto_parcial.iloc[0]
                    else:
                        return None
            
            detalles = {
                'nombre': producto.get('Nombre', nombre_limpio),
                'precio': float(producto.get('Precio Venta', 0)),
                'proveedor': producto.get('Proveedor', ''),
                'categoria': producto.get('Categoría', ''),
                'estado': producto.get('Estado', 'Disponible'),
                'subcategoria': producto.get('Subcategoría', '')
            }
            
            return detalles
            
        except Exception as e:
            print(f"Error obteniendo detalles: {str(e)}")
            return None

    def buscar_productos(self, query, limit=10):
        if not self.catalogo_cargado or not query or self.df_catalogo is None:
            return []
        
        query = query.lower().strip()
        if len(query) < 2:
            return []
        
        try:
            productos_filtrados = [
                producto for producto in self.productos_disponibles 
                if query in producto.lower()
            ][:limit]
            return productos_filtrados
        except Exception:
            return []

    def validar_carrito(self, carrito_actual):
        if len(carrito_actual) >= self.config.get('max_items_carrito', 50):
            return False, "Límite de items en carrito alcanzado"
        return True, "OK"

    def agregar_al_carrito(self, carrito_actual, producto_nombre, cantidad):
        try:
            self._wait_for_unlock()
            
            valid, msg = self.validar_carrito(carrito_actual)
            if not valid:
                return False, msg, carrito_actual

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
                'producto': producto_nombre,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': cantidad * precio,
                'proveedor': detalles['proveedor'],
                'categoria': detalles['categoria'],
                'timestamp': datetime.now().isoformat()
            }
            
            carrito_actual.append(item)
            return True, f"{producto_nombre} agregado al carrito", carrito_actual
            
        except Exception as e:
            return False, f"Error: {str(e)}", carrito_actual
        finally:
            self._release_lock()
    
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
            iva_porcentaje = self.config.get('iva', 21)
            iva = subtotal * (iva_porcentaje / 100)
            total = subtotal + iva
            
            return {
                'subtotal': max(0, subtotal),
                'iva': max(0, iva),
                'total': max(0, total),
                'porcentaje_iva': iva_porcentaje
            }
        except Exception:
            return {'subtotal': 0, 'iva': 0, 'total': 0, 'porcentaje_iva': self.config.get('iva', 21)}

    def finalizar_venta(self, carrito_actual):
        if not carrito_actual:
            return False, "El carrito está vacío"
        
        try:
            self._wait_for_unlock()
            
            id_cliente = self.contador_clientes
            fecha = date.today().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            
            if self.df_ventas.empty or 'ID_Venta' not in self.df_ventas.columns:
                id_venta = 1
            else:
                id_venta = int(self.df_ventas['ID_Venta'].max() or 0) + 1
            
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
                    'Vendedor': 'Sistema Web POCOPAN',
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
                self.df_ventas.to_excel(app.config['ARCHIVO_VENTAS'], index=False, engine='openpyxl')
            return True
        except Exception as e:
            print(f"Error guardando ventas: {e}")
            return True

    def guardar_contadores(self):
        try:
            if os.environ.get('VERCEL') != '1':
                contadores = {
                    "ultimo_cliente": self.contador_clientes - 1,
                    "ultima_venta": self.df_ventas['ID_Venta'].max() if not self.df_ventas.empty else 0,
                    "total_ventas": len(self.df_ventas['ID_Venta'].unique()) if not self.df_ventas.empty else 0
                }
                with open(app.config['ARCHIVO_CONTADORES'], 'w', encoding='utf-8') as f:
                    json.dump(contadores, f, indent=4)
            return True
        except Exception as e:
            print(f"Error guardando contadores: {e}")
            return True

    def obtener_estadisticas_dashboard(self, terminal_id=None):
        try:
            if self.df_ventas.empty:
                return self._estadisticas_vacias(terminal_id)
                
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
            
            return {
                'ventas_totales': total_ventas,
                'ingresos_totales': f"{self.config['moneda']}{ingresos_totales:,.2f}",
                'productos_catalogo': productos_disponibles,
                'usuarios_activos': 1,
                'ventas_hoy_count': ventas_hoy_count,
                'dashboard_nombre': f"Dashboard - POCOPAN {terminal_nombre}",
                'terminal_actual': app.config['ID_TERMINAL_ACTUAL']
            }
        except Exception:
            return self._estadisticas_vacias(terminal_id)

    def _estadisticas_vacias(self, terminal_id):
        terminal_nombre = terminal_id or "General"
        return {
            'ventas_totales': 0,
            'ingresos_totales': f"{self.config['moneda']}0.00",
            'productos_catalogo': len(self.df_catalogo) if self.df_catalogo is not None else 0,
            'usuarios_activos': 1,
            'ventas_hoy_count': 0,
            'dashboard_nombre': f"Dashboard - POCOPAN {terminal_nombre}",
            'terminal_actual': app.config['ID_TERMINAL_ACTUAL']
        }

# Instancia global
try:
    sistema = SistemaPocopan()
    print("Sistema POCOPAN listo")
except Exception as e:
    print(f"Error iniciando sistema: {e}")
    sistema = None

# --- RUTAS ---

def get_carrito():
    if 'carrito' not in session:
        session['carrito'] = []
    return session['carrito']

@app.route('/')
def index():
    if sistema is None:
        return render_template('error.html', 
                             mensaje="Sistema no disponible. Contacte al administrador.")
        
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
        return redirect(url_for('index'))
        
    stats = sistema.obtener_estadisticas_dashboard(terminal_id=None)
    
    return render_template('dashboard.html', 
                           stats=stats,
                           empresa=sistema.config['empresa'],
                           sistema=sistema)

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
        'terminal': app.config['ID_TERMINAL_ACTUAL'],
        'catalogo_cargado': sistema.catalogo_cargado,
        'productos_en_catalogo': len(sistema.productos_disponibles),
        'ventas_registradas': len(sistema.df_ventas) if hasattr(sistema, 'df_ventas') else 0
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
            
    except Exception as e:
        print(f"Error en agregar-carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
def eliminar_carrito(index):
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
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
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
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
    if sistema is None:
        return jsonify({'success': False, 'message': 'Sistema no disponible'}), 500
        
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

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
    