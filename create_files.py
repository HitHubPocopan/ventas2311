# [file name]: create_files.py
# [file content begin]
import pandas as pd
import json
import os

print("--- Creando archivos de inicialización ---")

# 1. Crear ventas.xlsx con múltiples hojas
ARCHIVO_VENTAS = 'ventas.xlsx'
columnas_ventas = [
    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
]

try:
    with pd.ExcelWriter(ARCHIVO_VENTAS, engine='openpyxl') as writer:
        for sheet in ['POS1', 'POS2', 'POS3', 'TODAS']:
            df_ventas_vacio = pd.DataFrame(columns=columnas_ventas)
            df_ventas_vacio.to_excel(writer, sheet_name=sheet, index=False)
    print(f"✅ Creado {ARCHIVO_VENTAS} con hojas: POS1, POS2, POS3, TODAS.")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_VENTAS}: {e}")

# 2. Crear config.json
ARCHIVO_CONFIG = 'config.json'
config_default = {
    "iva": 21.0,
    "moneda": "$",
    "empresa": "POCOPAN",
    "backup_automatico": False,
    "mostrar_estadisticas_inicio": True,
    "usuarios": {
        "admin": {"password": "admin123", "rol": "admin", "terminal": "TODAS"},
        "pos1": {"password": "pos1123", "rol": "pos", "terminal": "POS1"},
        "pos2": {"password": "pos2123", "rol": "pos", "terminal": "POS2"},
        "pos3": {"password": "pos3123", "rol": "pos", "terminal": "POS3"}
    }
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
    "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "TODAS": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
}
try:
    with open(ARCHIVO_CONTADORES, 'w', encoding='utf-8') as f:
        json.dump(contadores_default, f, indent=4)
    print(f"✅ Creado {ARCHIVO_CONTADORES}.")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_CONTADORES}: {e}")

print("--- Proceso finalizado ---")
# [file content end]
