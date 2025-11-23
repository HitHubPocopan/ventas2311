import pandas as pd
import json
import os

print("--- Creando archivos de inicialización ---")

# 1. Crear ventas.xlsx
ARCHIVO_VENTAS = 'ventas.xlsx'
columnas_ventas = [
    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
]
df_ventas_vacio = pd.DataFrame(columns=columnas_ventas)

try:
    df_ventas_vacio.to_excel(ARCHIVO_VENTAS, index=False, engine='openpyxl')
    print(f"✅ Creado {ARCHIVO_VENTAS} con encabezados.")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_VENTAS}: {e}")

# 2. Crear config.json
ARCHIVO_CONFIG = 'config.json'
config_default = {
    "iva": 21.0,
    "moneda": "$",
    "empresa": "POCOPAN",
    "backup_automatico": False,
    "mostrar_estadisticas_inicio": True
}
try:
    with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config_default, f, indent=4)
    print(f"✅ Creado {ARCHIVO_CONFIG}.")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_CONFIG}: {e}")

# 3. Crear contadores.json
ARCHIVO_CONTADORES = 'contadores.json'
contadores_default = {
    "ultimo_cliente": 0,
    "ultima_venta": 0,
    "total_ventas": 0
}
try:
    with open(ARCHIVO_CONTADORES, 'w', encoding='utf-8') as f:
        json.dump(contadores_default, f, indent=4)
    print(f"✅ Creado {ARCHIVO_CONTADORES}.")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_CONTADORES}: {e}")

print("--- Proceso finalizado ---")