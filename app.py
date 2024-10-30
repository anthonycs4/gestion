import base64
import io
from matplotlib import pyplot as plt
import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, make_response, render_template, request, redirect, send_from_directory, url_for, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'esta_es_una_clave_secreta_muy_segura_1234'

# Configuración de la base de datos MySQL
app.config['MYSQL_HOST'] = 'netdreams.pe'
app.config['MYSQL_USER'] = 'netdrepe_anthony'
app.config['MYSQL_PASSWORD'] = 'itIsnt4u'
app.config['MYSQL_DB'] = 'netdrepe_gestion_de_proyectos'

# Inicializar MySQL con PyMySQL como backend
mysql = MySQL(app)

# Inicializar Bcrypt para encriptar contraseñas
bcrypt = Bcrypt(app)

# Inicializar Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Definir una clase User que funcione con Flask-Login
class User(UserMixin):
    def __init__(self, id, email, nombre):
        self.id = id
        self.email = email
        self.nombre = nombre

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_usuario, correo, nombre FROM Usuario WHERE id_usuario = %s", (user_id,))
    user = cur.fetchone()
    if user:
        return User(id=user[0], email=user[1], nombre=user[2])
    return None

# Ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para registrar usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        
        # Encriptar la contraseña
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Verificar si el correo ya está registrado
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Usuario WHERE correo = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('El correo ya está registrado. Por favor, inicia sesión.', 'danger')
            return redirect(url_for('login'))
        
        # Insertar el nuevo usuario en la base de datos
        cur.execute("INSERT INTO Usuario (nombre, correo, password) VALUES (%s, %s, %s)", 
                    (nombre, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('¡Cuenta creada con éxito! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('index.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id_usuario, correo, password, nombre FROM Usuario WHERE correo = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[2], password):
            # Crear un objeto User y loguear al usuario
            user_obj = User(id=user[0], email=user[1], nombre=user[3])
            login_user(user_obj)
            flash('Has iniciado sesión con éxito.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Datos incorrectos. Por favor, verifica tu correo o contraseña.', 'danger')

    return render_template('proyectos.html')

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    # Obtener solo los proyectos en los que el usuario logueado es miembro
    cur.execute("""
        SELECT p.id_proyecto, p.nombre, p.fechainicio, p.fechafin, p.descripcion, p.estado
        FROM Proyecto p
        JOIN Miembro_Proyecto mp ON p.id_proyecto = mp.id_proyecto
        WHERE mp.id_usuario = %s
    """, (current_user.id,))
    proyectos = cur.fetchall()  # Obtenemos los proyectos del usuario logueado
    cur.close()

    return render_template('proyectos.html', proyectos=proyectos)

@app.route('/register_user', methods=['GET', 'POST'])
@login_required
def register_user():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']  # Asegúrate de obtener 'apellido' del formulario
        email = request.form['email']
        password = request.form['password']
        rol = request.form['rol']
        metodologia = request.form['metodologia']
        
        # Encriptar la contraseña
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Validar si el correo ya está registrado
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Usuario WHERE correo = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('El correo ya está registrado. Por favor, usa otro correo.', 'danger')
            return redirect(url_for('register_user'))
        
        # Insertar el nuevo usuario en la tabla de Usuario
        cur.execute("""
            INSERT INTO Usuario (nombre, apellido, correo, password)
            VALUES (%s, %s, %s, %s)
        """, (nombre, apellido, email, hashed_password))
        mysql.connection.commit()

        # Obtener el ID del nuevo usuario insertado
        new_user_id = cur.lastrowid

        # Insertar en la tabla Miembro_Proyecto el nuevo miembro con su rol
        cur.execute("""
            INSERT INTO Miembro_Proyecto (id_usuario, id_rol, id_proyecto)
            VALUES (%s, %s, %s)
        """, (new_user_id, rol, metodologia))  # Aquí 'metodologia' sería el id_proyecto si aplica
        mysql.connection.commit()
        
        cur.close()

        flash('¡Usuario registrado con éxito!', 'success')
        return redirect(url_for('proyectos'))  # Redirigir a la página de dashboard

    # Si es GET, mostramos el formulario de registro
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_rol, nombre FROM Rol")  # Obtener los roles de la tabla Rol
    roles = cur.fetchall()

    cur.execute("SELECT id_metodologia, nombre FROM Metodologia")  # Obtener las metodologías
    metodologias = cur.fetchall()
    
    cur.close()

    return render_template('register_user.html', roles=roles, metodologias=metodologias)







from flask_login import current_user

@app.route('/crear_proyecto', methods=['GET', 'POST'])
@login_required
def crear_proyecto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        fechainicio = request.form['fechainicio']
        fechafin = request.form['fechafin']
        estado = request.form['estado']

        if not nombre or not descripcion or not fechainicio or not fechafin:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('crear_proyecto'))

        # Obtener el ID del usuario logueado
        id_usuario = current_user.id
        
        cur = mysql.connection.cursor()
        # Insertar el proyecto en la tabla Proyecto
        cur.execute("""
            INSERT INTO Proyecto (nombre, descripcion, fechainicio, fechafin, estado)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, descripcion, fechainicio, fechafin, estado))
        mysql.connection.commit()

        # Obtener el ID del proyecto recién insertado
        id_proyecto = cur.lastrowid

        # Insertar en la tabla Miembro_Proyecto para asociar al usuario logueado con el proyecto
        cur.execute("""
            INSERT INTO Miembro_Proyecto (id_usuario, id_proyecto, id_rol)
            VALUES (%s, %s, %s)
        """, (id_usuario, id_proyecto, 1))  # Asignamos el rol de 'Líder de Proyecto' como ejemplo
        mysql.connection.commit()
        cur.close()

        flash('Proyecto creado con éxito', 'success')
        return redirect(url_for('dashboard'))

    return render_template('crear_proyecto.html')


@app.route('/editar_proyecto/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_proyecto(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Proyecto WHERE id_proyecto = %s", (id,))
    proyecto = cur.fetchone()
    cur.close()

    # Ajustar los índices de acuerdo con los datos correctos
    nombre = proyecto[2]
    descripcion = proyecto[3]
    fechainicio = proyecto[4]  # Cambiado al índice correcto
    fechafin = proyecto[5]  # Cambiado al índice correcto
    estado = proyecto[7]  # Estado del proyecto

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        fechainicio = request.form['fechainicio']
        fechafin = request.form['fechafin']
        estado = request.form['estado']
        
        if not nombre or not descripcion or not fechainicio or not fechafin:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('editar_proyecto', id=id))
        
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE Proyecto
            SET nombre = %s, descripcion = %s, fechainicio = %s, fechafin = %s, estado = %s
            WHERE id_proyecto = %s
        """, (nombre, descripcion, fechainicio, fechafin, estado, id))
        mysql.connection.commit()
        cur.close()

        flash('Proyecto editado con éxito', 'success')
        return redirect(url_for('dashboard'))

    return render_template('editar_proyecto.html', proyecto=proyecto, fechainicio=fechainicio, fechafin=fechafin)

# Ruta para deshabilitar o habilitar un proyecto
@app.route('/deshabilitar_proyecto/<int:id>', methods=['GET'])
@login_required
def deshabilitar_proyecto(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT estado FROM Proyecto WHERE id_proyecto = %s", (id,))
    proyecto = cur.fetchone()
    
    nuevo_estado = 'Inactivo' if proyecto[0] == 'Activo' else 'Activo'
    
    cur.execute("""
        UPDATE Proyecto
        SET estado = %s
        WHERE id_proyecto = %s
    """, (nuevo_estado, id))
    mysql.connection.commit()
    cur.close()

    flash(f'Proyecto {"deshabilitado" if nuevo_estado == "Inactivo" else "habilitado"} con éxito', 'success')
    return redirect(url_for('dashboard'))


@app.route('/configurar_metodologia/<int:id>', methods=['GET', 'POST'])
@login_required
def configurar_metodologia(id):
    cur = mysql.connection.cursor()
    
    # Obtener el proyecto correspondiente al id
    cur.execute("SELECT * FROM Proyecto WHERE id_proyecto = %s", (id,))
    proyecto = cur.fetchone()

    # Obtener la lista de metodologías disponibles
    cur.execute("SELECT * FROM Metodologia")
    metodologias = cur.fetchall()
    
    if request.method == 'POST':
        id_metodologia = request.form['metodologia']
        
        # Actualizar la metodología asociada al proyecto
        cur.execute("UPDATE Proyecto SET id_metodologia = %s WHERE id_proyecto = %s", (id_metodologia, id))
        mysql.connection.commit()
        cur.close()

        flash('Metodología configurada con éxito', 'success')
        return redirect(url_for('dashboard'))

    cur.close()
    return render_template('configurar_metodologia.html', proyecto=proyecto, metodologias=metodologias)






@app.route('/proyecto/<int:id>/tareas', methods=['GET'])
@login_required
def ver_tareas(id):
    # Conexión a la base de datos
    cur = mysql.connection.cursor()
    
    # Obtener las tareas del proyecto
    cur.execute("SELECT * FROM Tarea WHERE id_proyecto = %s", (id,))
    tareas = cur.fetchall()
    
    # Obtener los usuarios asignados a este proyecto
    cur.execute("""
        SELECT Usuario.id_usuario, Usuario.nombre, Usuario.apellido 
        FROM Usuario
        JOIN Miembro_Proyecto ON Usuario.id_usuario = Miembro_Proyecto.id_usuario
        WHERE Miembro_Proyecto.id_proyecto = %s
    """, (id,))
    usuarios = cur.fetchall()  # Obtiene solo los usuarios asignados al proyecto actual
    
    # Cerrar cursor
    cur.close()

    # Pasar tareas y usuarios al template
    return render_template('tareas.html', tareas=tareas, usuarios=usuarios, id_proyecto=id)


@app.route('/proyecto/<int:id>/tareas/crear', methods=['POST'])
@login_required
def crear_tarea(id):
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    fecha_inicio = request.form['fecha_inicio']
    fecha_fin = request.form['fecha_fin']
    id_asignado_a = request.form['asignado_a']

    if not nombre or not descripcion or not fecha_inicio or not fecha_fin or not id_asignado_a:
        flash('Todos los campos son obligatorios', 'danger')
        return redirect(url_for('ver_tareas', id=id))

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO Tarea (nombre, descripcion, fecha_inicio, fecha_fin, id_proyecto, id_asignado_a)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, descripcion, fecha_inicio, fecha_fin, id, id_asignado_a))
    mysql.connection.commit()
    cur.close()

    flash('Tarea creada con éxito', 'success')
    return redirect(url_for('ver_tareas', id=id))

from datetime import date, timedelta

@app.route('/notificaciones')
@login_required
def notificaciones():
    cur = mysql.connection.cursor()
    
    # Obtener la fecha actual
    hoy = date.today()
    
    # Definir el rango para próximas tareas (por ejemplo, 3 días antes de la fecha de fin)
    proximas_tareas = hoy + timedelta(days=3)

    # Consultar tareas próximas a vencer (fecha_fin está dentro de los próximos 3 días)
    cur.execute("SELECT * FROM Tarea WHERE fecha_fin BETWEEN %s AND %s AND estado = 'Pendiente'", (hoy, proximas_tareas))
    tareas_proximas = cur.fetchall()

    # Consultar tareas retrasadas (fecha_fin ya pasó)
    cur.execute("SELECT * FROM Tarea WHERE fecha_fin < %s AND estado = 'Pendiente'", (hoy,))
    tareas_retrasadas = cur.fetchall()
    
    cur.close()
    
    return render_template('notificaciones.html', tareas_proximas=tareas_proximas, tareas_retrasadas=tareas_retrasadas)


@app.route('/proyecto/<int:id>/miembros', methods=['GET'])
@login_required
def ver_miembros(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT m.id_miembro, u.nombre, u.apellido, r.nombre 
        FROM Miembro_Proyecto m
        JOIN Usuario u ON m.id_usuario = u.id_usuario
        JOIN Rol r ON m.id_rol = r.id_rol
        WHERE m.id_proyecto = %s AND m.estado = 'Activo'
    """, (id,))
    miembros = cur.fetchall()
    cur.close()

    return render_template('miembros.html', miembros=miembros, id_proyecto=id)
@app.route('/proyecto/<int:id>/miembros/añadir', methods=['GET', 'POST'])
@login_required
def añadir_miembro(id):
    if request.method == 'POST':
        usuario_id = request.form['usuario']
        rol = request.form['rol']

        # Verificar que todos los campos estén completos
        if not usuario_id or not rol:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('añadir_miembro', id=id))

        cur = mysql.connection.cursor()
        # Insertar el nuevo miembro en el proyecto
        cur.execute("INSERT INTO Miembro_Proyecto (id_usuario, id_rol, id_proyecto, estado) VALUES (%s, %s, %s, 'Activo')", (usuario_id, rol, id))
        mysql.connection.commit()
        cur.close()

        flash('Miembro añadido con éxito', 'success')
        return redirect(url_for('ver_miembros', id=id))

    # Obtener usuarios disponibles que no estén asignados actualmente al proyecto
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.id_usuario, u.nombre, u.apellido 
        FROM Usuario u
        WHERE NOT EXISTS (
            SELECT 1 FROM Miembro_Proyecto mp 
            WHERE mp.id_usuario = u.id_usuario AND mp.id_proyecto = %s
        )
    """, (id,))
    usuarios_disponibles = cur.fetchall()

    # Obtener roles disponibles
    cur.execute("SELECT * FROM Rol")
    roles = cur.fetchall()
    cur.close()

    return render_template('añadir_miembro.html', usuarios=usuarios_disponibles, roles=roles, id_proyecto=id)


@app.route('/proyecto/<int:id_proyecto>/miembros/editar/<int:id_miembro>', methods=['GET', 'POST'])
@login_required
def editar_miembro(id_proyecto, id_miembro):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nuevo_rol = request.form['rol']
        cur.execute("UPDATE Miembro_Proyecto SET id_rol = %s WHERE id_miembro = %s", (nuevo_rol, id_miembro))
        mysql.connection.commit()
        cur.close()

        flash('Miembro editado con éxito', 'success')
        return redirect(url_for('ver_miembros', id=id_proyecto))

    # Obtener los datos del miembro actual
    cur.execute("""
        SELECT u.nombre, u.apellido, r.id_rol, r.nombre
        FROM Miembro_Proyecto m
        JOIN Usuario u ON m.id_usuario = u.id_usuario
        JOIN Rol r ON m.id_rol = r.id_rol
        WHERE m.id_miembro = %s
    """, (id_miembro,))
    miembro = cur.fetchone()

    # Obtener la lista de roles disponibles
    cur.execute("SELECT * FROM Rol")
    roles = cur.fetchall()
    cur.close()

    return render_template('editar_miembro.html', miembro=miembro, roles=roles, id_proyecto=id_proyecto)

@app.route('/proyecto/<int:id_proyecto>/miembro/<int:id_miembro>/eliminar', methods=['POST'])
@login_required
def eliminar_miembro(id_proyecto, id_miembro):
    cur = mysql.connection.cursor()
    try:
        # Eliminar registros dependientes en Informe_Cambio
        cur.execute("DELETE FROM Informe_Cambio WHERE id_solicitud_cambio IN (SELECT id_solicitud_cambios FROM Solicitud_Cambios WHERE id_miembro = %s)", (id_miembro,))
        mysql.connection.commit()

        # Eliminar registros dependientes en Solicitud_Cambios
        cur.execute("DELETE FROM Solicitud_Cambios WHERE id_miembro = %s", (id_miembro,))
        mysql.connection.commit()

        # Eliminar el miembro del proyecto
        cur.execute("DELETE FROM Miembro_Proyecto WHERE id_miembro = %s", (id_miembro,))
        mysql.connection.commit()

        flash('Miembro eliminado con éxito', 'success')
    except Exception as e:
        flash(f'Error al eliminar el miembro: {str(e)}', 'danger')
    finally:
        cur.close()

    return redirect(url_for('ver_miembros', id=id_proyecto))




@app.route('/proyecto/<int:id>/configuracion', methods=['GET'])
@login_required
def ver_configuracion(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id_version, version, tipo, fecha_subida, descripcion, ruta_archivo
        FROM Version_Configuracion
        WHERE id_proyecto = %s
        ORDER BY fecha_subida DESC
    """, (id,))
    versiones = cur.fetchall()
    cur.close()

    return render_template('ver_configuracion.html', versiones=versiones, id_proyecto=id)


@app.route('/proyecto/<int:id>/configuracion/subir', methods=['GET', 'POST'])
@login_required
def subir_version(id):
    if request.method == 'POST':
        archivo = request.files['archivo']
        descripcion = request.form['descripcion']
        tipo = request.form['tipo']  # Tipo de archivo (Documento, Código, etc.)
        if archivo and descripcion:
            # Guardar archivo
            ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(archivo.filename))
            archivo.save(ruta_archivo)

            # Insertar versión en la base de datos
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO Version_Configuracion (version, descripcion, ruta_archivo, tipo, fecha_subida, id_proyecto)
                VALUES (%s, %s, %s, %s, NOW(), %s)
            """, (archivo.filename, descripcion, ruta_archivo, tipo, id))
            mysql.connection.commit()
            cur.close()

            flash('Nueva versión subida con éxito', 'success')
            return redirect(url_for('ver_configuracion', id=id))
    return render_template('subir_version.html', id_proyecto=id)


import os
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
from werkzeug.utils import secure_filename

import difflib

def comparar_archivos(ruta_version_1, ruta_version_2):
    with open(ruta_version_1, 'r', encoding='utf-8', errors='ignore') as archivo_1, open(ruta_version_2, 'r', encoding='utf-8', errors='ignore') as archivo_2:
        contenido_1 = archivo_1.readlines()
        contenido_2 = archivo_2.readlines()

    d = difflib.HtmlDiff()
    diferencia = d.make_file(contenido_1, contenido_2)
    return diferencia


@app.route('/proyecto/<int:id>/configuracion/comparar', methods=['GET'])
@login_required
def comparar_versiones(id):
    id_version_1 = request.args.get('id_version_1')
    id_version_2 = request.args.get('id_version_2')

    # Obtener rutas de ambas versiones seleccionadas
    cur = mysql.connection.cursor()

    cur.execute("SELECT ruta_archivo FROM Version_Configuracion WHERE id_version = %s", (id_version_1,))
    ruta_version_1 = cur.fetchone()[0]

    cur.execute("SELECT ruta_archivo FROM Version_Configuracion WHERE id_version = %s", (id_version_2,))
    ruta_version_2 = cur.fetchone()[0]

    cur.close()

    # Comparar los archivos
    diferencias = comparar_archivos(ruta_version_1, ruta_version_2)

    # Renderizar el HTML con las diferencias
    return render_template('comparar_versiones.html', diferencias=diferencias, id_proyecto=id)


# Descargar versión
@app.route('/proyecto/version/descargar/<path:ruta>', methods=['GET'])
@login_required
def descargar_version(ruta):
    return send_from_directory(app.config['UPLOAD_FOLDER'], ruta, as_attachment=True)


@app.route('/proyecto/<int:id_proyecto>/configuracion/restaurar/<int:id_version>', methods=['POST'])
@login_required
def restaurar_version(id_proyecto, id_version):
    cur = mysql.connection.cursor()

    # Obtener la ruta de la versión que se va a restaurar
    cur.execute("SELECT ruta_archivo FROM Version_Configuracion WHERE id_version = %s", (id_version,))
    ruta_version = cur.fetchone()[0]

    # Aquí puedes implementar la lógica para copiar ese archivo a su ubicación original o marcarlo como la versión activa
    # Por ahora, simplemente mostramos un mensaje de éxito
    flash(f'Versión restaurada desde {ruta_version} con éxito', 'success')

    cur.close()
    return redirect(url_for('ver_configuracion', id=id_proyecto))





from flask import render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required
from fpdf import FPDF
import os
from werkzeug.utils import secure_filename

# Ruta para ver informes de un proyecto
@app.route('/proyecto/<int:id>/informes', methods=['GET'])
@login_required
def ver_informes(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT i.id_informe, p.nombre, i.periodo, i.fecha_generacion
        FROM Informe_Estado i
        JOIN Proyecto p ON i.id_proyecto = p.id_proyecto
        WHERE p.id_proyecto = %s
    """, (id,))
    informes = cur.fetchall()
    cur.close()

    # Verifica si se están recuperando informes
    print(informes)  # Esto debería mostrar los informes en la consola

    return render_template('informes.html', informes=informes, id_proyecto=id)



# Ruta para gestionar informes (ver y generar)
@app.route('/proyecto/informes', methods=['GET', 'POST'])
@login_required
def gestionar_informes():
    cur = mysql.connection.cursor()
    
    # Obtener los proyectos disponibles
    cur.execute("SELECT id_proyecto, nombre FROM Proyecto")
    proyectos = cur.fetchall()

    if request.method == 'POST':
        id_proyecto = request.form['proyecto']
        periodo = request.form['periodo']

        if not id_proyecto or not periodo:
            flash('Debe seleccionar un proyecto y un periodo.', 'danger')
            return redirect(url_for('gestionar_informes'))

        # Generar el informe (ejemplo de datos)
        avance_general = "El proyecto tiene un avance del 70%."
        problemas = "Se identificaron algunos retrasos en las entregas del módulo 3."

        # Guardar el informe en la base de datos
        cur.execute("""
            INSERT INTO Informe_Estado (id_proyecto, periodo, fecha_generacion, avance_general, problemas)
            VALUES (%s, %s, NOW(), %s, %s)
        """, (id_proyecto, periodo, avance_general, problemas))
        mysql.connection.commit()

        flash('Informe generado con éxito', 'success')
        return redirect(url_for('gestionar_informes'))
    
    # Obtener los informes para mostrarlos en la tabla
    cur.execute("""
        SELECT i.id_informe, p.nombre, i.periodo, i.fecha_generacion
        FROM Informe_Estado i
        JOIN Proyecto p ON i.id_proyecto = p.id_proyecto
    """)
    informes = cur.fetchall()

    # Asegúrate de imprimir lo que hay en 'informes'
    print("Informes:", informes)  # Esto imprimirá los informes en la consola del servidor

    cur.close()

    return render_template('informes.html', proyectos=proyectos, informes=informes)




# Ruta para ver un informe específico
@app.route('/proyecto/informe/<int:id_informe>', methods=['GET'])
@login_required
def ver_informe(id_informe):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT i.avance_general, i.problemas, p.nombre, i.periodo, i.fecha_generacion
        FROM Informe_Estado i
        JOIN Proyecto p ON i.id_proyecto = p.id_proyecto
        WHERE i.id_informe = %s
    """, (id_informe,))
    informe = cur.fetchone()

    cur.close()

    return render_template('ver_informe.html', informe=informe)


# Ruta para exportar el informe a PDF
@app.route('/proyecto/informe/<int:id_informe>/exportar', methods=['GET'])
@login_required
def exportar_informe_pdf(id_informe):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT i.avance_general, i.problemas, p.nombre, i.periodo, i.fecha_generacion
        FROM Informe_Estado i
        JOIN Proyecto p ON i.id_proyecto = p.id_proyecto
        WHERE i.id_informe = %s
    """, (id_informe,))
    informe = cur.fetchone()
    cur.close()

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, f"Informe de Estado - {informe[2]}", ln=True, align='C')

    pdf.set_font('Arial', '', 12)
    pdf.cell(200, 10, f"Periodo: {informe[3]}", ln=True)
    pdf.cell(200, 10, f"Fecha de Generación: {informe[4]}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, "Avance General:", ln=True)
    pdf.multi_cell(200, 10, informe[0])

    pdf.ln(10)
    pdf.cell(200, 10, "Problemas Identificados:", ln=True)
    pdf.multi_cell(200, 10, informe[1])

    response = make_response(pdf.output(dest='S'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'

    return response




# Ruta para mostrar los proyectos y el formulario para generar reportes
from flask_login import current_user

@app.route('/proyecto/reportes', methods=['GET', 'POST'])
@login_required
def gestionar_reportes():
    cur = mysql.connection.cursor()
    
    # Obtener los proyectos donde el usuario está asignado
    cur.execute("""
        SELECT p.id_proyecto, p.nombre 
        FROM Proyecto p
        JOIN Miembro_Proyecto mp ON p.id_proyecto = mp.id_proyecto
        WHERE mp.id_usuario = %s
    """, (current_user.id,))
    proyectos = cur.fetchall()

    if request.method == 'POST':
        id_proyecto = request.form['proyecto']
        periodo = request.form['periodo']

        if not id_proyecto or not periodo:
            flash('Debe seleccionar un proyecto y un periodo.', 'danger')
            return redirect(url_for('gestionar_reportes'))

        # Generar el informe (ejemplo de datos)
        avance_general = "El proyecto tiene un avance del 70%."
        problemas = "Se identificaron algunos retrasos en las entregas del módulo 3."

        # Guardar el informe en la base de datos
        cur.execute("""
            INSERT INTO Informe_Estado (id_proyecto, periodo, fecha_generacion, avance_general, problemas)
            VALUES (%s, %s, NOW(), %s, %s)
        """, (id_proyecto, periodo, avance_general, problemas))
        mysql.connection.commit()

        flash('Informe generado con éxito', 'success')
        return redirect(url_for('gestionar_reportes'))

    # Obtener los informes generados relacionados con los proyectos donde el usuario está asignado
    cur.execute("""
        SELECT i.id_informe, p.nombre, i.periodo, i.fecha_generacion 
        FROM Informe_Estado i
        JOIN Proyecto p ON i.id_proyecto = p.id_proyecto
        JOIN Miembro_Proyecto mp ON p.id_proyecto = mp.id_proyecto
        WHERE mp.id_usuario = %s
    """, (current_user.id,))
    
    informes = cur.fetchall()
    print("Informes recuperados:", informes)  # Agregar este print para ver los resultados
    cur.close()

    return render_template('reportes.html', proyectos=proyectos, informes=informes)



# Ruta para ver un reporte de progreso específico
@app.route('/proyecto/reporte/<int:id_reporte>', methods=['GET'])
@login_required
def ver_reporte(id_reporte):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT p.nombre, r.periodo, r.avance, r.actividades_completadas, r.problemas, r.fecha_generacion
        FROM Reporte_Progreso r
        JOIN Proyecto p ON r.id_proyecto = p.id_proyecto
        WHERE r.id_reporte = %s
    """, (id_reporte,))
    reporte = cur.fetchone()

    cur.close()

    return render_template('ver_reporte.html', reporte=reporte)


# Ruta para exportar un informe a PDF
@app.route('/proyecto/reporte/<int:id_reporte>/exportar', methods=['GET'])
@login_required
def exportar_reporte_pdf(id_reporte):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT p.nombre, r.periodo, r.avance, r.actividades_completadas, r.problemas, r.fecha_generacion
        FROM Reporte_Progreso r
        JOIN Proyecto p ON r.id_proyecto = p.id_proyecto
        WHERE r.id_reporte = %s
    """, (id_reporte,))
    reporte = cur.fetchone()
    cur.close()

    # Generar PDF
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, f"Informe de Progreso - {reporte[0]}", ln=True, align='C')

    pdf.set_font('Arial', '', 12)
    pdf.cell(200, 10, f"Periodo: {reporte[1]}", ln=True)
    pdf.cell(200, 10, f"Fecha de Generación: {reporte[5]}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, "Porcentaje de Avance:", ln=True)
    pdf.cell(200, 10, f"{reporte[2]}%", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, "Actividades Completadas:", ln=True)
    pdf.multi_cell(200, 10, reporte[3])

    pdf.ln(10)
    pdf.cell(200, 10, "Problemas Identificados:", ln=True)
    pdf.multi_cell(200, 10, reporte[4])

    response = make_response(pdf.output(dest='S'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_{id_reporte}.pdf'

    return response

# Ruta para generar un nuevo informe
@app.route('/informes/generar', methods=['POST'])
@login_required
def generar_informe():
    proyecto_id = request.form['proyecto']
    periodo = request.form['periodo']

    if not proyecto_id:
        flash('Debe seleccionar un proyecto', 'danger')
        return redirect(url_for('gestionar_informes'))

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO Informe_Estado (id_proyecto, periodo, fecha_generacion, avance_general, problemas)
        VALUES (%s, %s, NOW(), 'Avance del proyecto', 'Problemas detectados')
    """, (proyecto_id, periodo))
    mysql.connection.commit()
    cur.close()

    flash('Informe generado con éxito', 'success')
    return redirect(url_for('gestionar_informes'))







# Ruta para solicitar un cambio
@app.route('/proyecto/<int:id_proyecto>/solicitar_cambio', methods=['GET', 'POST'])
@login_required
def solicitar_cambio(id_proyecto):
    if request.method == 'POST':
        archivo = request.files['archivo']
        descripcion = request.form['descripcion']

        if archivo and descripcion:
            filename = secure_filename(archivo.filename)
            archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(archivo_path)

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO Solicitud_Cambio (id_proyecto, id_usuario, archivo, descripcion, estado)
                VALUES (%s, %s, %s, %s, 'Pendiente')
            """, (id_proyecto, current_user.id, archivo_path, descripcion))
            mysql.connection.commit()
            cur.close()

            flash('Solicitud de cambio enviada correctamente', 'success')
            return redirect(url_for('ver_solicitudes_cambio', id_proyecto=id_proyecto))
    
    return render_template('solicitar_cambio.html', id_proyecto=id_proyecto)

# Ruta para revisar las solicitudes de cambio
@app.route('/proyecto/<int:id_proyecto>/cambios', methods=['GET'])
@login_required
def ver_solicitudes_cambio(id_proyecto):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sc.id_cambio, sc.descripcion, sc.estado, sc.fecha_solicitud, u.nombre 
        FROM Solicitud_Cambio sc 
        JOIN Usuario u ON sc.id_usuario = u.id_usuario
        WHERE sc.id_proyecto = %s
    """, (id_proyecto,))
    solicitudes = cur.fetchall()
    cur.close()

    return render_template('ver_solicitudes_cambio.html', solicitudes=solicitudes, id_proyecto=id_proyecto)

@app.route('/proyecto/<int:id_proyecto>/cambio/<int:id_cambio>/revisar', methods=['POST'])
@login_required
def revisar_cambio(id_proyecto, id_cambio):
    accion = request.form['accion']  # Puede ser 'Aprobar' o 'Rechazar'
    
    # Validar que la acción sea correcta
    if accion not in ['Aprobar', 'Rechazar']:
        flash('Acción inválida', 'danger')
        return redirect(url_for('ver_solicitudes_cambio', id_proyecto=id_proyecto))

    # Mapear la acción a los estados correspondientes
    estado_final = 'Aprobado' if accion == 'Aprobar' else 'Rechazado'
    
    cur = mysql.connection.cursor()

    # Actualizar el estado de la solicitud
    cur.execute("UPDATE Solicitud_Cambio SET estado = %s WHERE id_cambio = %s", (estado_final, id_cambio))
    
    # Registrar la acción en el historial de cambios
    cur.execute("INSERT INTO Historial_Cambios (id_cambio, id_usuario, accion) VALUES (%s, %s, %s)", 
                (id_cambio, current_user.id, estado_final))

    mysql.connection.commit()
    cur.close()

    flash(f'El cambio ha sido {estado_final.lower()} con éxito.', 'success')
    return redirect(url_for('ver_solicitudes_cambio', id_proyecto=id_proyecto))



@app.route('/proyecto/<int:id_proyecto>/tarea/<int:id_tarea>/actualizar', methods=['POST'])
@login_required
def actualizar_estado_tarea(id_proyecto, id_tarea):
    nuevo_estado = request.form['estado']

    cur = mysql.connection.cursor()
    
    # Obtener el estado anterior
    cur.execute("SELECT estado FROM Tarea WHERE id_tarea = %s", (id_tarea,))
    estado_anterior = cur.fetchone()[0]
    
    # Actualizar el estado de la tarea
    cur.execute("UPDATE Tarea SET estado = %s WHERE id_tarea = %s", (nuevo_estado, id_tarea))
    
    # Insertar en el historial de cambios
    cur.execute("""
        INSERT INTO Historial_Tareas (id_tarea, estado_anterior, estado_nuevo, id_usuario)
        VALUES (%s, %s, %s, %s)
    """, (id_tarea, estado_anterior, nuevo_estado, current_user.id))
    
    mysql.connection.commit()
    cur.close()

    flash('El estado de la tarea ha sido actualizado y registrado en el historial.', 'success')
    return redirect(url_for('ver_flujo_tareas', id_proyecto=id_proyecto))


@app.route('/proyecto/<int:id_proyecto>/flujotareas', methods=['GET'])
@login_required
def ver_flujo_tareas(id_proyecto):
    cur = mysql.connection.cursor()

    # Obtener todas las tareas del proyecto con su estado
    cur.execute("""
        SELECT t.id_tarea, t.nombre, t.descripcion, t.fecha_inicio, t.fecha_fin, t.estado, u.nombre AS responsable
        FROM Tarea t
        JOIN Usuario u ON t.id_asignado_a = u.id_usuario
        WHERE t.id_proyecto = %s
    """, (id_proyecto,))
    tareas = cur.fetchall()
    cur.close()

    return render_template('flujo_tareas.html', tareas=tareas, id_proyecto=id_proyecto)


@app.route('/proyecto/<int:id_proyecto>/tarea/<int:id_tarea>/historial', methods=['GET'])
@login_required
def ver_historial_tarea(id_proyecto, id_tarea):
    cur = mysql.connection.cursor()

    # Consulta del historial de la tarea
    cur.execute("""
        SELECT ht.fecha, ht.estado_anterior, ht.estado_nuevo, u.nombre
        FROM Historial_Tareas ht
        JOIN Usuario u ON ht.id_usuario = u.id_usuario
        WHERE ht.id_tarea = %s
        ORDER BY ht.fecha DESC
    """, (id_tarea,))
    historial = cur.fetchall()

    cur.close()

    return render_template('historial_tarea.html', historial=historial, id_proyecto=id_proyecto)




@app.route('/proyecto/<int:id_proyecto>/reporte_analiticas', methods=['GET'])
@login_required
def reporte_analiticas(id_proyecto):
    cur = mysql.connection.cursor()

    # Obtener el historial de tareas para el proyecto
    cur.execute("""
        SELECT t.nombre, h.estado_anterior, h.estado_nuevo, h.fecha, u.nombre
        FROM Historial_Tareas h
        JOIN Tarea t ON h.id_tarea = t.id_tarea
        JOIN Usuario u ON h.id_usuario = u.id_usuario
        WHERE t.id_proyecto = %s
        ORDER BY h.fecha
    """, (id_proyecto,))
    transiciones = cur.fetchall()
    cur.close()

    # Generar un gráfico de ejemplo para mostrar la transición de estados
    estados = ["Pendiente", "En progreso", "Completada"]
    conteo_transiciones = {estado: 0 for estado in estados}

    for transicion in transiciones:
        if transicion[2] in conteo_transiciones:
            conteo_transiciones[transicion[2]] += 1

    # Crear gráfico de barras
    plt.bar(conteo_transiciones.keys(), conteo_transiciones.values())
    plt.xlabel('Estados')
    plt.ylabel('Cantidad de Transiciones')
    plt.title('Transiciones de Estado de las Tareas')

    # Convertir gráfico a imagen para incrustar en HTML
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_url = base64.b64encode(img.getvalue()).decode()

    return render_template('reporte_analiticas.html', img_url=img_url, transiciones=transiciones, id_proyecto=id_proyecto)

@app.route('/proyecto/<int:id_proyecto>/reporte_analiticas/pdf', methods=['GET'])
@login_required
def exportar_reporteanaliticas_pdf(id_proyecto):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT t.nombre, h.estado_anterior, h.estado_nuevo, h.fecha, u.nombre
        FROM Historial_Tareas h
        JOIN Tarea t ON h.id_tarea = t.id_tarea
        JOIN Usuario u ON h.id_usuario = u.id_usuario
        WHERE t.id_proyecto = %s
        ORDER BY h.fecha
    """, (id_proyecto,))
    transiciones = cur.fetchall()
    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Reporte de Analíticas - Proyecto {}".format(id_proyecto), ln=True, align="C")

    for transicion in transiciones:
        pdf.cell(200, 10, txt="Tarea: {}, Estado Anterior: {}, Estado Nuevo: {}, Fecha: {}, Responsable: {}".format(
            transicion[0], transicion[1], transicion[2], transicion[3], transicion[4]), ln=True)

    response = make_response(pdf.output(dest='S'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_analiticas_{}.pdf'.format(id_proyecto)
    
    return response


import pandas as pd

@app.route('/proyecto/<int:id_proyecto>/reporte_analiticas/excel', methods=['GET'])
@login_required
def exportar_reporte_excel(id_proyecto):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT t.nombre, h.estado_anterior, h.estado_nuevo, h.fecha, u.nombre
        FROM Historial_Tareas h
        JOIN Tarea t ON h.id_tarea = t.id_tarea
        JOIN Usuario u ON h.id_usuario = u.id_usuario
        WHERE t.id_proyecto = %s
        ORDER BY h.fecha
    """, (id_proyecto,))
    transiciones = cur.fetchall()
    cur.close()

    df = pd.DataFrame(transiciones, columns=["Nombre de la Tarea", "Estado Anterior", "Estado Nuevo", "Fecha de Transición", "Responsable"])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte de Analiticas')
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_analiticas_{}.xlsx'.format(id_proyecto)
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return response




from flask import render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        # Recoger los datos del formulario
        nombre = request.form['nombre']
        correo = request.form['correo']
        notificaciones = request.form['notificaciones']
        imagen_perfil = request.files['imagen_perfil']

        # Validar campos obligatorios
        if not nombre or not correo:
            flash('Debe completar los campos obligatorios.', 'danger')
            return redirect(url_for('editar_perfil'))

        # Procesar la imagen de perfil si se sube una nueva
        if imagen_perfil:
            ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(imagen_perfil.filename))
            imagen_perfil.save(ruta_imagen)

            # Actualizar la imagen de perfil en la base de datos
            cur.execute("UPDATE Usuario SET imagen_perfil = %s WHERE id_usuario = %s", (ruta_imagen, current_user.id))

        # Actualizar los datos del perfil en la base de datos
        cur.execute("""
            UPDATE Usuario
            SET nombre = %s, correo = %s, notificaciones = %s
            WHERE id_usuario = %s
        """, (nombre, correo, notificaciones, current_user.id))
        
        mysql.connection.commit()
        cur.close()

        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('editar_perfil'))

    # Obtener los datos actuales del usuario
    cur.execute("SELECT nombre, correo, notificaciones, imagen_perfil FROM Usuario WHERE id_usuario = %s", (current_user.id,))
    usuario = cur.fetchone()
    cur.close()

    return render_template('editar_perfil.html', usuario=usuario)



# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
