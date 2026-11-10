import os
import time
import math
import logging
import tempfile
import urllib.request
import urllib.error

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


# ==========================================================
# CONFIGURACION GENERAL
# ==========================================================

INTERVALO = 60
TIMEOUT = 10

DIRECTORIO = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_LOG = os.path.join(
    DIRECTORIO, "adquisicion.log"
)

ARCHIVO_CONSOLIDADO = os.path.join(
    DIRECTORIO, "datos_completos.txt"
)


# ==========================================================
# CONFIGURACION DE LAS CUATRO ESP32
# ==========================================================

DISPOSITIVOS = {
    "esp1": {
        "url": "http://backup-esp1.local/irradiancia",
        "archivo": "datos_esp1.txt"
    },

    "esp2": {
        "url": "http://backup-esp2.local/irradiancia",
        "archivo": "datos_esp2.txt"
    },

    "esp3": {
        "url": "http://backup-esp3.local/irradiancia",
        "archivo": "datos_esp3.txt"
    },

    "esp4": {
        "url": "http://esp4-update.local/irradiancia",
        "archivo": "datos_esp4.txt"
    }
}


# ==========================================================
# ARCHIVOS TXT ADICIONALES
# ==========================================================
#
# Aqui puedes agregar archivos generados por otros programas.
#
# Ejemplo:
#
# ARCHIVOS_ADICIONALES = [
#     "datos_adicional.txt",
#     "datos_temperatura.txt",
#     "datos_otro_programa.txt"
# ]
#
# Todos deben contener valores numericos separados por comas.
# Si un archivo no existe, se omite automaticamente.
# ==========================================================

ARCHIVOS_ADICIONALES = [
    "datos_adicional.txt"
]


# ==========================================================
# CONFIGURACION DEL REGISTRO
# ==========================================================

logging.basicConfig(
    filename=ARCHIVO_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ==========================================================
# GUARDADO ATOMICO DE ARCHIVOS
# ==========================================================

def guardar_archivo(ruta, contenido):

    temporal = None

    directorio_destino = os.path.dirname(ruta)

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directorio_destino,
            delete=False
        ) as archivo:

            temporal = archivo.name

            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())

        os.replace(temporal, ruta)
        temporal = None

    finally:

        if temporal and os.path.exists(temporal):
            os.remove(temporal)


# ==========================================================
# VALIDACION DE DATOS
# ==========================================================

def validar_datos(contenido):

    contenido = contenido.strip()

    # Eliminar comas finales
    contenido = contenido.rstrip(",").strip()

    if not contenido:
        raise ValueError("Archivo o respuesta vacia")

    valores = [
        valor.strip()
        for valor in contenido.split(",")
    ]

    if not valores:
        raise ValueError("No se recibieron valores")

    for indice, valor in enumerate(valores, start=1):

        if not valor:
            raise ValueError(
                f"Valor vacio en posicion {indice}"
            )

        numero = float(valor)

        if not math.isfinite(numero):
            raise ValueError(
                f"Valor no finito en posicion {indice}: {valor}"
            )

    return ",".join(valores), len(valores)


# ==========================================================
# ADQUISICION DE DATOS DESDE ESP32
# ==========================================================

def adquirir_datos(nombre, configuracion):

    request = urllib.request.Request(
        configuracion["url"],
        headers={
            "User-Agent": "Raspberry-Irradiancia/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT
    ) as respuesta:

        if respuesta.status != 200:
            raise RuntimeError(
                f"Respuesta HTTP inesperada: {respuesta.status}"
            )

        contenido = respuesta.read().decode("utf-8")

    return validar_datos(contenido)


# ==========================================================
# PROCESAMIENTO INDIVIDUAL DE CADA ESP32
# ==========================================================

def procesar_dispositivo(nombre, configuracion):

    try:

        datos, cantidad = adquirir_datos(
            nombre,
            configuracion
        )

        ruta = os.path.join(
            DIRECTORIO,
            configuracion["archivo"]
        )

        guardar_archivo(ruta, datos)

        print(
            f"[OK] {nombre.upper()}: "
            f"{cantidad} valores actualizados",
            flush=True
        )

        logging.info(
            "%s adquisicion correcta: %s valores",
            nombre.upper(),
            cantidad
        )

        return True

    except urllib.error.HTTPError as error:

        print(
            f"[ERROR] {nombre.upper()}: HTTP {error.code}",
            flush=True
        )

        logging.error(
            "%s error HTTP: %s",
            nombre.upper(),
            error
        )

    except urllib.error.URLError as error:

        print(
            f"[ERROR] {nombre.upper()}: conexion: {error.reason}",
            flush=True
        )

        logging.error(
            "%s error de conexion: %s",
            nombre.upper(),
            error.reason
        )

    except Exception as error:

        print(
            f"[ERROR] {nombre.upper()}: {error}",
            flush=True
        )

        logging.exception(
            "%s error durante la adquisicion",
            nombre.upper()
        )

    print(
        f"[AVISO] {nombre.upper()}: "
        "se conserva su ultimo TXT valido",
        flush=True
    )

    return False


# ==========================================================
# LECTURA Y VALIDACION DE UN TXT
# ==========================================================

def leer_archivo_txt(ruta):

    with open(
        ruta,
        "r",
        encoding="utf-8"
    ) as archivo:

        contenido = archivo.read()

    return validar_datos(contenido)


# ==========================================================
# CONSOLIDACION DE TODOS LOS ARCHIVOS
# ==========================================================

def actualizar_consolidado():

    datos_consolidados = []
    fuentes_incluidas = []
    total_valores = 0

    # ------------------------------------------------------
    # 1. LEER LOS TXT DE LAS CUATRO ESP32
    # ------------------------------------------------------

    for nombre, configuracion in DISPOSITIVOS.items():

        ruta = os.path.join(
            DIRECTORIO,
            configuracion["archivo"]
        )

        if not os.path.isfile(ruta):

            print(
                f"[AVISO] {nombre.upper()}: "
                "no existe TXT; se omite",
                flush=True
            )

            continue

        try:

            datos, cantidad = leer_archivo_txt(ruta)

            datos_consolidados.append(datos)

            fuentes_incluidas.append(nombre.upper())

            total_valores += cantidad

            print(
                f"[TXT] {nombre.upper()}: "
                f"{cantidad} valores incluidos",
                flush=True
            )

        except Exception as error:

            print(
                f"[AVISO] {nombre.upper()}: "
                f"TXT invalido; se omite: {error}",
                flush=True
            )

            logging.exception(
                "Error leyendo TXT de %s",
                nombre.upper()
            )

    # ------------------------------------------------------
    # 2. LEER LOS ARCHIVOS TXT ADICIONALES
    # ------------------------------------------------------

    for nombre_archivo in ARCHIVOS_ADICIONALES:

        ruta = os.path.join(
            DIRECTORIO,
            nombre_archivo
        )

        nombre_fuente = os.path.basename(
            nombre_archivo
        )

        if not os.path.isfile(ruta):

            print(
                f"[ADICIONAL] {nombre_fuente}: "
                "todavia no existe; se omite",
                flush=True
            )

            continue

        try:

            datos, cantidad = leer_archivo_txt(ruta)

            datos_consolidados.append(datos)

            fuentes_incluidas.append(nombre_fuente)

            total_valores += cantidad

            print(
                f"[ADICIONAL] {nombre_fuente}: "
                f"{cantidad} valores incluidos",
                flush=True
            )

            logging.info(
                "Archivo adicional incluido: %s (%s valores)",
                nombre_fuente,
                cantidad
            )

        except Exception as error:

            print(
                f"[ADICIONAL] {nombre_fuente}: "
                f"archivo invalido; se omite: {error}",
                flush=True
            )

            logging.exception(
                "Error leyendo archivo adicional %s",
                nombre_fuente
            )

    # ------------------------------------------------------
    # 3. ACTUALIZAR ARCHIVO CONSOLIDADO
    # ------------------------------------------------------

    if not datos_consolidados:

        print(
            "[AVISO] No hay TXT validos. "
            "Se conserva el consolidado anterior.",
            flush=True
        )

        logging.warning(
            "No hay archivos validos para consolidar"
        )

        return

    try:

        contenido_final = ",".join(
            datos_consolidados
        )

        guardar_archivo(
            ARCHIVO_CONSOLIDADO,
            contenido_final
        )

        print("\n========================================")
        print(" CONSOLIDADO ACTUALIZADO")
        print("========================================")

        print(
            f"Total de valores: {total_valores}"
        )

        print(
            f"Total de fuentes: {len(fuentes_incluidas)}"
        )

        print(
            "Fuentes: " + ", ".join(fuentes_incluidas)
        )

        print("Archivo: datos_completos.txt")
        print("========================================")

        logging.info(
            "Consolidado actualizado: %s valores. Fuentes: %s",
            total_valores,
            ", ".join(fuentes_incluidas)
        )

    except Exception:

        print(
            "[ERROR] No se pudo actualizar "
            "datos_completos.txt",
            flush=True
        )

        logging.exception(
            "Error actualizando archivo consolidado"
        )


# ==========================================================
# PROGRAMA PRINCIPAL
# ==========================================================

def main():

    print("\n========================================")
    print(" SISTEMA DE ADQUISICION DE IRRADIANCIA")
    print("========================================")

    print("ESP32 configuradas: 4")
    print("Valores por placa: VARIABLE")
    print(f"Intervalo: {INTERVALO} segundos")
    print("Adquisicion simultanea: ACTIVA")
    print("Archivos adicionales: ACTIVOS")
    print("Consolidacion automatica: ACTIVA")
    print("Conservacion de datos anteriores: ACTIVA")
    print("Correccion de comas finales: ACTIVA")
    print("Presiona CTRL+C para detener")

    print("========================================\n")

    logging.info(
        "Sistema de adquisicion iniciado"
    )

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        while True:

            inicio = time.monotonic()

            print(
                f"\n--- ADQUISICION "
                f"{datetime.now():%Y-%m-%d %H:%M:%S} ---",
                flush=True
            )

            # Consultar las cuatro ESP32 simultaneamente
            tareas = []

            for nombre, configuracion in DISPOSITIVOS.items():

                tarea = executor.submit(
                    procesar_dispositivo,
                    nombre,
                    configuracion
                )

                tareas.append(tarea)

            # Esperar a que terminen las cuatro adquisiciones
            for tarea in tareas:
                tarea.result()

            # Consolidar ESP32 y TXT adicionales
            actualizar_consolidado()

            # Mantener intervalo entre inicios de ciclo
            transcurrido = time.monotonic() - inicio

            espera = max(
                0,
                INTERVALO - transcurrido
            )

            print(
                f"\nSiguiente adquisicion en "
                f"{espera:.1f} segundos",
                flush=True
            )

            time.sleep(espera)


# ==========================================================
# INICIO
# ==========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n[INFO] Sistema detenido manualmente",
            flush=True
        )

        logging.info(
            "Sistema detenido manualmente"
        )
