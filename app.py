from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime, date
import sqlite3, io, os

import pandas as pd

app = Flask(__name__)

def init_db():
    with sqlite3.connect('my_database.db') as conn:
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())

def obtener_productos():
    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return productos

@app.route("/")
def index():
    busqueda = request.args.get("q", "")

    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if busqueda:
        cursor.execute("""
            SELECT * FROM productos
            WHERE nombre LIKE ? OR categoria LIKE ?
        """, (f"%{busqueda}%", f"%{busqueda}%"))
    else:
        cursor.execute("SELECT * FROM productos")

    productos = cursor.fetchall()
    conn.close()

    return render_template("index.html", productos=productos, busqueda=busqueda)

# 🔹 NUEVA RUTA PARA AGREGAR
@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        stock_minimo = request.form["stock_minimo"]
        proveedor = request.form["proveedor"]

        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO productos (nombre, categoria, precio, stock, stock_minimo, proveedor)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, categoria, precio, stock, stock_minimo, proveedor))

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("agregar.html")

@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        stock_minimo = request.form["stock_minimo"]
        proveedor = request.form["proveedor"]

        cursor.execute("""
            UPDATE productos
            SET nombre=?, categoria=?, precio=?, stock=?, stock_minimo=?, proveedor=?
            WHERE id=?
        """, (nombre, categoria, precio, stock, stock_minimo, proveedor, id))

        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()

    return render_template("editar.html", producto=producto)

@app.route("/vender/<int:id>", methods=["GET", "POST"])
def vender(id):
    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()

    if request.method == "POST":
        cantidad = int(request.form["cantidad"])

        if cantidad > producto["stock"]:
            conn.close()
            return "No hay suficiente stock disponible."

        # Descontar stock
        nuevo_stock = producto["stock"] - cantidad
        cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id))

        # Registrar venta
        cursor.execute("""
            INSERT INTO ventas (producto_id, cantidad, fecha)
            VALUES (?, ?, ?)
        """, (id, cantidad, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn.close()
    return render_template("vender.html", producto=producto)

@app.route("/ventas")
def ventas():
    hoy = date.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ventas.id,
               productos.nombre,
               ventas.cantidad,
               productos.precio,
               ventas.fecha,
               (ventas.cantidad * productos.precio) as total
        FROM ventas
        JOIN productos ON ventas.producto_id = productos.id
        WHERE ventas.fecha LIKE ?
    """, (f"{hoy}%",))

    ventas_hoy = cursor.fetchall()

    # 🔹 Calcular total general
    total_general = sum(venta["total"] for venta in ventas_hoy)

    conn.close()

    return render_template("ventas.html",
                           ventas=ventas_hoy,
                           hoy=hoy,
                           total_general=total_general)

@app.route("/exportar_ventas")
def exportar_ventas():
    hoy = date.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect('my_database.db')

    query = """
        SELECT productos.nombre as Producto,
               ventas.cantidad as Cantidad,
               productos.precio as Precio,
               (ventas.cantidad * productos.precio) as Total,
               ventas.fecha as Fecha
        FROM ventas
        JOIN productos ON ventas.producto_id = productos.id
        WHERE ventas.fecha LIKE ?
    """

    df = pd.read_sql_query(query, conn, params=(f"{hoy}%",))
    conn.close()

    # Crear archivo en memoria
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(output,
                     download_name=f"ventas_{hoy}.xlsx",
                     as_attachment=True)



if __name__ == '__main__':
    if not os.path.exists('my_database.db'):
        init_db()
    
    app.run(debug=True)
