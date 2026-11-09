# EcoTech Solutions — Sistema de Gestión (Unidad 3)

Proyecto en Python para la asignatura **Programación Orientada a Objeto Seguro (TI3021)**, correspondiente a la Evaluación Formativa de la Unidad 3: **Consumo de Servicios Externos y Seguridad en Python**.

EcoTech Solutions es una aplicación de consola y web para gestionar empleados, departamentos, proyectos, asignaciones y bitácora de horas, integrando **APIs externas** (clima, indicadores económicos y conversión de moneda) con un módulo de **autenticación y validación de entradas**.

---

## ✨ Características principales

### Gestión interna
- CRUD de **empleados, departamentos, proyectos** y **registros de tiempo**.
- **Asignación** de empleados a departamentos y a proyectos.
- **Bitácora de horas** por proyecto.
- **Restauración** de la base de datos a su estado base.

### Consumo de servicios externos (APIs)
Menú: **Servicios Externos (API)** (opción 6 en consola) o página **Servicios API** en la web.

- **Clima por ciudad**
  - Si existe `OPENWEATHER_API_KEY` en el entorno, usa **OpenWeatherMap**.
  - Si no existe (o falla), usa **Open-Meteo** + geocodificación (sin clave) como respaldo.
  - Muestra temperatura, sensación térmica, humedad, viento y descripción.
- **Indicadores económicos** (mindicador.cl, sin API key): dólar, euro, UF, UTM y Bitcoin.
  - Incluye **caché y valores de respaldo** para funcionar siempre, incluso si la API externa falla.
- **Conversión de moneda**: convierte entre **CLP, USD y EUR** (en ambas direcciones, incluido USD↔EUR vía CLP), usando los indicadores anteriores.
  - También cuenta con **respaldo** para no fallar por problemas de red.

### Seguridad
- **Login obligatorio** al iniciar la aplicación.
- Contraseñas almacenadas como hash seguro (**PBKDF2-HMAC-SHA256 con salt**).
- **Control de acceso por roles**: `Administrador`, `Gerente`, `Empleado`, `Lector`.
- **Validación y saneamiento** de todas las entradas (nombres, emails, teléfonos, fechas, salarios, ciudades, códigos, usuarios y contraseñas).
- Gestión de usuarios (solo administrador): crear, listar, eliminar y cambiar contraseña.

### Interfaz web (Flask + Bootstrap)
- Login y sesión con roles.
- CRUD web de empleados, departamentos, proyectos, registros y asignaciones.
- **Tablero visual con drag & drop** para asignar empleados a departamentos.
- Servicios externos con formularios HTML.
- **Combobox con búsqueda (Select2)** en todos los selectores, más **autocompletado** en campos como ciudad, rol, moneda e IDs.
- Gestión de usuarios y restauración de BD (solo administrador).

---

## 🧰 Requisitos

- Python 3.10 o superior.
- Dependencias en `requirements.txt` (Flask, requests, etc.).
- Base de datos: MySQL si está disponible; en caso contrario usa **SQLite** automáticamente (portable).

---

## 🚀 Instalación y ejecución

### 1) Consola (CLI)
```bash
cd "POO 09-11-2.0"
python main.py
```
Inicia sesión con un usuario existente (por defecto `admin` / `Admin123!`).

### 2) Interfaz web
```bash
cd "POO 09-11-2.0"
python -m pip install -r requirements.txt
python webapp.py
```
Luego abre `http://127.0.0.1:5000` en el navegador.  
También puedes usar `run_web.bat` (Windows) o `run_web.sh` (Linux/macOS).

### Variables de entorno (`.env`)
Copia `.env.example` a `.env` y ajusta:
- `OPENWEATHER_API_KEY` (opcional, para clima con OpenWeatherMap).
- `ADMIN_INITIAL_PASSWORD` (contraseña inicial del admin).
- Configuración de base de datos (MySQL) y `FLASK_SECRET_KEY`.

---

## 📖 Uso rápido

1. **Inicia sesión** (CLI o web).
2. Usa el menú principal para gestionar empleados, departamentos, proyectos, asignaciones y registros.
3. En **Servicios API** consulta clima por ciudad, indicadores económicos o conversión de moneda.
4. Los selectores con búsqueda permiten elegir sin memorizar IDs o códigos.

---

## 🗂️ Estructura del proyecto

```text
.
├── main.py                 # Aplicación de consola
├── webapp.py               # Interfaz web (Flask)
├── templates/              # Plantillas HTML (Bootstrap + Select2)
├── static/css/app.css      # Estilos
├── SERVICIOS/              # clima_service.py, indicadores_service.py
├── DAO/                    # Acceso a datos (MySQL/SQLite)
├── DTO/                    # Objetos de transferencia
├── SEGURIDAD/              # autenticacion.py, validaciones.py
├── BASE/ecotech.sql        # Esquema base
├── requirements.txt
└── README.md
```

---

## 🔐 Roles y permisos

| Rol          | Acceso principal |
|--------------|------------------|
| Administrador | Todo + gestión de usuarios y restauración de BD |
| Gerente       | Empleados, departamentos, proyectos, asignaciones, registros, APIs |
| Empleado      | Proyectos, registros, APIs |
| Lector        | APIs |

---

## 📝 Notas técnicas

- Las solicitudes HTTP usan la librería oficial **`requests`** y procesan respuestas **JSON**.
- Las claves de API se leen desde variables de entorno (`.env`), evitando su exposición en el código.
- El backend de datos se selecciona automáticamente (MySQL si está disponible, SQLite en caso contrario), por lo que es portable.
- Los servicios externos incluyen **respaldo/caché** para mantenerse disponibles ante fallos de red.

---

## 📄 Licencia y créditos

Proyecto académico para la asignatura TI3021. Desarrollado con Python, Flask, Bootstrap, Select2 y SQLite/MySQL.