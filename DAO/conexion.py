import os
import sqlite3

try:
    import pymysql
except Exception:
    pymysql = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, statement, parameters=(), *args, **kwargs):
        if isinstance(statement, str) and '%s' in statement:
            statement = statement.replace('%s', '?')
        return self._cursor.execute(statement, parameters, *args, **kwargs)


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())


class Conexion:
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'ecotech_db'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'charset': 'utf8mb4',
        }
        if pymysql is not None:
            self.config['cursorclass'] = pymysql.cursors.DictCursor
        self.backend = self._detectar_backend()
        if self.backend == 'sqlite':
            self._inicializar_sqlite()

    def _detectar_backend(self):
        if pymysql is None:
            return 'sqlite'
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                port=self.config['port'],
                connect_timeout=1,
                charset='utf8mb4',
            )
            conn.close()
            return 'mysql'
        except Exception:
            return 'sqlite'

    def _inicializar_sqlite(self):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ecotech.db')
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                telefono TEXT NOT NULL,
                salario REAL NOT NULL,
                rol TEXT NOT NULL DEFAULT 'Empleado',
                departamento_id INTEGER NULL,
                FOREIGN KEY (departamento_id) REFERENCES departamentos(id) ON UPDATE CASCADE ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT,
                gerente_id INTEGER NULL,
                FOREIGN KEY (gerente_id) REFERENCES empleados(id) ON UPDATE CASCADE ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS proyecto_empleados (
                proyecto_id INTEGER NOT NULL,
                empleado_id INTEGER NOT NULL,
                fecha_asignacion TEXT NOT NULL,
                PRIMARY KEY (proyecto_id, empleado_id),
                FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON UPDATE CASCADE ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS registros_tiempo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horas REAL NOT NULL,
                descripcion_tarea TEXT NOT NULL,
                fecha TEXT NOT NULL,
                empleado_id INTEGER NOT NULL,
                proyecto_id INTEGER NOT NULL,
                FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON UPDATE CASCADE ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'Empleado',
                empleado_id INTEGER NULL,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON UPDATE CASCADE ON DELETE SET NULL
            );
            """
        )

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM empleados")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT OR IGNORE INTO empleados (id, nombre, email, telefono, salario, rol) VALUES
                (1, 'Ana Silva', 'ana.silva@ecotech.cl', '+56911111111', 1400000.00, 'Empleado'),
                (2, 'Carlos Ruiz', 'carlos.ruiz@ecotech.cl', '+56922222222', 2200000.00, 'Gerente'),
                (3, 'Beatriz Soto', 'beatriz.soto@ecotech.cl', '+56933333333', 1200000.00, 'Empleado');
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO departamentos (id, nombre, descripcion, gerente_id) VALUES
                (1, 'Ingenieria', 'Desarrollo y proyectos tecnicos', 2),
                (2, 'Medio Ambiente', 'Sustentabilidad y monitoreo ambiental', 2);
                """
            )
            cursor.execute("UPDATE empleados SET departamento_id = 1 WHERE id IN (1, 2)")
            cursor.execute("UPDATE empleados SET departamento_id = 2 WHERE id = 3")
            cursor.execute(
                """
                INSERT OR IGNORE INTO proyectos (id, nombre, descripcion, fecha_inicio) VALUES
                (1, 'Parque Solar Atacama', 'Instalacion de paneles solares fotovoltaicos', '2026-03-01'),
                (2, 'Gestion Hidrica Central', 'Monitoreo de consumo de agua residual', '2026-04-15'),
                (3, 'Auditoria Energetica', 'Revision de consumo en plantas industriales', '2026-05-10');
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO proyecto_empleados (proyecto_id, empleado_id, fecha_asignacion) VALUES
                (1, 1, '2026-03-05'),
                (1, 2, '2026-03-05'),
                (2, 3, '2026-04-20');
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO registros_tiempo (id, horas, descripcion_tarea, fecha, empleado_id, proyecto_id) VALUES
                (1, 5.0, 'Diseno de circuitos electricos', '2026-04-01', 1, 1),
                (2, 8.0, 'Reunion de coordinacion y presupuesto', '2026-04-02', 2, 1),
                (3, 4.5, 'Toma de muestras de caudal', '2026-04-05', 3, 2);
                """
            )
        conn.commit()
        conn.close()

    def conectar(self):
        if self.backend == 'mysql':
            return pymysql.connect(**self.config)
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ecotech.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return SQLiteConnectionWrapper(conn)
