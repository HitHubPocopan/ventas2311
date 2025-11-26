#!/usr/bin/env python
import os
import sys

os.environ['VERCEL'] = '0'

sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import app, sistema
    print("✅ App importada correctamente")
    print(f"✅ Sistema inicializado: {sistema is not None}")
    print(f"✅ Catálogo cargado: {sistema.catalogo_cargado}")
    print(f"✅ Productos: {len(sistema.catalogo)}")
    
    with app.test_client() as client:
        print("\n🧪 Probando rutas...")
        
        resp = client.get('/')
        print(f"  GET / → {resp.status_code} (esperado 302 redirect)")
        
        resp = client.get('/login')
        print(f"  GET /login → {resp.status_code} (esperado 200)")
        
        print("\n✅ Todas las pruebas pasaron")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
