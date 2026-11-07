# Raspberry Irradiance Logger

## Descripción

Sistema de adquisición automática de datos de irradiancia mediante cuatro dispositivos ESP32 conectados a una Raspberry Pi.

El sistema permite consultar los datos mediante HTTP, almacenar las mediciones individuales y generar un archivo consolidado con la información disponible.

## Características

- Adquisición simultánea de cuatro ESP32.
- Comunicación HTTP mediante endpoints `/irradiancia`.
- Intervalo de adquisición configurable (60 segundos).
- Almacenamiento individual de cada dispositivo.
- Lectura de archivos TXT adicionales.
- Consolidación automática de datos.
- Conservación de los últimos datos válidos ante fallos de conexión.
- Inicio automático mediante systemd.
- Ejecución de múltiples programas Python.

## Dispositivos configurados

| Dispositivo | Endpoint |
|---|---|
| ESP1 | `http://backup-esp1.local/irradiancia` |
| ESP2 | `http://backup-esp2.local/irradiancia` |
| ESP3 | `http://backup-esp3.local/irradiancia` |
| ESP4 | `http://esp4-update.local/irradiancia` |

## Archivos generados

- `datos_esp1.txt`
- `datos_esp2.txt`
- `datos_esp3.txt`
- `datos_esp4.txt`
- `datos_adicional.txt`
- `datos_completos.txt`

## Instalación

El proyecto se ejecuta en Raspberry Pi OS o Ubuntu para Raspberry Pi.

Directorio de trabajo:

`/home/rasp4/Documents`

Entorno virtual:

`/home/rasp4/Documents/Estacion`

## Inicio automático

El sistema utiliza el servicio:

`adquisicion-irradiancia.service`

Para consultar su estado:

```bash
sudo systemctl status adquisicion-irradiancia.service
```

Para consultar los registros:

```bash
sudo journalctl -u adquisicion-irradiancia.service -f
```

## Autor

Proyecto de adquisición y monitoreo de irradiancia con Raspberry Pi y ESP32.
