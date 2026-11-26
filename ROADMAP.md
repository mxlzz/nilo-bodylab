# Plan auditable — aprobado 2026-11-25

Se conserva E0.01 del scaffold original (H0.01 en propuesta de chat). E0 se amplía; E1–E3 originales se refinan. La fase activa y los gates se consultan en STATE.json, fuente canónica. Las fases posteriores son condicionales: ningún protocolo, motor ni tecnología aprobado por anticipado.

| Hito | Dependencia | Resultado y aceptación del gate |
|---|---|---|
| E0 antecedentes y selección | Ninguna | Inventario trazable, requisitos y brechas; alternativas, licencias/versiones/coste de finalistas y protocolo E1 preregistrado. G0 antes de ejecución. |
| E1 bioenergética mínima | G0 | A0 vs candidato de flujos; balances, convergencia, perturbación/recuperación y coste contrastados. G1 decide qué conservar. |
| E2 regulación y límites | G1 | Solo mecanismos necesarios (agua, nutrición, temperatura, fatiga/daño/recuperación según evidencia); perturbaciones combinadas, sin recursos creados ni correcciones ocultas. G2. |
| E3 cuerpo físico fijo | G1,G2 (orden ajustable con razón) | Geometría sencilla, contactos, sensores, actuación y trabajo acoplados; controlador intercambiable, sin acceso privilegiado; balance y replay. G3 valida base común o reformula/cierra. |
| P1 desarrollo condicionado | G3 | Plan corporal parcial vs fijo en condiciones y presupuesto comparables; cambios dentro de una vida por historia/recursos, efecto funcional y coste. G-P1. |
| P2 ciclo vital y robustez | G-P1 | Desarrollo, envejecimiento y muerte cuando pertinentes; escenarios reservados, sensibilidad, ablación y transferencia entre sustitutos; mecanismo mínimo y límites. G-P2. |
| X1 factibilidad morfogénesis abierta | G3 y oportunidad justificada | Pregunta independiente y recurso acotado; comparar modelos locales/celulares/estructurales existentes; no confundir patrón emergente con organismo funcional. G-X1 puede cerrar sin ejecución. |
| X2 contraste abierto | G-X1 | Formación/reorganización dentro de una vida, coste material y continuidad funcional, comparación con fijo y/o P en condiciones equivalentes. G-X2 decide continuar, transferir mecanismo o cerrar. |
| F síntesis | P2 o cierre justificado de P | Dictamen de suficiencia, limitaciones y transferibilidad. X no bloquea P ni F; integrar con Nilo requiere gate/aprobación externos. |

Cada gate requiere auditoría en audits/ y criterio cuantitativo preregistrado por ensayo. No escalar si modelo simple satisface requisitos. Unidades verificables, sucesivas si el usuario solicita y no hay dependencia pendiente. No iniciar campañas paralelas con escrituras conflictivas.

## E0 — tareas
- **E0.01 (siguiente)**: leer objetivo, D001, RESEARCH y auditoría externa Nilo enlazada; matriz R1–R7 → observable → evidencia de referencia → falsificador → exclusión; definir consultas reproducibles, fuentes, inclusión/exclusión y límites antes de búsqueda adicional. Entregable evidence/E0.01.md. Aceptación: cada R tiene observable y falsificador o incertidumbre explícita; cribado y registro de búsqueda definidos; antecedentes internos recuperados sin duplicar auditoría. No seleccionar motor ni escribir simulador. Guardar LOG/STATE/STATUS. Siguiente E0.02.
- E0.02: revisión científica dirigida y búsqueda por citas; extender RESEARCH con fuentes originales, alcance, resultados, brechas y contraejemplos. Aceptación: referencias primarias de finalistas, límites y preguntas abiertas.
- E0.03: cribado técnico (código, licencias por componente, versiones/commits, dependencias, mantenimiento, coste y evidencia). Aceptación: matriz comparable, inaccesibles explícitos, no copiar sin permiso.
- E0.04: comparar adoptar/adaptar/combinar/desarrollar mínimo/cerrar por R1–R7 y coste. Aceptación: decisión fundamentada, descartes y dudas discriminantes.
- E0.05: reproducir únicamente ejemplos mínimos de finalistas si necesario y seguro, con preregistro y controles. Aceptación: resultado verificable o bloqueo con recuperación, sin afirmar validación integral.
- E0.06: protocolo E1: baseline A0, alternativa justificada, fronteras, unidades, ecuaciones, escenarios, métricas/tolerancias, coste, convergencia/replay, condiciones de rechazo. Aceptación: preregistro auditable sin umbrales post hoc.
- E0.07: G0 audita trazabilidad y adecuación; decidir avanzar/corregir/replantear/pausar/cerrar. Aceptación: auditoría registrada, protocolo apto según coordinación Nilo. Respetar gates y solicitar autorización ante cambios sustantivos o costes pagos.

## Hipótesis candidatas, no resultados
H-common: flujos acoplados mejoran coherencia causal frente a indicadores independientes. H-P: plasticidad histórica aporta cambio funcional útil sin coste desproporcionado frente a fijo. H-X: organización abierta puede mantener estructuras funcionales sin anatomía final prescrita. Reformular con E0 antes de ensayar; ninguna confirmación obligatoria.

## E2 — secuencia operativa (2026-11-25, posterior a G1)
Ver evidence/E2.01.md. E2.01 cribado; E2.02 capacidad térmica y balance acoplado E1 (preregistro, implementación, ejecución); E2.03 criba y contraste agua/calor si justificado; E2.04 límites funcionales, daño/reparación si causalmente definidos; E2.05 contraste conjunto y G2. Cada ensayo requiere preregistro propio; diferir mecanismos con razón y no reclamar validación integral. Sin cambio de objetivo ni arquitectura. 

## E3 — secuencia operativa (2026-11-25, posterior a G2)
Ver [evidence/E3.01.md](evidence/E3.01.md). E3.01 cribado; E3.02 referencia mecánica restringida con cuerpo finito, reacción, contacto y ledger; E3.03 comparación de motor reutilizable cuando acceso/licencias/recursos verificados; E3.04 cuerpo fijo situado y frontera sensorial/material; E3.05 perturbación material y disposición de daño/reparación; G3 auditoría de suficiencia para P/X. Cada ensayo preregistrado; no seleccionar motor por anticipado ni confundir referencia guiada con cuerpo completo. Bloqueo de acceso externo solo afecta unidades dependientes; no afirmar contraste realizado si falta. Criterios de gate y tolerancias por ensayo en evidencia/protocolos.

## E3.06 — corrección G3 (2026-11-26)

Dictamen [G3 inicial](audits/G3.md): E3.01–05 completas en alcance restringido; G3 no superado. Contraste conjunto acotado de cuerpo fijo: reserva compartida, locomoción situada, deterioro y reparación material, acceso local, historia sin reset, balances, frontera sensorial, referencia y replay. Cribado → preregistro → implementación → ejecución → revisión → reevaluación G3. Térmica/hídrica solo con causalidad compatible y pregunta discriminante; justificar exclusiones. No abrir P/X antes de dictamen, no agregar requisitos de anatomía, integración, muerte global ni fisiología exhaustiva. 

## P1 — continuidad tras G3 (2026-11-26)

[G3 reevaluado](audits/G3-recheck.md): base fija C02 suficiente en dominio restringido. P1 inicia con cribado de desarrollo individual y plasticidad física, luego preregistro, implementación, ejecución, revisión y G-P1. Fijo conserva reparación, recursos y costes equivalentes; distinguir reparación de cambio funcional por historia. Evaluar crecimiento/redistribución con materia, energía y mecánica explícitas, sin asumir anatomía final ni utilidad adaptativa. X elegible solo por oportunidad justificada y acotada, no bloqueante.
