# Revisión E3-M03 y disposición de E3.03

2026-11-25. Autoevaluación, no auditoría independiente. Evidencia congelada en d635809dffffe0f59b4f262393d3899551a25ccb; lectura de results.json idéntica byte a byte al registro RESULT_JSON del job 139324985832 (con LF final). SHA256 comunicado por ejecución en summary.json, no recalculado independientemente aquí. Primer intento de persistencia devolvió error de API GraphQL; HEAD intacto, reintento exitoso y lectura posterior verificada.

## Decisión

**E3.03 completada para el dominio restringido; MuJoCo 4.0.1 es candidato provisional para contrastes E3.04, no motor definitivo.** M02 permanece rechazado (C2); M03 supera C1–C7 y D1 (24 corridas, 266000 pasos). No se cambiaron ecuaciones, casos ni tolerancias, ni se compensó el residual. El refinamiento de dt x8 reduce el máximo fino de 0.2650156709 a 0.0313349711 J (factor 8.46), dentro del umbral preexistente de 0.05 J. El error de la identidad diagnóstica es 1.44e-12 J; en este dominio el defecto de trabajo corresponde a discretización Euler semiimplícita, no a pérdida física o calor. El replay exacto incluye contacto activo. La ejecución costó 3.066 s y 61.38 MiB RSS para el conjunto de pruebas frente a 0.394 s y 59.48 MiB en M02 (aprox. 7.8 veces más tiempo); no se extrapola rendimiento a escenas generales.

Alternativas: la referencia M01 por eventos sigue siendo baseline válido de un eje y choque ideal; no constituye motor general. Mantener la evaluación previa E3.01 de Box2D/Pymunk/Rapier como alternativas si contacto multiaxial, coste o frontera sensorial invalidan candidato. No se ejecutaron dichos motores; no se afirma superioridad comparativa. Evitar sustituir contabilidad de trabajo medido por cuadratura que cierre identidad algebraicamente. No perseguir refinamientos indefinidos: contrastar coste y resolución para nueva geometría y condiciones reservadas.

Límites: ensayos diagnósticos sobre casos ya conocidos, no validación independiente; máximo de penetración 0.01478 m frente al radio 0.25 m, contacto blando y soporte guiado ideal. No demuestra desplazamiento libre, intercambio de momento en entorno finito, percepción local, captación de recursos, perturbación material, autonomía ni fisiología empírica. El acceso local falló por DNS; runner público estándar permitido, sin cambios de configuración de repositorio ni pago. No se integra con otros labs.

## Próxima unidad

E3.04: cribado de cuerpo fijo situado, mecanismo mínimo de acción con reacción ambiental explícita, sensores locales, intercambio material solo por contacto/alcance definido, controlador experimental sustituible sin acceso privilegiado; comparar mecanismos/alternativas antes de preregistrar. No predeterminar anatomía o locomoción biológica. G3 abierto; E3.05 y su disposición de daño/reparación pendientes. Ningún cambio sustantivo ni intervención requerida.
