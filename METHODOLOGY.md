# Metodología experimental

## Abstracción y controles
A0 reservas abstractas; A1 compartimentos y flujos; A2 subsistemas regulados; A3 geometría/mecánica; A4 organización celular/bioquímica. Ejes combinables, no escalera obligatoria. Fijo como control permanente. P: plan parcial y variables modificables explícitas. X: sustrato y reglas sin anatomía final prescrita. Registrar si hay programa de desarrollo, optimización externa, mutación o control interno; no confundir con morfogénesis autónoma.

## Preregistro (experiments/<id>/protocol.md)
ID, hito, requisito, pregunta, hipótesis falsable y alternativa nula; referencias, frontera, unidades y escalas; baseline/tratamiento, factores, controles positivos/negativos, métricas, patrones de referencia externa o solución analítica, tolerancias cuantitativas justificadas y condición de rechazo; semillas, tamaño de muestra/unidad independiente, escenarios de ajuste y reservados, presupuesto CPU/RAM/tiempo, versiones y procedimiento reproducible. Registrar cambios antes de ejecutar; preservar protocolos previos y negativos. No ajustar contra test reservado ni cambiar umbrales post hoc.

## Banco experimental
Entorno sintético con stocks/flujos, condiciones térmicas, superficies/obstáculos y estímulos cuando corresponda. Controlador prescrito/aleatorio/simple con interfaz pública; mismo controlador y presupuesto en contrastes pertinentes. Instrumentación separada. No confundir control prescrito con autonomía. No imponer beber/comer por umbral; regulación local involuntaria con costes explícitos admisible. No usar LLM para resolver fisiología. Movimiento: fuerza/desplazamiento/contacto/trabajo, no teletransportación. Cambios de geometría: contabilizar materia/energía de construcción y cambios físicos, no crear masa escalando gráficos. X puede usar motor distinto si comparabilidad de observables/fronteras justificada.

## Invariantes y métricas
- Materia: delta de pool = entradas - salidas + producción/consumo por transformaciones; conservar elementos/masa en frontera ampliada y declarar aproximaciones. Energía: delta de energía almacenada/interna/mecánica = entradas - salidas (incluidos calor, trabajo y residuos), sin doble conteo. Residuales normalizados y acumulados; tolerancias justificadas por escala, precisión y refinamiento temporal/espacial. No clipping silencioso.
- Estados admisibles: stocks no negativos, saturación explícita, recursos finitos, rechazo sin mutación oculta. Muerte definida operacionalmente como pérdida irreversible de función bajo modelo y condiciones, sin reset arbitrario.
- Causalidad: intervenciones de un factor y combinadas; controles sin recurso, actividad o mecanismo; perturbaciones, recuperación, calor/frío según hipótesis. Referencia independiente, distinguir calibración biológica de hipótesis físicas.
- Sensores: posición, contacto, alcance y propiedades declaradas; oclusión si pertinente; sin estado oculto. Trazas observación → comando → resultado → estado.
- Reproducibilidad: commit/versiones, config, semillas, comandos, salida cruda/resumen; replay/checkpoint con tolerancia justificada; duración/RAM/tiempo simulado. No contar pasos o medidas correlacionadas como réplicas.
- Suficiencia: comparar condiciones/presupuesto, ablación, sensibilidad, holdout. Añadir mecanismo solo para requisito incumplido o mejora relevante con coste aceptable.
- Auditoría: hipótesis, evidencias, sesgos, desviaciones, criterios, alineación, alternativas y coste de oportunidad; niveles documental, estático, upstream ejecutado, contraste propio, réplica. Decidir avanzar/corregir/replantear/pausar/cerrar; separar auditor si viable, declarar autoevaluación.

## Integridad y recursos
Guardar protocolo, config, código, logs, resultados y hash/enlace de artefactos. CPU/gratuito primero; pruebas pequeñas; revisar licencia, scripts y dependencias antes de ejecutar código externo. Recursos pagos, cambios sustantivos, integraciones, borrados/permisos requieren aprobación. No guardar secretos. Si no puede ejecutar, registrar bloqueo. STATE canónico, STATUS derivado. Preferir commit atómico con evidencia y estado final; si escritura parcial, no avanzar STATE, reconciliar por diff/HEAD antes de continuar.
