import sqlite3
import pandas as pd
import os
import unicodedata

# Función para quitar acentos
def limpiar_acentos(texto):
    if isinstance(texto, str):
        return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

archivo_excel = 'inventarioFerreteria-hm.xlsx'

if not os.path.exists(archivo_excel):
    raise FileNotFoundError(f"El archivo '{archivo_excel}' no se encuentra.")

try:
    with sqlite3.connect('my_database.db') as conn:
        cursor = conn.cursor()

        # 👇 BORRAR TABLA ANTERIOR PARA EVITAR CONFLICTOS
        cursor.execute("DROP TABLE IF EXISTS productos")

        # Crear tabla
        cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS productos(
                   id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   nombre TEXT NOT NULL,
                   categoria TEXT NOT NULL, 
                   precio REAL NOT NULL,
                   stock INTEGER NOT NULL,
                   stock_minimo INTEGER NOT NULL,
                   proveedor TEXT
                   )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
        """)

        # LEER EXCEL
        df = pd.read_excel(archivo_excel)
        
        # Normalizar columnas
        df.columns = df.columns.str.strip().str.lower()
        # 👇 CORRECCIÓN: Usar .map() en lugar de .apply()
        df.columns = df.columns.map(limpiar_acentos)
        df.columns = df.columns.str.replace(" ", "_")

        # Verificar columnas
        print(f"Columnas detectadas: {df.columns.tolist()}")

        columnas_requeridas = ['nombre', 'categoria', 'precio', 'stock', 'stock_minimo', 'proveedor']
        
        if not all(col in df.columns for col in columnas_requeridas):
            faltantes = [col for col in columnas_requeridas if col not in df.columns]
            raise ValueError(f"Faltan columnas: {faltantes}")

        # Insertar datos
        datos = df[columnas_requeridas].values.tolist()
        cursor.executemany("""
        INSERT INTO productos (nombre, categoria, precio, stock, stock_minimo, proveedor)
        VALUES (?, ?, ?, ?, ?, ?)
        """, datos)

        conn.commit()
        print(f"✅ {len(datos)} datos insertados correctamente.")

except Exception as e:
    print(f"❌ Error: {e}")