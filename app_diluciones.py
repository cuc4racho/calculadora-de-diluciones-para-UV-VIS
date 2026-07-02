import streamlit as st
import pandas as pd
import numpy as np

# ======================================================
# Configuración de la App
# ======================================================
st.set_page_config(
    page_title="Diseñador de Diluciones a la Medida", 
    layout="wide"
)

st.title("🧪 Diseñador Inteligente y Configurable de Diluciones")
st.markdown(
    "Define cuántos niveles de dilución necesitas, introduce tus factores a la medida "
    "y obtén la mejor estrategia de pipeteo con números redondos."
)

MATRACES_ESTANDAR = [5, 10, 25, 50, 100, 250, 500, 1000]

# ======================================================
# 1. CONTROL DE DISPONIBILIDAD DE MUESTRA
# ======================================================
st.subheader("1. Control de Volumen Disponible")
v_madre_disponible = st.number_input(
    "Cantidad total de Muestra Madre original disponible en tu vial (mL):",
    min_value=0.1, value=5.0, step=0.5,
    help="Evita diseñar bancos de dilución que consuman más reactivo del que posees."
)

# ======================================================
# 2. ENTRADA DINÁMICA DE NIVELES Y FACTORES
# ======================================================
st.subheader("2. Configurar Niveles de Dilución y Balones de Aforo")

# El usuario define cuántas diluciones quiere realizar en total
num_factores = st.number_input(
    "¿Cuántos niveles de dilución deseas preparar para tu curva?", 
    min_value=1, max_value=20, value=5, step=1
)

st.markdown("### 🛠️ Introduce los factores y selecciona los balones para cada nivel:")

# Lista para almacenar la configuración dinámica del usuario
lista_config_usuario = []

# Lista de valores por defecto lógicos para rellenar los campos inicialmente
valores_defecto_factores = [5000, 1000, 500, 100, 50, 20, 10, 5, 2]

# Generar filas dinámicas basadas en la cantidad de factores solicitados
for i in range(int(num_factores)):
    col_f, col_m = st.columns([1, 1])
    
    # Asignar valor por defecto de la lista o un múltiplo si excede la lista guía
    val_def = valores_defecto_factores[i] if i < len(valores_defecto_factores) else float((i + 1) * 10)
    
    with col_f:
        factor_val = st.number_input(
            f"Factor para el Nivel {i+1} (ej. 50 para 1:50)", 
            min_value=1.1, value=float(val_def), step=10.0, key=f"f_{i}"
        )
    with col_m:
        # Estimar un balón por defecto adecuado según el tamaño del factor
        def_index = 3 if factor_val <= 50 else (4 if factor_val in [100, 500] else 5)
        matraz_val = st.selectbox(
            f"Balón de aforo para Nivel {i+1} (mL)", 
            options=MATRACES_ESTANDAR, 
            index=min(def_index, len(MATRACES_ESTANDAR)-1), key=f"m_{i}"
        )
        
    # Guardar la combinación como un diccionario
    lista_config_usuario.append({"factor": factor_val, "matraz": matraz_val})

# Botón ejecutor
calcular = st.button("Calcular y Validar Banco de Diluciones", type="primary")

# ======================================================
# 3. FUNCIONES DE EVALUACIÓN ANALÍTICA
# ======================================================
def evaluar_comodidad_pipeteo(v_ml):
    uL = round(v_ml * 1000, 2)
    if abs(v_ml - round(v_ml)) < 1e-4:
        return "✅ Entero Excelente (mL)", True
    if abs((v_ml * 2) - round(v_ml * 2)) < 1e-4:
        return "✅ Medio Mililitro (Redondo)", True
    if uL % 50 == 0:
        return "✅ Redondo Excelente (μL)", True
    if uL % 10 == 0:
        return "🟡 Aceptable (Múltiplo de 10 μL)", True
    return "❌ Decimal Complejo (Evitar)", False

def buscar_alternativas_redondas(factor):
    sugerencias = []
    for m in MATRACES_ESTANDAR:
        v_posible = m / factor
        _, es_bueno = evaluar_comodidad_pipeteo(v_posible)
        if es_bueno and v_posible >= 0.02:
            sugerencias.append(f"{m} mL")
    return sugerencias

# ======================================================
# 4. PROCESAMIENTO Y DESPLIEGUE DE RESULTADOS
# ======================================================
if calcular:
    st.subheader("3. Diagnóstico de la Ruta de Preparación")
    
    # ORDENAR la lista de mayor a menor factor (mayor a menor concentración)
    # Esto asegura que la lógica del Stock intermedio se aplique correctamente a los niveles más diluidos
    lista_config_ordenada = sorted(lista_config_usuario, key=lambda x: x["factor"], reverse=True)
    
    cronograma = []
    v_madre_total_requerido = 0.0
    hubo_decimales_complejos = False
    
    # Evaluar si los factores altos de la lista ordenada necesitan stock intermedio
    necesita_stock = False
    for item in lista_config_ordenada:
        if (item["matraz"] / item["factor"]) < 0.02: 
            necesita_stock = True
            
    # Configuración del Stock basada en el vial del usuario
    v_tomar_stock = 1.0 if v_madre_disponible >= 2.0 else 0.5
    matraz_stock = 50 if v_madre_disponible >= 2.0 else 25
    factor_stock = matraz_stock / v_tomar_stock  # Ej: Stock 1:50
    
    if necesita_stock:
        v_madre_total_requerido += v_tomar_stock

    # Procesar la lista ordenada secuencialmente
    for item in lista_config_ordenada:
        f = item["factor"]
        matraz = item["matraz"]
        
        # Enrutamiento analítico automático
        if necesita_stock and f >= 1000:
            origen = f"Solución Stock Intermedia (1:{factor_stock:.0f})"
            factor_origen = factor_stock
        else:
            origen = "Muestra Madre Original"
            factor_origen = 1.0
            
        factor_relativo = f / factor_origen
        v_pipeta = matraz / factor_relativo
        
        if origen == "Muestra Madre Original":
            v_madre_total_requerido += v_pipeta
            
        dictamen, es_comodo = evaluar_comodidad_pipeteo(v_pipeta)
        
        alternativas_texto = "-"
        if not es_comodo:
            hubo_decimales_complejos = True
            lista_alt = buscar_alternativas_redondas(f)
            if lista_alt:
                alternativas_texto = f"Cambiar a balón de: {', '.join(lista_alt)}"
            else:
                alternativas_texto = "Hacer dilución intermedia personalizada"

        cronograma.append({
            "Factor": f"1:{f:.0f}",
            "Origen del Líquido": origen,
            "Volumen a Pipetear": v_pipeta,
            "Equivalente (μL)": round(v_pipeta * 1000, 0),
            "Balón Elegido": f"{matraz} mL",
            "Calidad del Volumen": dictamen,
            "💡 Alternativa sugerida": alternativas_texto
        })

    # --- PANEL DE VALIDACIONES ---
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        if v_madre_total_requerido > v_madre_disponible:
            st.error(f"❌ **¡Error de Volumen!** Esta preparación requiere **{v_madre_total_requerido:.2f} mL** de tu Muestra Madre, pero solo posees **{v_madre_disponible:.2f} mL**. Por favor, reduce el tamaño de tus balones de aforo.")
        else:
            st.success(f"✔️ **Volumen de muestra verificado:** Consumo total de **{v_madre_total_requerido:.2f} mL**. Te restarán **{v_madre_disponible - v_madre_total_requerido:.2f} mL** seguros en tu vial.")
            
    with col_v2:
        if hubo_decimales_complejos:
            st.warning("⚠️ **Volúmenes complejos detectados:** Algunos pasos contienen decimales difíciles de medir con exactitud. Revisa las alternativas sugeridas en la tabla de abajo.")
        else:
            st.success("🎉 **¡Excelente!** Todos los volúmenes del banco son números redondos y fáciles de pipetear.")

    # Mostrar tabla estructurada
    df_cronograma = pd.DataFrame(cronograma)
    st.dataframe(
        df_cronograma.style.format({
            "Volumen a Pipetear": "{:.3f}",
            "Equivalente (μL)": "{:.0f}"
        }),
        hide_index=True, 
        use_container_width=True
    )

    # --- INSTRUCCIONES EN LA MESA ---
    st.subheader("📑 Guía Práctica de Preparación")
    if necesita_stock:
        st.markdown(f"**[PASO PREVIO MANDATORIO] / Preparación del Stock Intermedio (1:{factor_stock:.0f}):**")
        st.markdown(f"* Pipetea exactamente **{v_tomar_stock:.1f} mL** de tu Muestra Madre Original y afóralos en un balón de **{matraz_stock} mL**.")
        st.markdown("---")

    for p in cronograma:
        alerta_css = "🚨 " if "❌" in p["Calidad del Volumen"] else ""
        st.markdown(f"""
        **Para preparar la Dilución {p['Factor']}:**
        * {alerta_css}Toma **{p['Volumen a Pipetear']:.3f} mL** ({p['Equivalente (μL)']:.0f} μL) desde la **{p['Origen del Líquido']}**.
        * Transfiérelos al balón volumétrico de **{p['Balón Elegido']}**.
        """)