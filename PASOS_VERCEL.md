# Pasos para activar la Base de Datos en Vercel

## 1. Crear Base de Datos PostgreSQL Gratis

### Opción A: Neon (Recomendado - Más fácil)
1. Ir a https://console.neon.tech
2. Registrarse gratis
3. Crear un proyecto
4. Copiar la URL de conexión que empieza con `postgresql://`

### Opción B: Railway
1. Ir a https://railway.app
2. Registrarse con GitHub
3. Crear nuevo proyecto → Add PostgreSQL
4. Copiar la connection string desde el panel

## 2. Agregar Variable de Entorno en Vercel

1. Ir a tu proyecto en Vercel
2. Ir a **Settings** → **Environment Variables**
3. Crear nueva variable:
   - **Name**: `DATABASE_URL`
   - **Value**: Pegar la URL de PostgreSQL completa
   - Click "Add"
4. Hacer re-deploy desde Vercel (o ejecutar `git push` si tienes connected repo)

## 3. Listo!

Ahora la app:
- Usará PostgreSQL en Vercel (datos persisten para siempre)
- Usará SQLite local cuando ejecutes `python app.py` en tu PC
- La edición de catálogo funcionará correctamente
- Todos los cambios se guardan en la BD

## Verificar que Funciona

- Ir a `/diagnostico` y verás:
  - `"database": "PostgreSQL"` si está en Vercel con BD configurada
  - `"database": "SQLite"` si está local

---

**Tips:**
- Si olvidaste la URL de PostgreSQL, puedes copiarla de nuevo y actualizar la variable en Vercel
- Los productos de ejemplo se crean automáticamente la primera vez
- Sin BASE DE DATOS: Los cambios se pierden con cada redeploy/reinicio de Vercel
