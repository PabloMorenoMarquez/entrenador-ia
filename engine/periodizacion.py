"""
Capa de planificación por mesociclos — se coloca ENCIMA del motor reactivo.
El motor (motor_decision.py) sigue analizando el presente.
Este módulo planifica el futuro y provee contexto de fase al LLM.

Secuencia estándar:
  hipertrofia (4-6 sem) → fuerza (3-4 sem) → deload (1 sem) → repetir
  Para objetivo "fuerza": fuerza (4 sem) → deload (1 sem) → repetir
"""

from datetime import date, timedelta
from typing import Optional
from db.supabase_client import get_client, get_user_id

# ─────────────────────────────────────────
# CONFIGURACIÓN DE FASES
# ─────────────────────────────────────────

_DURACION_FASE = {
    # (objetivo) → {fase: semanas}
    "hipertrofia":   {"hipertrofia": 5, "fuerza": 4, "deload": 1},
    "fuerza":        {"hipertrofia": 4, "fuerza": 4, "deload": 1},
    "recomposicion": {"hipertrofia": 5, "fuerza": 3, "deload": 1},
}

_SIGUIENTE_FASE = {
    "hipertrofia": "fuerza",
    "fuerza":      "deload",
    "deload":      "hipertrofia",
}

# Volumen objetivo por fase y grupo muscular (series/semana)
_VOLUMEN_POR_FASE = {
    "hipertrofia": {"min": 14, "max": 20},
    "fuerza":      {"min": 6,  "max": 10},
    "deload":      {"min": 4,  "max": 6},
}

# Umbral de estancamiento largo: semanas sin progresión significativa
_SEMANAS_ESTANCAMIENTO = 5


# ─────────────────────────────────────────
# CRUD MESOCICLOS (Supabase)
# ─────────────────────────────────────────

def obtener_plan_activo() -> Optional[dict]:
    """Retorna el mesociclo activo actual o None si no existe."""
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("mesociclo")
        .select("*")
        .eq("user_id", uid)
        .eq("activo", True)
        .order("semana_inicio", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def crear_mesociclo(fase: str, objetivo: str, semana_inicio: Optional[date] = None) -> dict:
    """Crea un nuevo mesociclo (desactiva el anterior si existe)."""
    sb = get_client()
    uid = get_user_id()

    # Desactivar anterior
    sb.table("mesociclo").update({"activo": False}).eq("user_id", uid).eq("activo", True).execute()

    inicio = semana_inicio or date.today()
    duracion = _DURACION_FASE.get(objetivo, _DURACION_FASE["recomposicion"]).get(fase, 4)
    vol = _VOLUMEN_POR_FASE.get(fase, _VOLUMEN_POR_FASE["hipertrofia"])

    payload = {
        "user_id": uid,
        "fase": fase,
        "semana_inicio": inicio.isoformat(),
        "duracion_semanas": duracion,
        "objetivo_volumen": {"todas": vol},
        "activo": True,
    }
    result = sb.table("mesociclo").insert(payload).execute()
    return result.data[0] if result.data else payload


def obtener_o_crear_plan(objetivo: str) -> dict:
    """Obtiene el plan activo o crea uno nuevo (hipertrofia por defecto)."""
    plan = obtener_plan_activo()
    if not plan:
        plan = crear_mesociclo("hipertrofia", objetivo)
        print(f"[periodizacion] Nuevo mesociclo creado: hipertrofia")
    return plan


# ─────────────────────────────────────────
# ANÁLISIS DE FASE ACTUAL
# ─────────────────────────────────────────

def semana_en_fase(plan: dict) -> int:
    """Semana actual dentro de la fase (1-indexed)."""
    inicio = date.fromisoformat(plan["semana_inicio"])
    dias = (date.today() - inicio).days
    return max(1, dias // 7 + 1)


def progreso_fase(plan: dict) -> dict:
    """
    Retorna: semana actual, duración, % completado, días restantes hasta transición.
    """
    semana = semana_en_fase(plan)
    duracion = plan.get("duracion_semanas", 4)
    pct = min(100, round(semana / duracion * 100))
    dias_restantes = max(0, (
        date.fromisoformat(plan["semana_inicio"])
        + timedelta(weeks=duracion)
        - date.today()
    ).days)
    return {
        "semana": semana,
        "duracion": duracion,
        "pct_completado": pct,
        "dias_restantes": dias_restantes,
    }


def evaluar_transicion(plan: dict, estado_global: dict, objetivo: str) -> Optional[str]:
    """
    Decide si hay que transicionar de fase.
    Retorna: "deload_urgente" | "transicion_programada" | "continuar" | None
    """
    progreso = progreso_fase(plan)
    fase = plan.get("fase", "hipertrofia")
    score = (estado_global or {}).get("score_global", 50)

    # Deload urgente: atleta en estado crítico (score < 30) en cualquier fase
    if score < 30 and fase != "deload":
        return "deload_urgente"

    # Transición programada: fase completada o sobrépasada
    if progreso["semana"] >= progreso["duracion"]:
        return "transicion_programada"

    # Señal anticipada: 80% completado + fatiga alta (score < 45)
    if progreso["pct_completado"] >= 80 and score < 45 and fase != "deload":
        return "transicion_programada"

    return "continuar"


def siguiente_fase_nombre(plan: dict, objetivo: str) -> str:
    """Retorna la siguiente fase en la secuencia."""
    if objetivo == "fuerza" and plan.get("fase") == "hipertrofia":
        return "deload"  # para objetivo fuerza: fuerza → deload → fuerza
    return _SIGUIENTE_FASE.get(plan.get("fase", "hipertrofia"), "hipertrofia")


def aplicar_transicion(plan: dict, objetivo: str, motivo: str = "") -> dict:
    """Crea el siguiente mesociclo y retorna el nuevo plan."""
    siguiente = siguiente_fase_nombre(plan, objetivo)
    nuevo = crear_mesociclo(siguiente, objetivo)
    print(f"[periodizacion] Transición: {plan['fase']} → {siguiente} ({motivo})")
    return nuevo


# ─────────────────────────────────────────
# ESTANCAMIENTO A LARGO PLAZO
# ─────────────────────────────────────────

def analizar_estancamiento_largo(
    ejercicios_historial: dict,
    semanas: int = _SEMANAS_ESTANCAMIENTO,
) -> dict[str, dict]:
    """
    Detecta ejercicios principales que llevan ≥N semanas sin progresión significativa.
    ejercicios_historial: {nombre: [{fecha, series, reps_realizadas, peso, rir}, ...]}
    Retorna: {nombre: {semanas_estancado, ultima_progresion, recomendacion}}
    """
    from datetime import datetime

    corte = date.today() - timedelta(weeks=semanas)
    estancados = {}

    for nombre, registros in ejercicios_historial.items():
        # Solo analizar ejercicios con suficiente historia
        registros_recientes = [
            r for r in registros
            if r.get("fecha") and _parsear_fecha(r["fecha"]) >= corte
        ]
        if len(registros_recientes) < 3:
            continue

        # Calcular volumen normalizado (series × reps × peso)
        volumenes = []
        for r in sorted(registros_recientes, key=lambda x: x.get("fecha", "")):
            vol = r.get("series", 0) * r.get("reps_realizadas", 0) * max(r.get("peso", 1), 1)
            volumenes.append(vol)

        if not volumenes:
            continue

        # Progresión: diferencia entre primera y última semana del período
        v_inicio = sum(volumenes[:2]) / len(volumenes[:2])
        v_final = sum(volumenes[-2:]) / len(volumenes[-2:])

        progresion_pct = ((v_final - v_inicio) / max(v_inicio, 1)) * 100

        # Estancado si progresión < 3% en el período analizado
        if abs(progresion_pct) < 3:
            estancados[nombre] = {
                "semanas_estancado": semanas,
                "progresion_pct": round(progresion_pct, 1),
                "recomendacion": _recomendacion_estancamiento(nombre),
            }

    return estancados


def _parsear_fecha(fecha_str: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(fecha_str, fmt).date()
        except ValueError:
            continue
    return date.min


def _recomendacion_estancamiento(nombre_ejercicio: str) -> str:
    """Recomendación básica según tipo de ejercicio estancado."""
    lower = nombre_ejercicio.lower()
    if any(kw in lower for kw in ["sentadilla", "squat"]):
        return "Cambiar a sentadilla búlgara, prensa o hack squat durante 3-4 semanas."
    if any(kw in lower for kw in ["press banca", "bench"]):
        return "Probar press inclinado, press con mancuernas o press de pie 3-4 semanas."
    if any(kw in lower for kw in ["peso muerto", "deadlift"]):
        return "Sustituir por peso muerto rumano, buenos días o hip thrust."
    if any(kw in lower for kw in ["dominada", "pullup", "pull-up"]):
        return "Cambiar a remo con barra, remo Pendlay o jalón al pecho."
    return "Variar ángulo, agarre o implemento (barra → mancuernas, libre → máquina)."


# ─────────────────────────────────────────
# RESUMEN PARA PROMPT
# ─────────────────────────────────────────

def resumen_periodizacion(plan: dict, objetivo: str, estancados: dict) -> str:
    """
    Genera el bloque de texto para inyectar al prompt del LLM.
    """
    progreso = progreso_fase(plan)
    fase = plan.get("fase", "hipertrofia")
    vol = (plan.get("objetivo_volumen") or {}).get("todas", _VOLUMEN_POR_FASE.get(fase, {}))

    lineas = [
        f"Fase actual: {fase.upper()} — semana {progreso['semana']}/{progreso['duracion']} "
        f"({progreso['pct_completado']}% completado, {progreso['dias_restantes']} días restantes)",
        f"Objetivo de volumen esta fase: {vol.get('min', '?')}-{vol.get('max', '?')} series/grupo/semana",
        f"Siguiente fase: {_SIGUIENTE_FASE.get(fase, 'hipertrofia')}",
    ]

    if estancados:
        lineas.append(f"\nEjercicios estancados ≥{_SEMANAS_ESTANCAMIENTO} semanas:")
        for nombre, info in list(estancados.items())[:3]:
            lineas.append(f"  - {nombre}: {info['recomendacion']}")

    return "\n".join(lineas)
