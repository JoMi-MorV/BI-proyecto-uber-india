# Uber India BI

ETL en Python para procesar las reservas de Uber India 2024 y cargarlas en PostgreSQL.

## Estructura del proyecto

```text
uber-india-bi/
├── data/
│   ├── raw/
│   │   └── uber_india_2024.csv
│   ├── staging/                 # archivos intermedios generados por el ETL
│   └── processed/               # CSV opcionales de salida
├── docs/
│   ├── capturas/                # capturas de validación y diagrama ER
│   └── resultados/              # salida de la validación (validacion.txt)                     
├── etl/
│   ├── cancelaciones.py
│   ├── config.py
│   ├── dimensiones.py
│   ├── duplicados.py
│   ├── extract.py
│   ├── imputacion.py
│   ├── limpieza.py
│   ├── load.py
│   ├── logger_etl.py
│   ├── quality_gates.py
│   └── transform.py
├── logs/                        # logs y resúmenes generados por el ETL
├── sql/
│   ├── 01_ddl.sql
│   ├── 02_seed.sql
│   ├── 03_views.sql
│   └── 04_validacion.sql
├── ejecutar_etl.py              # punto de entrada del ETL
├── requirements.txt
└── README.md
```

`.venv/`, `.env`, los archivos de staging y los logs son locales o generados; no son necesarios para reconstruir el código del proyecto.

## Ejecución en Linux

Ejecuta los comandos desde la raíz del proyecto.

### 1. Crear el entorno e instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En una terminal nueva, activa el entorno antes de trabajar:

```bash
source .venv/bin/activate
```

### 2. Preparar PostgreSQL

El servidor PostgreSQL debe estar iniciado y el usuario configurado debe tener permisos sobre la base de datos. El valor predeterminado es `BD_UBER_INDIA`, con usuario `postgres`, host `localhost` y puerto `5432`.

Si todavía no existe la base, créala:

```bash
createdb -U postgres -h localhost -p 5432 BD_UBER_INDIA
```

Para crear las tablas y los registros iniciales, ejecuta una vez:

```bash
psql -U postgres -h localhost -p 5432 -d BD_UBER_INDIA -f sql/01_ddl.sql
psql -U postgres -h localhost -p 5432 -d BD_UBER_INDIA -f sql/02_seed.sql
```

**Atención:** `01_ddl.sql` elimina y vuelve a crear las tablas. No lo ejecutes sobre una base con datos que quieras conservar. Si las tablas ya están creadas y sembradas, omite este paso.

### 3. Configurar la conexión

El ETL lee la contraseña de la variable de entorno `DB_PASSWORD`. Configúrala en la terminal actual antes de ejecutar el ETL:

```bash
export DB_PASSWORD='tu_contraseña'
export DB_USER=postgres DB_HOST=localhost DB_PORT=5432 DB_NAME=BD_UBER_INDIA
```

Reemplaza `tu_contraseña` por la contraseña real de PostgreSQL. Este método funcionó para completar la carga. La contraseña queda disponible solo en esa terminal, pero el comando puede guardarse en el historial del shell: no uses una contraseña que no quieras dejar en el historial y nunca subas ni compartas el valor real. El proyecto no carga automáticamente el archivo `.env`; hay que exportar las variables en cada terminal nueva.

### 4. Ejecutar el ETL completo

Con el entorno virtual activo y PostgreSQL configurado:

```bash
python ejecutar_etl.py
```

El comando ejecuta extract, transform y load. El CSV de origen predeterminado es `data/raw/uber_india_2024.csv`.

Se puede ejecutar un paso individual cuando ya existan los archivos intermedios requeridos:

```bash
python ejecutar_etl.py --paso extract
python ejecutar_etl.py --paso transform
python ejecutar_etl.py --paso load
```

Para transformar sin consultar ni escribir en PostgreSQL, y exportar CSV de revisión:

```bash
python ejecutar_etl.py --paso transform --sin-bd --exportar-csv
```

### 5. Validación

Requiere que el ETL ya haya cargado `fact_bookings`. Crea las vistas analíticas y ejecuta las pruebas de integridad y de KPIs:

```bash
# Crear las vistas analíticas
sudo -u postgres psql -d bd_uber_india -f sql/03_views.sql

# Ejecutar la validación y guardar la evidencia
mkdir -p docs/resultados
sudo -u postgres psql -d bd_uber_india -f sql/04_validacion.sql | tee docs/resultados/validacion.txt
```
