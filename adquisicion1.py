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

            # Consolidar ESP32 y TXT adic

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
