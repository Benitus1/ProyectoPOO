"""Interfaz web (HTML) para EcoTech Solutions.

Ejecutar:
    python webapp.py
Luego abrir http://127.0.0.1:5000 en el navegador.
"""
import os
import sys
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash,
)

# Asegurar imports del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from DAO.empleado_dao import EmpleadoDAO
from DAO.departamento_dao import DepartamentoDAO
from DAO.proyecto_dao import ProyectoDAO
from DAO.registro_tiempo_dao import RegistroTiempoDAO
from DAO.proyecto_asignacion_dao import ProyectoAsignacionDAO
from DAO.usuario_dao import UsuarioDAO
from SEGURIDAD.autenticacion import AutenticacionService, hash_password
from SEGURIDAD.validaciones import (
    sanitizar_texto, validar_email, validar_telefono, validar_nombre,
    validar_salario, validar_fecha, validar_ciudad, validar_codigo_moneda,
    validar_no_vacio, validar_username, validar_password, validar_rol,
)
from SERVICIOS.clima_service import ClimaService
from SERVICIOS.indicadores_service import IndicadoresService
from DTO.empleado_dto import EmpleadoDTO
from DTO.departamento_dto import DepartamentoDTO
from DTO.proyecto_dto import ProyectoDTO
from DTO.registro_tiempo_dto import RegistroTiempoDTO
from DTO.usuario_dto import UsuarioDTO

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ecotech-dev-secret-change-me")

# Instancias
empleado_dao = EmpleadoDAO()
departamento_dao = DepartamentoDAO()
proyecto_dao = ProyectoDAO()
registro_dao = RegistroTiempoDAO()
asignacion_dao = ProyectoAsignacionDAO()
usuario_dao = UsuarioDAO()
auth_service = AutenticacionService()
clima_service = ClimaService()
indicadores_service = IndicadoresService()


def usuario_actual():
    uid = session.get("usuario_id")
    if not uid:
        return None
    try:
        return usuario_dao.buscar_por_id(uid)
    except Exception:
        return None


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_id"):
            flash("Debe iniciar sesión.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = usuario_actual()
        if u is None or u.rol != "Administrador":
            flash("Acceso restringido a administradores.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


def tiene_permiso(modulo):
    u = usuario_actual()
    if u is None:
        return False
    return auth_service.tiene_permiso(u, modulo)


@app.context_processor
def inject_user():
    return {"current_user": usuario_actual()}


# ---------------- AUTH ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        u = auth_service.login(username, password)
        if u is not None:
            session["usuario_id"] = u.id_usuario
            flash(f"Bienvenido/a, {u.username} ({u.rol}).", "success")
            return redirect(url_for("dashboard"))
        flash("Credenciales inválidas.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


@app.route("/")
def index():
    if session.get("usuario_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------------- EMPLEADOS ----------------
@app.route("/empleados", methods=["GET", "POST"])
@login_required
def empleados():
    if request.method == "POST":
        if not tiene_permiso("empleados"):
            flash("Sin permisos para esta acción.", "danger")
            return redirect(url_for("empleados"))
        action = request.form.get("action")
        if action == "add":
            nombre = request.form.get("nombre", "").strip()
            email = request.form.get("email", "").strip()
            telefono = request.form.get("telefono", "").strip()
            salario_str = request.form.get("salario", "").strip()
            rol = request.form.get("rol", "Empleado").strip() or "Empleado"
            depto_str = request.form.get("departamento_id", "").strip()
            ok, msg = validar_nombre(nombre)
            if not ok:
                flash(f"Nombre: {msg}", "danger"); return redirect(url_for("empleados"))
            ok, msg = validar_email(email)
            if not ok:
                flash(f"Email: {msg}", "danger"); return redirect(url_for("empleados"))
            ok, msg = validar_telefono(telefono)
            if not ok:
                flash(f"Teléfono: {msg}", "danger"); return redirect(url_for("empleados"))
            try:
                salario = float(salario_str)
            except ValueError:
                flash("Salario inválido.", "danger"); return redirect(url_for("empleados"))
            ok, msg = validar_salario(salario)
            if not ok:
                flash(f"Salario: {msg}", "danger"); return redirect(url_for("empleados"))
            nombre = sanitizar_texto(nombre, 100)
            email = sanitizar_texto(email, 100)
            telefono = sanitizar_texto(telefono, 20)
            rol = sanitizar_texto(rol, 50)
            dto = EmpleadoDTO(nombre, email, telefono, salario, rol)
            if depto_str:
                try:
                    dto.departamento_id = int(depto_str)
                except ValueError:
                    dto.departamento_id = None
            else:
                dto.departamento_id = None
            try:
                empleado_dao.guardar(dto)
                flash("Empleado registrado.", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("empleados"))
        if action == "update":
            try:
                id_emp = int(request.form.get("id_empleado"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("empleados"))
            emp = empleado_dao.buscar_por_id(id_emp)
            if not emp:
                flash("Empleado no encontrado.", "danger"); return redirect(url_for("empleados"))
            nom = request.form.get("nombre", "").strip()
            em = request.form.get("email", "").strip()
            tel = request.form.get("telefono", "").strip()
            sal_str = request.form.get("salario", "").strip()
            rol = request.form.get("rol", "").strip()
            depto_str = request.form.get("departamento_id", "").strip()
            if nom:
                ok, msg = validar_nombre(nom)
                if not ok:
                    flash(f"Nombre: {msg}", "danger"); return redirect(url_for("empleados"))
                emp.nombre = sanitizar_texto(nom, 100)
            if em:
                ok, msg = validar_email(em)
                if not ok:
                    flash(f"Email: {msg}", "danger"); return redirect(url_for("empleados"))
                emp.email = sanitizar_texto(em, 100)
            if tel:
                ok, msg = validar_telefono(tel)
                if not ok:
                    flash(f"Teléfono: {msg}", "danger"); return redirect(url_for("empleados"))
                emp.telefono = sanitizar_texto(tel, 20)
            if sal_str:
                try:
                    sal = float(sal_str)
                    ok, msg = validar_salario(sal)
                    if not ok:
                        flash(f"Salario: {msg}", "danger"); return redirect(url_for("empleados"))
                    emp.salario = sal
                except ValueError:
                    flash("Salario inválido.", "danger"); return redirect(url_for("empleados"))
            if rol:
                emp.rol = sanitizar_texto(rol, 50)
            if depto_str == "":
                emp.departamento_id = None
            else:
                try:
                    emp.departamento_id = int(depto_str)
                except ValueError:
                    pass
            try:
                if empleado_dao.actualizar(emp):
                    flash("Empleado actualizado.", "success")
                else:
                    flash("No se realizaron cambios.", "info")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("empleados"))
        if action == "delete":
            try:
                id_emp = int(request.form.get("id_empleado"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("empleados"))
            try:
                if empleado_dao.eliminar(id_emp):
                    flash("Empleado eliminado.", "success")
                else:
                    flash("No se pudo eliminar.", "warning")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("empleados"))

    try:
        lista = empleado_dao.listar()
    except Exception as e:
        lista = []; flash(f"Error al listar: {e}", "danger")
    try:
        departamentos = departamento_dao.listar()
    except Exception:
        departamentos = []
    return render_template("empleados.html", empleados=lista, departamentos=departamentos)


# ---------------- DEPARTAMENTOS ----------------
@app.route("/departamentos", methods=["GET", "POST"])
@login_required
def departamentos():
    if request.method == "POST":
        if not tiene_permiso("departamentos"):
            flash("Sin permisos.", "danger"); return redirect(url_for("departamentos"))
        action = request.form.get("action")
        if action == "add":
            nombre = request.form.get("nombre", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            ger_str = request.form.get("gerente_id", "").strip()
            ok, msg = validar_no_vacio(nombre, "nombre")
            if not ok:
                flash(f"Nombre: {msg}", "danger"); return redirect(url_for("departamentos"))
            nombre = sanitizar_texto(nombre, 100)
            descripcion = sanitizar_texto(descripcion, 255)
            gerente_id = None
            if ger_str:
                try:
                    cand = int(ger_str)
                    if departamento_dao is not None and True:
                        gerente_id = cand
                except ValueError:
                    gerente_id = None
            dto = DepartamentoDTO(nombre, descripcion, None, gerente_id)
            try:
                departamento_dao.guardar(dto)
                flash("Departamento registrado.", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("departamentos"))
        if action == "update":
            try:
                id_dep = int(request.form.get("id_departamento"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("departamentos"))
            dep = departamento_dao.buscar_por_id(id_dep)
            if not dep:
                flash("Departamento no encontrado.", "danger"); return redirect(url_for("departamentos"))
            nom = request.form.get("nombre", "").strip()
            desc = request.form.get("descripcion", "").strip()
            ger_str = request.form.get("gerente_id", "").strip()
            if nom:
                dep.nombre = sanitizar_texto(nom, 100)
            if desc:
                dep.descripcion = sanitizar_texto(desc, 255)
            if ger_str == "":
                dep.gerente_id = None
            else:
                try:
                    dep.gerente_id = int(ger_str)
                except ValueError:
                    pass
            try:
                if departamento_dao.actualizar(dep):
                    flash("Departamento actualizado.", "success")
                else:
                    flash("No se realizaron cambios.", "info")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("departamentos"))
        if action == "delete":
            try:
                id_dep = int(request.form.get("id_departamento"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("departamentos"))
            try:
                if departamento_dao.eliminar(id_dep):
                    flash("Departamento eliminado.", "success")
                else:
                    flash("No se pudo eliminar.", "warning")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("departamentos"))
        if action == "assign":
            try:
                id_emp = int(request.form.get("id_empleado"))
                id_dep = int(request.form.get("id_departamento"))
            except (TypeError, ValueError):
                flash("IDs inválidos.", "danger"); return redirect(url_for("departamentos"))
            if departamento_dao.asignar_empleado(id_emp, id_dep):
                flash("Empleado asignado.", "success")
            else:
                flash("No se pudo asignar.", "warning")
            return redirect(url_for("departamentos"))
        if action == "unassign":
            try:
                id_emp = int(request.form.get("id_empleado"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("departamentos"))
            if departamento_dao.quitar_empleado(id_emp):
                flash("Empleado removido.", "success")
            else:
                flash("No se pudo remover.", "warning")
            return redirect(url_for("departamentos"))

    try:
        lista = departamento_dao.listar()
    except Exception as e:
        lista = []; flash(f"Error: {e}", "danger")
    try:
        empleados = empleado_dao.listar()
    except Exception:
        empleados = []
    return render_template("departamentos.html", departamentos=lista, empleados=empleados)


# ---------------- PROYECTOS ----------------
@app.route("/proyectos", methods=["GET", "POST"])
@login_required
def proyectos():
    if request.method == "POST":
        if not tiene_permiso("proyectos"):
            flash("Sin permisos.", "danger"); return redirect(url_for("proyectos"))
        action = request.form.get("action")
        if action == "add":
            nombre = request.form.get("nombre", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            fecha_inicio = request.form.get("fecha_inicio", "").strip()
            ok, msg = validar_no_vacio(nombre, "nombre")
            if not ok:
                flash(f"Nombre: {msg}", "danger"); return redirect(url_for("proyectos"))
            ok, msg = validar_no_vacio(descripcion, "descripción")
            if not ok:
                flash(f"Descripción: {msg}", "danger"); return redirect(url_for("proyectos"))
            ok, msg = validar_fecha(fecha_inicio)
            if not ok:
                flash(f"Fecha: {msg}", "danger"); return redirect(url_for("proyectos"))
            nombre = sanitizar_texto(nombre, 100)
            descripcion = sanitizar_texto(descripcion, 255)
            dto = ProyectoDTO(nombre, descripcion, fecha_inicio)
            try:
                proyecto_dao.guardar(dto)
                flash("Proyecto registrado.", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("proyectos"))
        if action == "update":
            try:
                id_proy = int(request.form.get("id_proyecto"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("proyectos"))
            proy = proyecto_dao.buscar_por_id(id_proy)
            if not proy:
                flash("Proyecto no encontrado.", "danger"); return redirect(url_for("proyectos"))
            nom = request.form.get("nombre", "").strip()
            desc = request.form.get("descripcion", "").strip()
            fec = request.form.get("fecha_inicio", "").strip()
            if nom:
                proy.nombre = sanitizar_texto(nom, 100)
            if desc:
                proy.descripcion = sanitizar_texto(desc, 255)
            if fec:
                try:
                    datetime.strptime(fec, "%Y-%m-%d")
                    proy.fecha_inicio = fec
                except ValueError:
                    flash("Fecha inválida. Se mantiene.", "warning")
            try:
                if proyecto_dao.actualizar(proy):
                    flash("Proyecto actualizado.", "success")
                else:
                    flash("No se realizaron cambios.", "info")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("proyectos"))
        if action == "delete":
            try:
                id_proy = int(request.form.get("id_proyecto"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("proyectos"))
            try:
                if proyecto_dao.eliminar(id_proy):
                    flash("Proyecto eliminado.", "success")
                else:
                    flash("No se pudo eliminar.", "warning")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("proyectos"))

    try:
        lista = proyecto_dao.listar()
    except Exception as e:
        lista = []; flash(f"Error: {e}", "danger")
    return render_template("proyectos.html", proyectos=lista)


# ---------------- REGISTROS ----------------
@app.route("/registros", methods=["GET", "POST"])
@login_required
def registros():
    if request.method == "POST":
        if not tiene_permiso("registros"):
            flash("Sin permisos.", "danger"); return redirect(url_for("registros"))
        action = request.form.get("action")
        if action == "add":
            try:
                id_emp = int(request.form.get("id_empleado"))
                id_proy = int(request.form.get("id_proyecto"))
                horas = float(request.form.get("horas"))
            except (TypeError, ValueError):
                flash("Datos numéricos inválidos.", "danger"); return redirect(url_for("registros"))
            if horas <= 0:
                flash("Las horas deben ser > 0.", "danger"); return redirect(url_for("registros"))
            if not empleado_dao.buscar_por_id(id_emp):
                flash("Empleado no existe.", "danger"); return redirect(url_for("registros"))
            if not proyecto_dao.buscar_por_id(id_proy):
                flash("Proyecto no existe.", "danger"); return redirect(url_for("registros"))
            tarea = request.form.get("tarea", "").strip()
            fecha = request.form.get("fecha", "").strip()
            ok, msg = validar_no_vacio(tarea, "descripción de la tarea")
            if not ok:
                flash(f"Tarea: {msg}", "danger"); return redirect(url_for("registros"))
            ok, msg = validar_fecha(fecha)
            if not ok:
                flash(f"Fecha: {msg}", "danger"); return redirect(url_for("registros"))
            tarea = sanitizar_texto(tarea, 255)
            dto = RegistroTiempoDTO(horas, tarea, fecha, id_emp, id_proy)
            try:
                registro_dao.guardar(dto)
                flash("Horas registradas.", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("registros"))
        if action == "update":
            try:
                id_reg = int(request.form.get("id_registro"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("registros"))
            reg = registro_dao.buscar_por_id(id_reg)
            if not reg:
                flash("Registro no encontrado.", "danger"); return redirect(url_for("registros"))
            h_str = request.form.get("horas", "").strip()
            tar = request.form.get("tarea", "").strip()
            fec = request.form.get("fecha", "").strip()
            if h_str:
                try:
                    h = float(h_str)
                    if h <= 0:
                        flash("Las horas deben ser > 0. Se mantiene.", "warning")
                    else:
                        reg.horas = h
                except ValueError:
                    flash("Horas inválidas. Se mantiene.", "warning")
            if tar:
                reg.descripcion_tarea = sanitizar_texto(tar, 255)
            if fec:
                try:
                    datetime.strptime(fec, "%Y-%m-%d")
                    reg.fecha = fec
                except ValueError:
                    flash("Fecha inválida. Se mantiene.", "warning")
            try:
                if registro_dao.actualizar(reg):
                    flash("Registro actualizado.", "success")
                else:
                    flash("No se realizaron cambios.", "info")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("registros"))
        if action == "delete":
            try:
                id_reg = int(request.form.get("id_registro"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("registros"))
            try:
                if registro_dao.eliminar(id_reg):
                    flash("Registro eliminado.", "success")
                else:
                    flash("No se pudo eliminar.", "warning")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("registros"))

    try:
        lista = registro_dao.listar()
    except Exception as e:
        lista = []; flash(f"Error: {e}", "danger")
    try:
        empleados = empleado_dao.listar()
        proyectos = proyecto_dao.listar()
    except Exception:
        empleados = []; proyectos = []
    return render_template("registros.html", registros=lista, empleados=empleados, proyectos=proyectos)


# ---------------- ASIGNACIONES ----------------
@app.route("/asignaciones", methods=["GET", "POST"])
@login_required
def asignaciones():
    if request.method == "POST":
        if not tiene_permiso("asignaciones"):
            flash("Sin permisos.", "danger"); return redirect(url_for("asignaciones"))
        action = request.form.get("action")
        if action == "assign":
            try:
                id_proy = int(request.form.get("id_proyecto"))
                id_emp = int(request.form.get("id_empleado"))
            except (TypeError, ValueError):
                flash("IDs inválidos.", "danger"); return redirect(url_for("asignaciones"))
            fecha = request.form.get("fecha", "").strip()
            if not fecha:
                fecha = datetime.now().strftime("%Y-%m-%d")
            ok, msg = validar_fecha(fecha)
            if not ok:
                flash(f"Fecha: {msg}", "danger"); return redirect(url_for("asignaciones"))
            proy = proyecto_dao.buscar_por_id(id_proy)
            emp = empleado_dao.buscar_por_id(id_emp)
            if not proy or not emp:
                flash("Proyecto o empleado no existe.", "danger"); return redirect(url_for("asignaciones"))
            if asignacion_dao.asignar_empleado(id_proy, id_emp, fecha):
                flash("Empleado asignado al proyecto.", "success")
            else:
                flash("Ya asignado o no se pudo asignar.", "warning")
            return redirect(url_for("asignaciones"))
        if action == "unassign":
            try:
                id_proy = int(request.form.get("id_proyecto"))
                id_emp = int(request.form.get("id_empleado"))
            except (TypeError, ValueError):
                flash("IDs inválidos.", "danger"); return redirect(url_for("asignaciones"))
            if asignacion_dao.desasignar_empleado(id_proy, id_emp):
                flash("Empleado desasignado.", "success")
            else:
                flash("No se pudo desasignar.", "warning")
            return redirect(url_for("asignaciones"))

    try:
        proyectos = proyecto_dao.listar()
    except Exception as e:
        proyectos = []; flash(f"Error: {e}", "danger")
    # equipos por proyecto
    equipos = {}
    for p in proyectos:
        try:
            equipos[p.id_proyecto] = asignacion_dao.listar_empleados_por_proyecto(p.id_proyecto)
        except Exception:
            equipos[p.id_proyecto] = []
    try:
        empleados = empleado_dao.listar()
    except Exception:
        empleados = []
    return render_template("asignaciones.html", proyectos=proyectos, equipos=equipos, empleados=empleados)


# ---------------- API: DEPARTAMENTOS ----------------
@app.route("/api/asignar-departamento", methods=["POST"])
@login_required
def api_asignar_departamento():
    if not tiene_permiso("departamentos"):
        return {"ok": False, "msg": "Sin permisos"}, 403
    data = request.get_json(silent=True) or {}
    try:
        emp_id = int(data.get("empleado_id"))
    except (TypeError, ValueError):
        return {"ok": False, "msg": "empleado_id inválido"}, 400
    depto_raw = data.get("departamento_id")
    depto_id = None
    if depto_raw not in (None, "", "null"):
        try:
            depto_id = int(depto_raw)
        except (TypeError, ValueError):
            return {"ok": False, "msg": "departamento_id inválido"}, 400
    emp = empleado_dao.buscar_por_id(emp_id)
    if not emp:
        return {"ok": False, "msg": "Empleado no encontrado"}, 404
    if depto_id is not None:
        dep = departamento_dao.buscar_por_id(depto_id)
        if not dep:
            return {"ok": False, "msg": "Departamento no encontrado"}, 404
    try:
        if depto_id is None:
            ok = departamento_dao.quitar_empleado(emp_id)
        else:
            ok = departamento_dao.asignar_empleado(emp_id, depto_id)
        if ok:
            return {"ok": True}
        return {"ok": False, "msg": "No se pudo actualizar"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}, 500


# ---------------- AJUSTES ----------------
@app.route("/ajustes")
@login_required
def ajustes():
    return render_template("ajustes.html")


@app.route("/tablero")
@login_required
def tablero():
    try:
        departamentos = departamento_dao.listar()
    except Exception as e:
        departamentos = []; flash(f"Error: {e}", "danger")
    try:
        empleados = empleado_dao.listar()
    except Exception:
        empleados = []
    grupos = {None: []}
    for d in departamentos:
        grupos[d.id_departamento] = []
    for e in empleados:
        grupos.setdefault(e.departamento_id, []).append(e)
    sin_depto = [e for e in empleados if e.departamento_id is None]
    grupos[None] = sin_depto

    # proyectos y equipos
    try:
        proyectos = proyecto_dao.listar()
    except Exception:
        proyectos = []
    equipos_proj = {}
    for p in proyectos:
        try:
            equipos_proj[p.id_proyecto] = asignacion_dao.listar_empleados_por_proyecto(p.id_proyecto)
        except Exception:
            equipos_proj[p.id_proyecto] = []
    return render_template("tablero.html", departamentos=departamentos, empleados=empleados,
                           grupos=grupos, proyectos=proyectos, equipos_proj=equipos_proj)


@app.route("/api/asignar-proyecto", methods=["POST"])
@login_required
def api_asignar_proyecto():
    if not tiene_permiso("asignaciones"):
        return {"ok": False, "msg": "Sin permisos"}, 403
    data = request.get_json(silent=True) or {}
    try:
        emp_id = int(data.get("empleado_id"))
        proy_id = int(data.get("proyecto_id"))
    except (TypeError, ValueError):
        return {"ok": False, "msg": "IDs inválidos"}, 400
    fecha = data.get("fecha")
    if not fecha:
        from datetime import date
        fecha = date.today().strftime("%Y-%m-%d")
    emp = empleado_dao.buscar_por_id(emp_id)
    proy = proyecto_dao.buscar_por_id(proy_id)
    if not emp or not proy:
        return {"ok": False, "msg": "Empleado o proyecto no existe"}, 404
    try:
        ok = asignacion_dao.asignar_empleado(proy_id, emp_id, fecha)
        if ok:
            return {"ok": True}
        return {"ok": False, "msg": "Ya asignado o no se pudo asignar"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}, 500


@app.route("/api/desasignar-proyecto", methods=["POST"])
@login_required
def api_desasignar_proyecto():
    if not tiene_permiso("asignaciones"):
        return {"ok": False, "msg": "Sin permisos"}, 403
    data = request.get_json(silent=True) or {}
    try:
        emp_id = int(data.get("empleado_id"))
        proy_id = int(data.get("proyecto_id"))
    except (TypeError, ValueError):
        return {"ok": False, "msg": "IDs inválidos"}, 400
    try:
        ok = asignacion_dao.desasignar_empleado(proy_id, emp_id)
        if ok:
            return {"ok": True}
        return {"ok": False, "msg": "No se pudo desasignar"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}, 500
@app.route("/servicios", methods=["GET", "POST"])
@login_required
def servicios():
    if not tiene_permiso("api"):
        flash("Sin permisos para servicios externos.", "danger")
        return redirect(url_for("dashboard"))
    clima = None
    indicadores = None
    conversion = None
    error = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "clima":
            ciudad = request.form.get("ciudad", "").strip()
            ok, msg = validar_ciudad(ciudad)
            if not ok:
                flash(f"Ciudad: {msg}", "danger")
            else:
                try:
                    clima = clima_service.obtener_clima(ciudad)
                except Exception as e:
                    flash(f"Error clima: {e}", "danger")
        elif action == "indicadores":
            try:
                indicadores = indicadores_service.listar_indicadores()
                codigo = request.form.get("codigo", "").strip().lower()
                if codigo:
                    try:
                        detalle = indicadores_service.obtener_indicador(codigo)
                        indicadores = {"_detalle": detalle}
                    except Exception as e:
                        flash(f"Error indicador: {e}", "danger")
            except Exception as e:
                flash(f"Error indicadores: {e}", "danger")
        elif action == "convertir":
            try:
                monto = float(request.form.get("monto"))
                origen = request.form.get("origen", "").strip().upper()
                destino = request.form.get("destino", "").strip().upper()
                ok, msg = validar_codigo_moneda(origen)
                if not ok:
                    flash(f"Origen: {msg}", "danger")
                else:
                    ok, msg = validar_codigo_moneda(destino)
                    if not ok:
                        flash(f"Destino: {msg}", "danger")
                    else:
                        resultado, info = indicadores_service.convertir(monto, origen, destino)
                        conversion = (monto, origen, resultado, destino, info)
            except ValueError:
                flash("Monto inválido.", "danger")
            except Exception as e:
                flash(f"Error conversión: {e}", "danger")
    return render_template("servicios.html", clima=clima, indicadores=indicadores, conversion=conversion)


# ---------------- USUARIOS (ADMIN) ----------------
@app.route("/usuarios", methods=["GET", "POST"])
@login_required
@admin_required
def usuarios():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            rol = request.form.get("rol", "Empleado").strip() or "Empleado"
            emp_str = request.form.get("empleado_id", "").strip()
            empleado_id = None
            if emp_str:
                try:
                    empleado_id = int(emp_str)
                except ValueError:
                    empleado_id = None
            try:
                nuevo = auth_service.registrar_usuario(username, password, rol, empleado_id)
                flash(f"Usuario '{nuevo.username}' creado.", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("usuarios"))
        if action == "change_password":
            username = request.form.get("username", "").strip()
            actual = request.form.get("actual", "")
            nuevo = request.form.get("nuevo", "")
            ok, msg = auth_service.cambiar_password(username, actual, nuevo)
            flash(msg, "success" if ok else "danger")
            return redirect(url_for("usuarios"))
        if action == "delete":
            try:
                id_usr = int(request.form.get("id_usuario"))
            except (TypeError, ValueError):
                flash("ID inválido.", "danger"); return redirect(url_for("usuarios"))
            u = usuario_actual()
            if u is not None and id_usr == u.id_usuario:
                flash("No puede eliminar su propio usuario.", "danger"); return redirect(url_for("usuarios"))
            if usuario_dao.eliminar(id_usr):
                flash("Usuario eliminado.", "success")
            else:
                flash("No se pudo eliminar.", "warning")
            return redirect(url_for("usuarios"))

    try:
        lista = usuario_dao.listar()
    except Exception as e:
        lista = []; flash(f"Error: {e}", "danger")
    try:
        empleados = empleado_dao.listar()
    except Exception:
        empleados = []
    return render_template("usuarios.html", usuarios=lista, empleados=empleados)


# ---------------- RESET DB (ADMIN) ----------------
@app.route("/reset", methods=["POST"])
@login_required
@admin_required
def reset():
    try:
        reset_database()
        flash("Base de datos restaurada a estado base.", "success")
    except Exception as e:
        flash(f"Error al restaurar: {e}", "danger")
    return redirect(url_for("dashboard"))


def reset_database():
    from DAO.conexion import Conexion
    import os as _os
    conn_obj = Conexion()
    if conn_obj.backend == "sqlite":
        db_path = _os.path.join(BASE_DIR, "ecotech.db")
        if _os.path.exists(db_path):
            _os.remove(db_path)
        # reinicializar
        c = conn_obj.conectar()
        c.close()
        return
    # MySQL
    import pymysql
    config = conn_obj.config.copy()
    db_name = config.pop("database")
    sql_file = _os.path.join(BASE_DIR, "BASE", "ecotech.sql")
    if not _os.path.exists(sql_file):
        raise FileNotFoundError(f"No se encontró {sql_file}")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_script = f.read()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
    cursor.execute(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci")
    cursor.execute(f"USE {db_name}")
    for statement in sql_script.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--") and statement.upper() not in ["CREATE DATABASE", "USE"]:
            try:
                cursor.execute(statement)
            except Exception:
                pass
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    # Crear admin por defecto (instancia ya lo hace)
    print("EcoTech Web iniciando en http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
