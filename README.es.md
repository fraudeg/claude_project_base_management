# project-base

[English](README.md) · Español

Un plugin de Claude Code que le da a un repositorio una configuración de Claude ligera y duradera: proyectos con memoria persistente, agentes baratos y enfocados, reglas que solo se cargan cuando aplican, checkpoints para que otra sesión retome una tarea, y una forma de medir lo que cuesta el trabajo. Siembra un repositorio vacío con toda la estructura en un solo comando, o audita uno existente y obtén un proyecto de adopción que mide dónde está y qué cambiar.

Empaqueta la forma de trabajar de un desarrollador para que cualquiera pueda adoptarla. Trae plantillas y los procedimientos para rellenarlas, nunca conocimiento ya escrito de ningún producto.

## Instalación

```text
/plugin marketplace add fraudeg/claude_project_base_management
/plugin install project-base@project-base
```

## Seed o audit

| | `/project-base:seed` | `/project-base:audit` |
|---|---|---|
| Para | un repositorio vacío o nuevo | un repositorio existente |
| Hace | escribe toda la estructura (ver abajo) y solo pregunta lo que no puede deducir: nombre del proyecto, propósito, lenguaje y comando de tests | se orienta, mide la configuración actual de Claude y encuentra qué cambiar |
| Escribe | `CLAUDE.md`, `.claude/`, `docs/` y un primer proyecto `docs/projects/<fecha>-bootstrap/` | solo `docs/projects/<fecha>-adopt-project-base/`: README, decisiones, log con la línea base y un plan con una tarea pequeña por cambio |
| Nunca | sobrescribe: se detiene si ya existe `CLAUDE.md`, `.claude/agents/` o `docs/projects/`, y te manda a audit | edita, reformatea ni mueve tu `CLAUDE.md`, docs, código, `.claude/` ni settings |

Si hay un grafo de graphify (`graphify-out/`), el audit lo lee, pero nunca lo construye ni lo necesita. Te pide que pegues la salida de `/usage` y `/context` (Claude no puede ejecutarlos) y la guarda como línea base. Ejecutar el plan es trabajo normal de proyecto: una tarea cada vez, a través de los agentes y con tu aprobación. La adopción es el primer proyecto del repositorio, así que aprendes el sistema usándolo.

## Checkpoint y measure

- `/project-base:checkpoint` crea o actualiza `docs/projects/<proyecto>/tasks/NNN-<slug>.md` para una tarea que no cupo en una sesión. El archivo lleva una línea `Status:` (`in-progress`, `blocked` o `done`), el objetivo, lo hecho hasta ahora, los archivos tocados, el siguiente paso exacto, cómo verificar y las preguntas abiertas. Una sesión o un agente nuevo retoma la tarea solo con ese archivo. Las tareas pequeñas se quedan como una línea en `plan.md`.
- Un hook lista las tareas abiertas en dos momentos:
  - Al compactar el contexto: el resumen le dice a la sesión retomada que las actualice.
  - Al terminar la sesión: te las muestra a ti.
- `/project-base:measure` recibe un nuevo pegado de `/usage` y `/context`, lo guarda literal en el `log.md` del proyecto y escribe una tabla corta de antes/después contra la línea base.

## Qué se instala

El plugin trae las skills, los hooks y los agentes originales. Seed copia el resto a tu repositorio, donde es tuyo y lo editas:

- `CLAUDE.md`: un esqueleto corto (menos de 200 líneas) con los comandos, las convenciones, la escala de criticidad y las reglas para trabajar con agentes.
- `.claude/agents/`: `explorer`, `implementer`, `test-runner` y `reviewer`. Todos usan `model: sonnet`; `explorer` y `test-runner` no cargan `CLAUDE.md`.
- `.claude/rules/`: una regla de ejemplo con `paths:` y un README sobre cuándo añadir una.
- `.claude/settings.json`: `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, más superpowers, ponytail y este plugin recomendados a cada colaborador. Si el archivo ya existe, solo se añaden claves, después de mostrarte el diff.
- `docs/`: el mapa, el flujo de proyectos, y los ADRs y topic cards con sus plantillas.
- `.claude/project-base.json`, que leen los hooks y los agentes:

  | Clave | Significado |
  |---|---|
  | `test_command` | el comando de tests del proyecto, que usa `test-runner` |
  | `test_command_patterns` | las regex que el hook de recorte compara con cada comando Bash. **Actualízalas siempre que cambies el comando de tests**, o el recorte deja de funcionar sin avisar |
  | `docs_root` | dónde viven los docs; por defecto `docs` |

Hooks que trae el plugin:

- **Recorte de salida de tests** (PreToolUse sobre Bash): cuando el comando coincide con `test_command_patterns`, se queda con las últimas 100 líneas y con el exit code. Sin archivo de configuración, unos patrones por defecto cubren los runners comunes.
- **Recordatorio de checkpoint** (PreCompact y SessionEnd): lista cada archivo de tarea con `Status: in-progress`. En PreCompact la lista entra en el resumen de compactación; en SessionEnd se te muestra a ti, porque Claude ya no puede actuar.

Las skills de conocimiento se cargan bajo demanda: `project-workflow`, `write-adr`, `write-topic-card`, `write-rule`, `criticality-gate` y `harness-ops`.

## Por qué: un caso real

El método viene de un harness en producción sobre un repositorio backend grande. Allí el límite semanal de uso se agotaba sobre todo por dos cosas:

- subagentes que heredaban el modelo más caro: el 61 % del uso;
- un `CLAUDE.md` de 67 KB que recargaba cada agente.

El harness redujo las instrucciones que se cargan siempre de 67 KB a 16 KB y pasó los subagentes a un modelo más barato, con benchmarks casi iguales. Este plugin es esa configuración sin el producto; del original solo quedan porcentajes y tamaños.

## Plugins recomendados

Seed recomienda dos plugins a cada colaborador del repositorio. El mérito es de sus autores: este plugin los complementa, no los sustituye.

- [superpowers](https://github.com/obra/superpowers), de Jesse Vincent: las skills de proceso (brainstorming, planes, TDD, ejecución con subagentes y revisión). El `CLAUDE.md` sembrado les dice a sus skills de subagentes que despachen los agentes del proyecto en vez de `general-purpose`.
- [ponytail](https://github.com/DietrichGebert/ponytail), de Dietrich Gebert: mantiene el código pequeño, con la librería estándar primero y sin abstracciones especulativas.

## Límites conocidos

- El hook de recorte se queda con las últimas 100 líneas, así que un fallo al principio de una ejecución muy larga puede quedar fuera de la salida.
- Los comandos encadenados o compuestos (`a && b`, pipes, redirecciones, `;`, backticks, `$(...)`) nunca se recortan; solo se reescribe una invocación simple.
- Un `test_command_patterns` sembrado reemplaza los patrones por defecto: solo se recorta la forma exacta del comando sembrado (con los argumentos que vengan detrás). Añade un patrón por cada variante que uses, por ejemplo `pytest ...` junto a `python3 -m pytest ...`.
- Probado en vivo el 2026-11-15 (Claude Code 2.1.325, `sonnet`): la reescritura se aplicó tanto con `--permission-mode auto` como en modo por defecto con `Bash` permitido. En ambas ejecuciones el modelo vio 100 de 216 líneas y se conservó el exit code (1). Los demás modos de permisos no se probaron.
- El hook reescribe el comando de tests (le añade `tail` y `pipefail`), así que puede dejar de coincidir con una regla de permisos escrita para el comando original.
- Un `docs_root` distinto de `docs` solo lo respetan los hooks y los agentes. Seed escribe bajo `docs/` y las skills usan esa ruta.
- Para mantenedores: `python3 scripts/check_neutral.py .` revisa que no aparezcan nombres prohibidos. Los nombres van en un archivo `.neutral-denylist` en la raíz, ignorado por git (uno por línea, se permiten comentarios con `#`), y nunca se commitean. Sin términos, el check solo avisa y sale con 0.
- Los tests unitarios corren en cualquier sitio (`python3 -m unittest discover -s tests`). Los smoke tests (`tests/smoke_seed.sh` y `tests/smoke_audit.sh`) llaman a `claude`, necesitan una cuenta que pueda usar `--permission-mode auto` y tienen coste.

## Contribuir

Se aceptan issues y comentarios; los pull requests están limitados a colaboradores. Ver [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

MIT, copyright FraudEG.
