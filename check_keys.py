import re
import os

# Read app.py and search for all dictionary key patterns
script_dir = os.path.dirname(os.path.abspath(__file__))
app_py_path = os.path.join(script_dir, 'app.py')

with open(app_py_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Search for product dictionary key patterns
patterns = [
    (r"'Categoria'", "Categoria (sin acento)"),
    (r"'Categoría'", "Categoría (con acento)"),
    (r"'SubCAT'", "SubCAT (mayúsculas)"),
    (r"'Subcategoría'", "Subcategoría (con acento)"),
]

print("=== Búsqueda de patrones de claves en app.py ===\n")
for pattern, description in patterns:
    matches = len(re.findall(pattern, content))
    if matches > 0:
        print(f"✓ Encontrado: {description} - {matches} veces")
    else:
        print(f"✗ NO encontrado: {description}")

print("\n✅ Análisis completado")
