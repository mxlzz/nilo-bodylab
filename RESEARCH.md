# Antecedentes — inventario de partida E0

2026-11-25. Revisión preliminar recuperada del diseño y verificación documental selectiva de fuentes primarias/documentación. No revisión sistemática cerrada, prueba local ni auditoría de licencias/versiones de estos candidatos. E0.01 registra estrategia de búsqueda, E0.02/03 amplían y verifican.

| Referencia documental | Aporte | Límite |
|---|---|---|
| [DEB portal](https://debportal.debtheory.org/docs/) | reservas, asimilación, mantenimiento, desarrollo; DEBtool | parametrización biológica; no asumir especie |
| [Kearney y Porter, NicheMapR](https://doi.org/10.1111/ecog.04680), [tutorial DEB](https://mrke.github.io/NicheMapR/inst/doc/deb-model-tutorial.html) | acoplamiento calor, agua, energía, nutrición y ciclo vital | ecofisiología terrestre, no agente artificial |
| [Grand et al. Creatures 1997](https://eem.foo/ccarchive/Sites/fp.cyberlifersrch.plus.com/articles/agents_%2797_paper.htm) | bioquímica artificial y modulación hormonal | no asumir conservación física ni importar conducta |
| [Keramati y Gutkin 2014](https://elifesciences.org/articles/04811) | estado interno y motivación | recompensa no requisito de BodyLab |
| [MuJoCo](https://mujoco.readthedocs.io/en/stable/overview.html) | mecánica, contactos y sensores | no fisiología; comparar alternativas simples |
| [MyoSuite](https://github.com/MyoHub/myosuite) | músculo, fatiga, acoplamiento motor | anatomía/tareas específicas; no adoptar RL por defecto |
| [Sims 1994](https://doi.org/10.1145/192161.192167) | evolución de morfología y controlador | selección generacional, no prueba ontogenética |
| [Kriegman et al. 2018](https://www.nature.com/articles/s41598-018-31868-7) | cambios morfológicos durante vida de robots blandos | desarrollo fijado por optimización evolutiva |
| [Biomaker CA](https://google-research.github.io/self-organising-systems/2023/biomaker-ca/) | desarrollo tipo vegetal con nutrientes/reglas locales | no acredita actuación animal ni organismo integral |
| [Flow-Lenia](https://research.google/pubs/flow-lenia-towards-open-ended-evolution-in-cellular-automata-through-mass-conservation-and-parameter-localization/) | autómata continuo conservativo de masa | conservación no equivale a metabolismo/agencia |

## Inventario adicional a verificar (no adopción)
Bioenergética: Add-my-Pet, JOS-3, pythermalcomfort, nicho termodinámico, sistemas abiertos. Vida artificial: openc2e, Chreatures, ALIEN, Framsticks, Polyworld, Stringmol, Genesis Engine (identidad exacta a verificar), autopoiesis/protocélulas. Fisiología humana: Pulse, BioGears, HumMod, Physiolibrary (Modelica); probablemente demasiado específicos para adoptar enteros. Mecánica: Box2D, OpenSim, OpenWorm/Sibernetic; Voxelyze y EvoGym como candidatos adicionales de cuerpos blandos/voxel. Bioquímica/composición: COPASI, Tellurium, Vivarium, COBRApy; evaluar si flujos sencillos no bastan. Conceptual: Di Paolo, autopoiesis/adaptividad, interocepción, alostasis, plasticidad y morfogénesis. Nilo histórico como baseline conceptual, no obligación de reactivar.

## Antecedentes internos recuperados
[Auditoría externa Nilo 24/11](https://github.com/mxlzz/Nilo_public/blob/main/docs/AUDITORIA_DESARROLLOS_EXTERNOS_2026-11-24.md) y [coordinación](https://github.com/mxlzz/Nilo_public/blob/main/docs/PROGRAMA_INVESTIGACION_NILO.md). CYMONIA: pruebas upstream y defectos adversariales de contención agregada y frontera observacional; Bigville: divergencia de restauración corregida en ensayo al igualar modos; MineWorld: pruebas de kernel/contratos; Chreatures: lectura y recibos sin reproducción independiente. Consultar alcance exacto en auditoría. No importar reflejos obligatorios, testigos privilegiados ni motores completos. No repetir campañas cerradas.

## Decisión provisional
No se ha comprobado solución integral para todos los requisitos. Comparar DEB/NicheMapR con balances mínimos y bioquímica artificial; mecánica sencilla vs MuJoCo/Box2D, fatiga dirigida si necesaria; morfogénesis abierta X condicional. No privilegiar stack. En E0 comparar madurez, licencia, versión, dependencias, coste, evidencia, compatibilidad y encaje R1–R7. Las consultas de inicialización fueron dirigidas a DEB/NicheMapR, Creatures, homeostatic RL, MuJoCo, Sims, desarrollo morfológico, Biomaker CA, Flow-Lenia y MyoSuite. Sin exhaustividad ni lectura íntegra acreditadas. Registrar búsqueda por fecha, consulta, fuente, inclusión/exclusión y nivel de evidencia.
