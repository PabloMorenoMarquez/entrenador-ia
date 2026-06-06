# Estructura del Libro de Google Sheets

Este documento describe la estructura, dimensiones y campos de cada una de las pestañas de mi libro de seguimiento (Fitness/Coach).

## 📄 Hoja: "perfil_usuario"
- **Tipo de hoja:** Ficha de perfil vertical (Fila 1 son etiquetas generales, los datos se estructuran por filas).
- **Dimensiones actuales:** 3 columnas × 31 filas.
- **Campos disponibles (Filas de datos):**
  * **Datos Personales:** `nombre` | `fecha_nacimiento` | `sexo` | `altura_cm` | `ciudad` | `peso_kg` | `edad`
  * **Bloque FÍSICO:** `nivel_experiencia` | `lesiones_actuales` | `lesiones_pasadas` | `limitaciones_fisicas`
  * **Bloque NUTRICIÓN:** `alergias_intolerancias` | `alimentos_que_no_gustan` | `alimentos_favoritos` | `dieta_tipo` | `suplementos_actuales`
  * **Bloque ESTILO DE VIDA:** `tipo_trabajo` | `horas_sueno_habitual` | `nivel_estres_habitual` | `disponibilidad_cocinar`
  * **Bloque ENTRENAMIENTO:** `lugar_entrenamiento` | `experiencia_gym_anos`

## 📄 Hoja: "memory"
- **Dimensiones actuales:** 7 columnas × 1 filas.
- **Columnas:** `ID | TIPO | CONTENIDO | PRIORIDAD | TAGS | FECHA_CREACION | ACTIVA`

## 📄 Hoja: "conversaciones"
- **Dimensiones actuales:** 4 columnas × 7 filas.
- **Columnas:** `ID_CONVERSACION | TIMESTAMP | ROL | CONTENIDO`

## 📄 Hoja: "dias_tipicos"
- **Dimensiones actuales:** 4 columnas × 12 filas.
- **Columnas:** `DIA_SEMANA | ENTRENA_HABITUALMENTE | HORA_PREFERIDA | NOTAS`

## 📄 Hoja: "plan_semanal"
- **Dimensiones actuales:** 6 columnas × 2 filas.
- **Columnas:** `SEMANA_INICIO | DIA | ENTRENA | HORA_REAL | LUGAR | NOTAS_DIA`

## 📄 Hoja: "objetivos"
- **Dimensiones actuales:** 6 columnas × 2 filas.
- **Columnas:** `FECHA_INICIO | OBJETIVO_PRINCIPAL | OBJETIVO_SECUNDARIO | FECHA_META | ESTADO | NOTAS`

## 📄 Hoja: "registro_corporal"
- **Dimensiones actuales:** 17 columnas × 4 filas.
- **Columnas:** `FECHA | HORA | PESO_KG | GRASA_PCT | MUSCULO_PCT | AGUA_PCT | PECHO_CM | CINTURA_CM | CADERA_CM | BRAZO_IZQ_CM | BRAZO_DER_CM | MUSLO_IZQ_CM | MUSLO_DER_CM | CUELLO_CM | HOMBROS_CM | CONDICION_MEDICION | NOTAS`

## 📄 Hoja: "fotos_progreso"
- **Dimensiones actuales:** 7 columnas × 4 filas.
- **Columnas:** `FECHA | PESO_KG_DIA | URL_FRENTE | URL_PERFIL_IZQ | URL_PERFIL_DER | URL_ESPALDA | NOTAS`

## 📄 Hoja: "historial_entrenamientos"
- **Dimensiones actuales:** 12 columnas × 1 filas.
- **Columnas:** `SESION_ID | FECHA | HORA_INICIO | HORA_FIN | DURACION_MIN | TIPO_SESION | GRUPO_MUSCULAR_PRINCIPAL | GRUPO_MUSCULAR_SECUNDARIO | NIVEL_ENERGIA_1_5 | NIVEL_ESFUERZO_1_10 | CALORIAS_APROX | NOTAS_SESION`

## 📄 Hoja: "ejercicios_detalle"
- **Dimensiones actuales:** 13 columnas × 1 filas.
- **Columnas:** `SESION_ID | FECHA | ORDEN | EJERCICIO | GRUPO_MUSCULAR | SERIES | REPS_OBJETIVO | REPS_REALIZADAS | PESO_KG | TIPO_PESO | DESCANSO_SEG | RIR | NOTAS_EJERCICIO`

## 📄 Hoja: "registro_comidas"
- **Dimensiones actuales:** 11 columnas × 4 filas.
- **Columnas:** `FECHA | HORA | TIPO_COMIDA | ALIMENTO | CANTIDAD_G_ML | CALORIAS | PROTEINAS_G | CARBOS_G | GRASAS_G | FIBRA_G | NOTAS`

## 📄 Hoja: "alimentos_disponibles"
- **Dimensiones actuales:** 6 columnas × 3 filas.
- **Columnas:** `ALIMENTO | CATEGORIA | CANTIDAD_APROX | UNIDAD | FECHA_ACTUALIZACION | DISPONIBLE`

## 📄 Hoja: "notas_coach"
- **Dimensiones actuales:** 5 columnas × 2 filas.
- **Columnas:** `FECHA | TIPO_NOTA | CONTENIDO | ACCION_PENDIENTE | RESUELTA`