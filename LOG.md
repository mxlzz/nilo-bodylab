# Bitácora

## INIT-001 — 2026-11-25
Usuario aprobó reformulación de corporalidad como fundamento de existencia y bifurcación P/X (D001). Se revisaron cuatro archivos iniciales, coordinación y auditoría externa Nilo; se conserva historial con base b45bb3c0c46b8a16852314feeb5050d9d8af8fb1. Se incorpora inventario preliminar y verificación documental selectiva (RESEARCH.md), plan, metodología, reglas y estado. No se seleccionó tecnología ni ejecutó experimento. E0.01 pendiente; antecedentes no cerrados. Publicación se comprueba por commit y lectura posterior, no auditoría independiente.

## E0.01 — 2026-11-25
Matriz R1–R7 y protocolo de búsqueda en evidence/E0.01.md. Recuperados coordinación, D001 y resultados de auditoría central; sin repetir ensayos. Aceptación documental propia 7/7, sin revisión independiente; no búsqueda nueva, selección técnica ni experimentos. Límites de búsqueda operativos fijados antes del cribado. G0 abierto; próxima E0.02. Base e26c9fdac237698205f0759de2faf10e9dad2071.

## E0.02 — 2026-11-25
Revisión dirigida de literatura: 12 consultas preregistradas y complementarias, fuentes y exclusiones en evidence/E0.02.md; actualiza RESEARCH. DEB como referencia, A0 conservativo vs A1 mínimo como contraste a resolver; NicheMapR para E2. Ronda de citas parcial y fallos de acceso declarados, no revisión sistemática. Aceptación documental propia suficiente para E0.03; no experimentos, coste pago ni selección de tecnología. Base a0eb513e3479b12f5026c07e5488d074dc144030.

## E0.03 — 2026-11-25
Cribado técnico de DEBtool, NicheMapR, PyDEB, COPASI, SciPy y balances mínimos; SHA/licencias raíz, dependencias, lectura estática, riesgos de clipping y comportamiento, disponibilidad y costes cualitativos registrados en evidence/E0.03.md. Sin ejecución, instalación, coste pago ni integración. Familias de gates posteriores diferidas, no excluidas. Aceptación documental propia; G0 abierto, próxima E0.04. Base 20804d36f4685a1771c12b237c01b2c62f5ac17d.

## E0.04 — 2026-11-25
Scoped minimum balance comparison selected; no integration or execution. Evidencia: evidence/E0.04.md. Próxima E0.05. Base b93cf62539766dd0d775acc485c24752fc28e1fd.

## E0.05 — 2026-11-25
Conditional external example reproduction not warranted; analytical reference derived; no execution. Evidencia: evidence/E0.05.md. Próxima E0.06. Base 355b03d81cc3c3502fd508901e9b4d5081593a9f.

## E0.06 — 2026-11-25
Preregistro E1-01 y config congelada; sin implementación ni ejecución. Próxima auditoría G0. Base 7fc390c7f7d473790d50b50d9fd0d94e4978ad19.

## E0.07 / G0 — 2026-11-25
Autoauditoría G0, avanzar a E1-01 con alcance sintético y protocolo congelado. Sin experimento todavía, sin autorización de integración. Base 55b2d9e6eb31d93d114933e88eaa7d23b22c4f55.

## E1-01 implementación — 2026-11-25
Código experimental propio y evaluador analítico congelados antes de ejecución, sin dependencias externas. Próximo ejecutar. Base 8c396a919638e74cf3c04eb9ec84f742a15a7e93.

## E1-01 ejecución — 2026-11-25
70 corridas; 10/10 controles; H1 condicional; primer timeout sin resultado, segunda ejecución sin cambios de modelo exit 0. Salida íntegra gzip y resumen, hashes y limitaciones en evidence/E1-01.md. Próximo G1. Base 5d0a53813ae90b2841121cd0d0f7e52d2d520437.

## G1 — 2026-11-25
Autoauditoría G1 superada con alcance sintético limitado. Conservar A0 y candidato A1 opcional; abrir E2. Sin integración. Base 27e600d6dce2ec952337c46ca1055c00902f7abf.

## E2.01 — 2026-11-25
Criba dirigida térmica/hídrica, NicheMapR fuente fijada; secuencia E2 acotada y omisiones explícitas. Próxima E2-T01 preregistro. Base 828854a774cbfa6dcdc982c5d9b4714e943e620b.

## E2-T01 preregistro — 2026-11-25
Contraste capacidad térmica vs equilibrio, calor de E1, controles y tolerancias congelados. No ejecución. Base fee060f46210bf06432d47b3d032b96fc0da5a2c.

## E2-T01 implementación — 2026-11-25
Código congelado, referencia analítica separada, E1 reutilizado sin modificar. Sin ejecución. Base 1844f9f858989cddfd3301cc527f6b6a24eaa736.

## E2-T01 enmienda previa 01 — 2026-11-25
Control activity: deducción algebraica detecta que el tramo de reposo original seguiría calentando; mantenimiento 0.05 en tramo 2. Enmienda explícita, sin ejecución ni cambio de criterios/código. Base 53692d26df805e004842e86a94febef98ff54a9e.

## E2-T01 ejecución — 2026-11-25
80 corridas, 13 controles/3 condiciones H1 superados; resultado condicional. Salida exacta gzip, resumen, fuente/config verificados, limitaciones en evidence/E2-T01.md. Base 5f9d0a4113e09d120e3be10b5d0043d459eecb98. Próxima revisión; G2 abierto.

## E2-T01 revisión — 2026-11-25
Resultado verificado y aceptado para nodo térmico sintético; T0 control de equilibrio válido, T1 candidato, sin retroacción fisiológica. Próxima E2.03. Base 5220177c7692db21a4f06dea5f31689429e7c6ef.

## E2.03 / E2-W01 preregistro — 2026-11-25
Criba hídrica, contraste de fase acotado; protocolo y configuración congelados sin código/ejecución. Base 4a92fc9497b2cb4d8a7ce3ab4624471f439b97a5.

## E2-W01 implementación — 2026-11-25
Código y referencia analítica congelados antes de ejecución. E1 reutilizado sin modificación. Base 1b3b1e79a638b2eaa16783fbf45924bb40a2399a.

## E2-W01 corrección previa — 2026-11-25
Inspección previa detectó denominador de residual combustible incluía soporte seco. Se corrige a max(1,combustible inicial), como exige protocolo. Sin corrida ni cambio de criterio. Base 2cdabacd85126296a828e643f3ed474f48041e6f.

## E2-W01 ejecución — 2026-11-25
70 corridas, 14/14 controles; evidencia, salida exacta comprimida y resumen. Próxima revisión; G2 abierto. Base d80b968337206e21adb57193ba19c14ff1249e87.

## E2-W01 revisión — 2026-11-25
Salida y evidencia verificadas; aceptación condicional a balance de fase, no regulación ni sed. Próximo E2.04, G2 abierto. Base f2ee1d1337a2073dbf59cd47905a9e34e8b29cd7.

## E2.04 / E2-F01 preregistro — 2026-11-25
Criba de mecanismos y preregistro electrotérmico. No motor elegido, daño/reparación diferidos por ausencia de mecanismo material, sin ejecución. Base 383af87944f56e991051fab148f407c703a51553.

## E2-F01 implementación — 2026-11-25
Fuente y referencia analítica/RK4 congeladas antes de ejecutar. Base eca658736ca2fbb3618d28a2169927edc2ca8719.

## E2-F01 ejecución — 2026-11-25
60 corridas, nueve controles, H1 condicional; salida íntegra y evidencia. DNS de descarga falló, hashes verificados por copia local. G2 abierto. Base 316b0ccb3799b20068ab9fcc81af93ca936f2af4.

## E2-F01 revisión — 2026-11-25
Readback verificado, límite electrotérmico aceptado condicionalmente, sin contador adicional de fatiga. Potencia potencial distinta de efectiva; daño/reparación diferidos. Próximo E2.05; G2 abierto. Base 7fce0a142d8711c59da7c307f8ffe11aedd1511e.

## E2-C01 preregistro — 2026-11-25
Contraste factorial de mecanismos existentes, referencia analítica/RK4, escenarios y criterios congelados. Sin ejecución. Base cb2466e1aed30cd57d080c287e0a9e929c3d96cc.

## E2-C01 implementación — 2026-11-25
Fuente y referencia congeladas antes de ejecución. Base 7c7ddc2194ebac465f4481a32ed9e242a6b70306.

## E2-C01 ejecución — 2026-11-25
80 corridas, 9/9 criterios, interacción factorial 6.052 J; no mejora de eficiencia, consumo mayor. Salida íntegra xz, hashes y límites. E2.05 concluida como contraste; próxima auditoría G2, aún abierto. Base fc0349667f672cf31aed8e63601ac99c9d637217.

## G2 — 2026-11-25
Autoauditoría de E2, 45/45 controles de cuatro contrastes sintéticos según resúmenes verificados, interacción condicional sin ganancia de eficiencia. G2 superado con alcance limitado; E3.01 cribado físico abierto. No se declara fisiología completa. Cabecera ROADMAP actualizada para referir STATE; sin cambio de plan. Base add5cc55cd4ee057402d120e9a569d12b66cbe3f.

## E3.01 — 2026-11-25
Cribado de cuatro motores y referencia analítica, secuencia E3 y requisitos de G3. MuJoCo candidato provisional; ningún motor instalado ni ejecutado, red local sin resolución DNS. Próximo E3.02 preregistro de banco mecánico, no integración. Base 5ed5ae05ab0cd5414273fa65554847e565417aac.

## E3-M01 preregistro — 2026-11-25
Banco mecánico restringido, frontera, controles, referencia y criterios congelados antes de implementación. Sin elección de motor ni ejecución. Base 75a04704ea6db816e6a4e67d04966166c1389201.

## E3-M01 implementación — 2026-11-25
Fuente y referencia por segmentos congeladas antes de ejecución; sin dependencias externas. Base b4118eee186d81eb4d6d265e1ca69e4e1370da6b.

## E3-M01 ejecución — 2026-11-25
40 corridas, 9/9 criterios, salida íntegra gzip y evidencia con hashes. Fallo DNS, copia local exacta verificada; exit 0. Próxima revisión, G3 abierto. Base 5ce19e1ffb21eb5ebe20095baefac9722b2c0b17.

## E3-M01 revisión / E3.03 preflight — 2026-11-25
Referencia revisada y readback verificado. Canal local de descarga falló; se documentan wheel oficial, runner gratuito y preflight sin ejecución de motor. Base fc8b440153198259001e04bb66eea87bcafe94c3.

## E3.03 — workflow de acceso — 2026-11-25
Preflight sin instalar/importar motor, runner estándar público, timeout 3 min, sin secretos ni acciones de terceros. Resultado pendiente. Base c4579b41f7cfc1e78b7856aa541a314fbbb78a1f.

## E3.03 acceso — 2026-11-25
Run 45647156945 success, hash wheel y metadata verificados en job 139321109993. Runner Python 3.12.3; usar wheel compatible, sin instalación aún. Próximo preregistro de contraste; G3 abierto. Base 76933a133e9767f20f79c5fa176f19a91e1820a8.

## E3-M02 preregistro — 2026-11-25
Contraste de MuJoCo headless contra referencia M01 en dominio compartido, contacto blando diferenciado, hashes de wheels y criterios congelados. Sin instalación ni ejecución. Base 06db4d59e1c84c0b5d8db3949f46b6afddcbe087.

## E3-M02 implementación — 2026-11-25
Fuente propia congelada, separación de contacto blando y referencia rígida; no ejecución. Base 3505df0f8057c65b0b09a8362a239011b1f5c2dd.

## E3-M02 disparo CI — 2026-11-25
Workflow de contraste acotado, runner público estándar, dependencias hash-pinned, inspección previa y venv offline. Pendiente confirmar ejecución. Base 464a66ed177b91bcadf718af0291bdb6c17401f7.

## E3-M02 resultado negativo — 2026-11-25
Run 45647841518, exit 1 por C2: residual energía contacto supera umbrales. 24 corridas, 6/7 criterios, datos íntegros y hashes preservados. No motor aceptado; próxima revisión. Base e9cdc727fbd2fdfd410aebace9aa392f0cc5864d.
