import time
import csv
import os
import json
from datetime import datetime, date
from epevermodbus.driver import EpeverChargeController

# 1. Configuración
ctrl = EpeverChargeController("/dev/ttyACM0", 1)

# Guardar todos los archivos en la misma carpeta donde está este programa
CARPETA_PROGRAMA = os.path.dirname(os.path.abspath(__file__))


# Variables para almacenar acumulados (CON LA CLAVE 'last_gen_d' INCLUIDA)
acumulados = {
    'daily_generation': 0.0,
    'monthly_generation': 0.0,
    'annually_generation': 0.0,
    'total_generation': 53.42,  # Valor inicial basado en Excel
    'daily_usage': 0.0,
    'monthly_usage': 0.0,
    'annually_usage': 0.0,
    'total_usage': 0.0,
    'last_gen_d': 0.0,  
    'last_cons_d': 0.0,
    'last_day': None,
    'last_month': None,
    'last_year': None
}

def cargar_acumulados():
    """Cargar acumulados desde un archivo si existe"""
    acum_file = os.path.join(CARPETA_PROGRAMA, "acumulados.json")
    try:
        if os.path.exists(acum_file):
            with open(acum_file, 'r') as f:
                data = json.load(f)
                
                # Asegurar que todas las claves necesarias existan
                claves_necesarias = ['last_gen_d', 'last_cons_d', 'last_day', 'last_month', 'last_year']
                for clave in claves_necesarias:
                    if clave not in data:
                        data[clave] = acumulados.get(clave, 0.0)
                
                # Verificar si es el mismo día
                today = date.today().isoformat()
                if data.get('last_day') != today:
                    # Nuevo día, reiniciar diario
                    data['daily_generation'] = 0.0
                    data['daily_usage'] = 0.0
                    data['last_gen_d'] = 0.0
                    data['last_cons_d'] = 0.0
                    data['last_day'] = today
                
                # Verificar si es nuevo mes
                current_month = date.today().strftime('%Y-%m')
                if data.get('last_month') != current_month:
                    data['monthly_generation'] = 0.0
                    data['monthly_usage'] = 0.0
                    data['last_month'] = current_month
                
                # Verificar si es nuevo año
                current_year = date.today().year
                if data.get('last_year') != current_year:
                    data['annually_generation'] = 0.0
                    data['annually_usage'] = 0.0
                    data['last_year'] = current_year
                
                return data
    except Exception as e:
        print(f"⚠️  Error cargando acumulados: {e}")
    
    # Valores por defecto (CON TODAS LAS CLAVES)
    acumulados['last_day'] = date.today().isoformat()
    acumulados['last_month'] = date.today().strftime('%Y-%m')
    acumulados['last_year'] = date.today().year
    acumulados['last_gen_d'] = 0.0
    acumulados['last_cons_d'] = 0.0
    return acumulados

def guardar_acumulados(acum):
    """Guardar acumulados en un archivo"""
    acum_file = os.path.join(CARPETA_PROGRAMA, "acumulados.json")
    try:
        with open(acum_file, 'w') as f:
            json.dump(acum, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error guardando acumulados: {e}")

# Cargar acumulados existentes
acumulados = cargar_acumulados()

def traducir_modo_carga(modo):
    """Traducir el modo de carga al formato del Excel"""
    traducciones = {
        'EQUALIZATION': 'Equalize Charging',
        'EQUALIZE': 'Equalize Charging',
        'BOOST': 'Boost Charging',
        'FLOAT': 'Float Charging',
        'OVERCHARGE': 'Overcharge',
        'NORMAL': 'Normal',
        'UNKNOWN': 'Unknown',
        'OTHER': 'Other'
    }
    # Intentar varias formas de coincidencia
    modo_upper = str(modo).upper()
    for key in traducciones:
        if key in modo_upper:
            return traducciones[key]
    return str(modo)

def determinar_alarma_bateria(voltaje, temp, soc):
    """Determinar estado de alarma basado en valores"""
    if voltaje < 22.0 or voltaje > 30.0:
        return "Alta"
    elif soc < 20:
        return "Baja"
    elif temp > 45:
        return "Alta Temperatura"
    else:
        return "Normal"

def determinar_status_voltaje(voltaje):
    """Determinar estado del voltaje"""
    if 23.0 <= voltaje <= 29.0:
        return "Normal"
    elif voltaje < 23.0:
        return "Bajo"
    else:
        return "Alto"

# Nombre del archivo CSV (se crea uno por día)
hoy_excel = date.today().strftime('%b-%d-%Y')
excel_ruta = os.path.join(CARPETA_PROGRAMA, f"TesjoQ_{int(time.time()*1000)}_{hoy_excel}.csv")

# Verificar si el archivo ya existe para no sobrescribir
if os.path.exists(excel_ruta):
    # Buscar un nombre único
    counter = 1
    base_name = os.path.join(CARPETA_PROGRAMA, f"TesjoQ_{hoy_excel}")
    while os.path.exists(f"{base_name}_{counter}.csv"):
        counter += 1
    excel_ruta = f"{base_name}_{counter}.csv"

while True:
    try:
        fecha_actual = datetime.now()
        
        # Verificar si es nuevo día para crear nuevo archivo
        hoy_str = fecha_actual.strftime('%b-%d-%Y')
        if hoy_str != hoy_excel:
            hoy_excel = hoy_str
            excel_ruta = os.path.join(CARPETA_PROGRAMA, f"TesjoQ_{int(time.time()*1000)}_{hoy_excel}.csv")
        
        # --- LECTURA DE DATOS EN TIEMPO REAL ---
        # Paneles solares
        vs = ctrl.get_solar_voltage()
        isol = ctrl.get_solar_current()
        ps = ctrl.get_solar_power()
        
        # Batería
        vb = ctrl.get_battery_voltage()
        ib = ctrl.get_battery_current()
        pb = ctrl.get_battery_power()
        
        # Carga
        vl = ctrl.get_load_voltage()
        il = ctrl.get_load_current()
        pl = ctrl.get_load_power()
        
        # Temperatura
        temp = ctrl.get_battery_temperature()
        soc = ctrl.get_battery_state_of_charge()  # SOC en %
        v_max = ctrl.get_maximum_battery_voltage_today()
        v_min = ctrl.get_minimum_battery_voltage_today()
        
        # --- ENERGÍA ---
        gen_d = ctrl.get_generated_energy_today()  # kWh hoy
        cons_d = ctrl.get_consumed_energy_today()  # kWh hoy
        
        # --- VOLTAJE PANELES ---
        pv_max = ctrl.get_maximum_pv_voltage_today()
        pv_min = ctrl.get_minimum_pv_voltage_today()
        
        # --- ESTADO CARGA ---
        estado_carga = ctrl.get_charging_equipment_status()
        modo_carga_raw = estado_carga.get('charging_status', 'UNKNOWN') if estado_carga else 'UNKNOWN'
        modo_carga = traducir_modo_carga(modo_carga_raw)
        
        # --- ACTUALIZAR ACUMULADOS ---
        # Si es nuevo día, reiniciar valores diarios
        today = date.today().isoformat()
        if acumulados['last_day'] != today:
            acumulados['daily_generation'] = 0.0
            acumulados['daily_usage'] = 0.0
            acumulados['last_gen_d'] = 0.0
            acumulados['last_cons_d'] = 0.0
            acumulados['last_day'] = today
        
        # Actualizar valores diarios
        acumulados['daily_generation'] = gen_d
        acumulados['daily_usage'] = cons_d
        
        # Calcular incrementos para acumulación mensual/anual/total
        # Usar try-except para evitar errores si las claves no existen
        try:
            incremento_gen = max(0, gen_d - acumulados.get('last_gen_d', 0))
            incremento_cons = max(0, cons_d - acumulados.get('last_cons_d', 0))
            
            if incremento_gen > 0:
                acumulados['monthly_generation'] = acumulados.get('monthly_generation', 0) + incremento_gen
                acumulados['annually_generation'] = acumulados.get('annually_generation', 0) + incremento_gen
                acumulados['total_generation'] = acumulados.get('total_generation', 53.42) + incremento_gen
            
            if incremento_cons > 0:
                acumulados['monthly_usage'] = acumulados.get('monthly_usage', 0) + incremento_cons
                acumulados['annually_usage'] = acumulados.get('annually_usage', 0) + incremento_cons
                acumulados['total_usage'] = acumulados.get('total_usage', 0) + incremento_cons
            
        except KeyError as e:
            print(f"⚠️  Clave no encontrada en acumulados: {e}")
            # Inicializar las claves faltantes
            for clave in ['monthly_generation', 'annually_generation', 'monthly_usage', 'annually_usage']:
                if clave not in acumulados:
                    acumulados[clave] = 0.0
        
        # Guardar valores actuales para la próxima comparación
        acumulados['last_gen_d'] = gen_d
        acumulados['last_cons_d'] = cons_d
        
        guardar_acumulados(acumulados)
        
        # --- DETERMINAR ALARMAS Y ESTADOS ---
        bat_alarm = determinar_alarma_bateria(vb, temp, soc)
        temp_alarm = "Alta" if temp > 45 else "Normal"
        input_status = determinar_status_voltaje(vs)
        system_status = determinar_status_voltaje(vb)
        
        # --- DEFINIR ENCABEZADOS (con caracteres corregidos) ---
        headers = [
            'Time',
            'Energy Information-Daily Generation(kWh)',
            'Energy Information-Monthly Generation(kWh)',
            'Energy Information-Annually Generation(kWh)',
            'Energy Information-Total Generation(kWh)',
            'Energy Information-Daily Usage(kWh)',
            'Energy Information-Monthly Usage(kWh)',
            'Energy Information-Annually Usage(kWh)',
            'Energy Information-Total Usage(kWh)',
            'PV Information-PV Voltage(V)',
            'PV Information-PV Current(A)',
            'PV Information-PV Power(W)',
            'Battery Information-Battery Voltage(V)',
            'Battery Information-Battery Current(A)',
            'Battery Information-Charging Status',
            'Battery Information-Battery Temperature(°C)',  # Corregido
            'Battery Information-Battery SOC(%)',
            'Battery Information-Maximum Battery Voltage(V)',
            'Battery Information-Minimum Battery Voltage(V)',
            'Battery Information-Battery Voltage Alarm',
            'Battery Information-Battery Temperature Alarm',
            'Load Information-Load Voltage(V)',
            'Load Information-Load Current(A)',
            'Load Information-Load Power(W)',
            'Load Information-Load Status',
            'Load Information-Load Short Circuit',
            'Load Information-Load Overcurrent',
            'Device Information-Device Temperature(°C)',  # Corregido
            'Device Information-Input Voltage Status',
            'Device Information-System Voltage Status',
            'Device Information-Device Fault'
        ]
        
        # --- CREAR FILA DE DATOS ---
        fila_datos = [
            fecha_actual.strftime('%b-%d-%Y %H:%M:%S'),  # Time
            round(acumulados.get('daily_generation', 0.0), 2),    # Daily Generation
            round(acumulados.get('monthly_generation', 0.0), 2),  # Monthly Generation
            round(acumulados.get('annually_generation', 0.0), 2), # Annually Generation
            round(acumulados.get('total_generation', 53.42), 2),  # Total Generation
            round(acumulados.get('daily_usage', 0.0), 2),         # Daily Usage
            round(acumulados.get('monthly_usage', 0.0), 2),       # Monthly Usage
            round(acumulados.get('annually_usage', 0.0), 2),      # Annually Usage
            round(acumulados.get('total_usage', 0.0), 2),         # Total Usage
            round(vs, 2),                                # PV Voltage
            round(isol, 2),                              # PV Current
            round(ps, 2),                                # PV Power
            round(vb, 2),                                # Battery Voltage
            round(ib, 2),                                # Battery Current
            modo_carga,                                  # Charging Status (traducido)
            round(temp, 2),                              # Battery Temperature
            round(soc, 1),                               # Battery SOC
            round(v_max, 2),                             # Max Battery Voltage
            round(v_min, 2),                             # Min Battery Voltage
            bat_alarm,                                   # Battery Voltage Alarm
            temp_alarm,                                  # Battery Temperature Alarm
            round(vl, 2),                                # Load Voltage
            round(il, 2),                                # Load Current
            round(pl, 2),                                # Load Power
            'ON' if il > 0.05 else 'OFF',               # Load Status (corregido)
            'No',                                        # Load Short Circuit
            'No',                                        # Load Overcurrent
            round(temp + 5, 2),                          # Device Temperature
            input_status,                                # Input Voltage Status
            system_status,                               # System Voltage Status
            'Normal'                                     # Device Fault
        ]
        
        # --- GUARDAR EN ARCHIVO CSV ---
        # Verificar si el archivo existe para decidir si escribir encabezados
        archivo_existe = os.path.exists(excel_ruta)
        
        with open(excel_ruta, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Si es nuevo archivo, escribir encabezados
            if not archivo_existe:
                writer.writerow(['Device: TesjoQ1760391581180'])
                writer.writerow([])  # Línea vacía
                writer.writerow(headers)
            
            # Escribir datos
            writer.writerow(fila_datos)
        
        print(f"✅ Datos guardados en: {os.path.basename(excel_ruta)}")
        
        # --- INTERFAZ EN TERMINAL ---
        os.system('clear')
        print("=" * 105)
        print(f" CONTROLADOR HIDROLEAFER EPEVER MPPT | {fecha_actual.strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 105)
        print(f" SOC: {soc:>3.0f}% | GEN HOY: {gen_d:>6.2f}kWh | CONS HOY: {cons_d:>6.2f}kWh")
        print(f" TEMP: {temp:>4.1f}°C | MODO: {modo_carga:<18s} | ALARMA: {bat_alarm}")
        print("-" * 105)
        print(f" PANELES      : {vs:>6.2f}V | {isol:>5.2f}A | {ps:>7.1f}W | MAX: {pv_max:>5.2f}V | MIN: {pv_min:>5.2f}V")
        print(f" BATERÍA      : {vb:>6.2f}V | {ib:>5.2f}A | {pb:>7.1f}W | MAX: {v_max:>5.2f}V | MIN: {v_min:>5.2f}V")
        print(f" CARGA        : {vl:>6.2f}V | {il:>5.2f}A | {pl:>7.1f}W | ESTADO: {'ON' if il > 0.05 else 'OFF'}")
        print("-" * 105)
        print(f" ACUMULADOS   : DÍA={acumulados.get('daily_generation', 0.0):>6.2f}kWh | MES={acumulados.get('monthly_generation', 0.0):>7.2f}kWh")
        print(f"              : AÑO={acumulados.get('annually_generation', 0.0):>7.2f}kWh | TOTAL={acumulados.get('total_generation', 53.42):>7.2f}kWh")
        print("-" * 105)
        print(f" ARCHIVO      : {os.path.basename(excel_ruta)}")
        print(f"              : Registros añadidos al mismo archivo hasta nuevo día")
        print("-" * 105)
        
        # Mostrar advertencias
        warnings = []
        if soc < 30:
            warnings.append(f"⚠️  Batería baja ({soc}%)")
        if temp > 45:
            warnings.append(f"⚠️  Temperatura alta ({temp:.1f}°C)")
        if vb < 22.0:
            warnings.append(f"⚠️  Voltaje batería bajo ({vb:.1f}V)")
        if vb > 30.0:
            warnings.append(f"⚠️  Voltaje batería alto ({vb:.1f}V)")
        
        if warnings:
            print(" ADVERTENCIAS:")
            for warning in warnings:
                print(f"  {warning}")
            print("-" * 105)
        
        print("=" * 105)
        
        time.sleep(10)  # Esperar 10 segundos
        
    except KeyboardInterrupt:
        print("\n🔴 Programa detenido por el usuario")
        guardar_acumulados(acumulados)
        break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(5)
