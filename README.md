# CompilScript

CompilScript es un compilador completo para un subconjunto de TypeScript con enfoque académico. La solución cubre cada fase del pipeline (análisis léxico/sintáctico, semántica, generación de código intermedio y backend MIPS) y expone ese pipeline a través de un servicio REST y un IDE web. Este README centraliza la documentación dispersa del repositorio, describe a detalle la arquitectura final y explica cómo recrear el entorno del proyecto.

---

## Tabla de contenido
1. [Visión general y objetivos](#visión-general-y-objetivos)
2. [Pila tecnológica](#pila-tecnológica)
3. [Mapa del repositorio](#mapa-del-repositorio)
4. [Flujo de compilación](#flujo-de-compilación)
5. [Requisitos previos](#requisitos-previos)
6. [Guía de preparación rápida](#guía-de-preparación-rápida)
7. [Modos de ejecución](#modos-de-ejecución)
8. [API `/analyze`](#api-analyze)
9. [Características del lenguaje](#características-del-lenguaje)
10. [Detalle de la implementación](#detalle-de-la-implementación)
11. [Artefactos generados](#artefactos-generados)
12. [Pruebas y aseguramiento de calidad](#pruebas-y-aseguramiento-de-calidad)
13. [Regenerar lexer/parser](#regenerar-lexerparser)
14. [Solución de problemas y preguntas frecuentes](#solución-de-problemas-y-preguntas-frecuentes)
15. [Recursos adicionales](#recursos-adicionales)

---

## Visión general y objetivos

- **Lenguaje objetivo**: CompilScript, un subset de TypeScript con tipado estático fuerte, clases, arreglos de N dimensiones y manejo de excepciones.
- **Pipeline completo**: Frontend (ANTLR + visitors en Python), representación intermedia (TAC) y backend (MIPS32 con optimizaciones).
- **Casos de uso**:
  - Validar código CompilScript desde CLI (`program/Driver.py`).
  - Exponer diagnósticos y artefactos vía un API REST (`program/server.py`).
  - Interactuar con el compilador desde un IDE React (`IDE-compiscript/`) que recrea la experiencia de laboratorio.
- **Objetivos académicos** (según los readmes originales):
  1. Aplicar técnicas modernas de análisis sintáctico y semántico.
  2. Construir tablas de símbolos con manejo jerárquico de scopes.
  3. Generar código intermedio con administración de temporales y registros de activación.
  4. Desarrollar una herramienta visual que consuma el compilador.
  5. Documentar arquitectura, lenguaje y pruebas para facilitar la evaluación.

## Pila tecnológica

| Capa                         | Tecnología / Biblioteca                                             |
|-----------------------------|---------------------------------------------------------------------|
| Lexer / parser              | [ANTLR 4.13.1](https://www.antlr.org/) (target Python, visitor-based) |
| Análisis / backend          | Python 3.12 (FastAPI, Pydantic, `antlr4-python3-runtime`, PyTest)    |
| Representación intermedia   | TAC propio con generadores modulares (`expression`, `control_flow`, `function`) |
| Backend assembler           | Traductor a MIPS32 + runtime personalizado + optimizador peephole    |
| Servicio HTTP               | FastAPI + Uvicorn + CORS abiertos                                    |
| IDE                         | React 19 + Vite 7 + `react-hot-toast` + `react-icons`                |
| Contenedorización opcional  | Docker + Uvicorn                                                     |

## Mapa del repositorio

```
.
├── program/
│   ├── AST/                        # Nodos, tabla de símbolos, exportadores DOT
│   ├── semantic/                   # Tipos, expresiones, sentencias, clases, helpers
│   ├── tac/                        # Generadores TAC + administradores de memoria
│   ├── mips/                       # Traductores a MIPS, optimizaciones y runtime
│   ├── tests/                      # PyTest, harness CLI y casos .cps
│   ├── Compiscript.g4 / .bnf       # Gramática
│   ├── Driver.py                   # CLI end-to-end
│   └── server.py                   # FastAPI (endpoint POST /analyze)
├── IDE-compiscript/                # IDE React + Vite
├── readmes/                        # Documentación histórica (semántica, TAC, tests, etc.)
├── Dockerfile                      # Imagen de referencia
├── README_RUN_PROJECT.md           # Guía breve enfocada en Docker
├── python-venv.sh                  # Script auxiliar para entornos POSIX
├── requirements.txt                # Dependencias Python
└── README.md                       # Este documento
```

## Flujo de compilación

1. **Lexer y Parser (ANTLR)**  
   - `CompiscriptLexer.py` y `CompiscriptParser.py` provienen de `Compiscript.g4`.  
   - El parser produce un árbol concreto que recorre `SemanticVisitor`.

2. **Análisis semántico**  
   - `AST/symbol_table.py` y `semantic/*` resuelven scopes, tipos, clases, control de flujo y excepciones.  
   - Se exportan `ast.dot` y `scopes.json`.

3. **Generación de TAC**  
   - `tac/integrated_generator.py` coordina generadores especializados:
     - `expression_generator` (expresiones, temporales, promoción de tipos).
     - `control_flow_generator` (if/switch/loops/try-catch).
     - `function_generator` (funciones libres, métodos, closures y registros de activación).
   - Se exponen estadísticas: temporales usados, etiquetas y funciones registradas.

4. **Anotación de memoria y símbolos**  
   - `tac.symbol_annotator.SymbolAnnotator` asigna offsets a variables globales, de stack y heap.

5. **Backend MIPS**  
   - `mips/integrated_mips_generator.py` consume `output.tac`, usa traductores específicos, asigna registros y ejecuta `peephole_optimizer`.  
   - Genera `output.s` listo para SPIM/MARS con runtime incluido.

6. **IDE / Servicio**  
   - El IDE envía código a `/analyze` y muestra diagnósticos, TAC, estadísticas y scopes.  
   - El servidor puede integrarse con otras herramientas externas.

## Requisitos previos

- **Python**: 3.12+ con `pip`.  
- **Node.js**: 20+ para ejecutar el IDE (opcional).  
- **Java**: 11+ si regeneras lexer/parser con ANTLR.  
- **Graphviz**: ejecutable `dot` para convertir `ast.dot` a PNG.  
- **Docker**: opcional, para aislar dependencias.  
- **Sistemas soportados**: Windows, macOS, Linux (probado principalmente en Windows + WSL).

## Guía de preparación rápida

```bash
# 1. Crear y activar entorno (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Alternativa Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias backend
pip install --upgrade pip
pip install -r requirements.txt

# 3. (Opcional) Dependencias del IDE
cd IDE-compiscript
npm install
```

> **Tip**: `python-venv.sh` automatiza la creación de entornos aislados dentro de contenedores evaluados en clase.

## Modos de ejecución

### 1. Driver CLI completo

```bash
python program/Driver.py program/program.cps
```

El driver ejecuta todo el pipeline y produce:

- `ast.dot` – AST en Graphviz.
- `output.tac` – código TAC con comentarios y estadísticas.
- `scopes.json` – tabla de símbolos anotada.
- `output.s` – ensamblador MIPS optimizado.

Fragmento típico:

```
V Semantic analysis completed successfully.
V AST -> ast.dot
--- TAC Generation ---
V Generated 132 TAC instructions
V TAC validation passed
--- TAC Statistics ---
  Functions registered: 6
  Temporaries used: 18
--- MIPS Generation ---
V MIPS -> output.s
```

### 2. Servicio REST (FastAPI + Uvicorn)

```bash
uvicorn program.server:app --host 0.0.0.0 --port 8000 --reload
```

Expone `POST /analyze`, con CORS abiertos para el IDE. Úsalo para integración con herramientas externas o el frontend React.

### 3. IDE web (React)

```bash
cd IDE-compiscript
npm run dev
```

Abrir `http://localhost:5173` (asegúrate de tener corriendo FastAPI). El IDE incluye:

- Editor custom (tabs convertidos, auto indentación, resaltado usando sentinelas Unicode).
- Panel de diagnósticos con líneas/columnas resaltadas y sincronizadas con las barras laterales.
- Vista de TAC + estadísticas de instrucciones, temporales y funciones.
- Toasts de éxito/error (`react-hot-toast`) y estado `isRunning`.

### 4. Docker (modo laboratorio)

```bash
docker build --rm . -t compiscript
docker run --rm -it -p 8000:8000 -v "%cd%/program":/program -w /program compiscript \
  uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

> En Linux/macOS reemplaza `"%cd%"` por `$(pwd)` y el `\` final por `&&`. Con esto el IDE o cualquier cliente HTTP puede conectarse al analizador dentro del contenedor.

## API `/analyze`

- **Método**: `POST`
- **Body**:

```json
{
  "code": "var x: integer = 1;",
  "return_ast_dot": true,
  "generate_tac": true
}
```

- **Respuesta**:

```json
{
  "ok": true,
  "diagnostics": [],
  "ast_dot": "digraph AST { ... }",
  "tac": {
    "code": [
      "# TAC Code Generation - CompilScript Compiler",
      "t0 = 1",
      "x = t0",
      "call print, 1",
      "..."
    ],
    "instruction_count": 42,
    "temporaries_used": 7,
    "functions_registered": 3,
    "validation_errors": []
  },
  "scopes": {
    "name": "global",
    "symbols": {
      "x": {
        "type": "integer",
        "address": "stack[0]",
        "mutable": true
      }
    },
    "children": []
  }
}
```

`diagnostics` puede contener errores léxicos, sintácticos, semánticos o de TAC/MIPS con campos `kind`, `message`, `line`, `column` y `length`. Los flags `return_ast_dot` y `generate_tac` son opcionales.

## Características del lenguaje

### Tipos soportados

- Primitivos: `integer`, `float`, `string`, `boolean`, `void`.
- Arreglos con notación `type[]` ilimitada (`integer[][]`).
- Clases definidas por el usuario con herencia simple.
- Literales especiales: `true`, `false`, `null`.

### Declaraciones y variables

```cps
var contador: integer = 0;
const PI: float = 3.1416;
var saludo = "hola";  // inferencia
```

- `const` exige inicialización inmediata.
- Inferencia disponible para `var` cuando el tipo se deduce del literal o expresión.

### Expresiones y operadores

- Aritmética: `+ - * / %` con promoción `integer -> float`.
- Lógica: `&& || !` estrictamente booleanas.
- Comparaciones: `== != < <= > >=`.
- Condicional ternario: `cond ? expr1 : expr2`.
- Acceso a propiedades y arreglos: `obj.campo`, `arr[i][j]`.
- Literal y acceso a arreglos multidimensionales.

### Control de flujo

```cps
if (cond) { ... } else { ... }
while (expr) { ... }
do { ... } while (expr);
for (var i: integer = 0; i < n; i = i + 1) { ... }
foreach (item in coleccion) { ... }
switch (valor) { case 1: ... default: ... }
break; continue; return expr?;
```

- Valida que `break/continue` existan solo dentro de bucles y `return` dentro de funciones.

### Funciones y closures

```cps
function suma(a: integer, b: integer): integer {
  return a + b;
}

function fabricaSaludo(nombre: string) {
  function interno() {
    print("Hola " + nombre);
  }
  return interno;
}
```

- Soporta recursión, funciones anidadas y captura léxica.
- `this` disponible dentro de métodos de clase con validación de contexto.

### Clases y objetos

```cps
class Animal {
  var nombre: string;
  function speak(): void {
    print(this.nombre);
  }
}

class Perro: Animal {
  function speak(): void {
    print(this.nombre + " dice guau");
  }
}

var dog: Perro = new Perro("Toby");
dog.speak();
```

- Constructor implícito si no existe.
- Herencia simple con verificación de overrides y compatibilidad de firmas.

### Manejo de errores

```cps
try {
  var peligro = lista[100];
} catch (err) {
  print("Error atrapado: " + err);
}
```

`catch` requiere un identificador y bloque válido; el analizador garantiza la forma correcta.

## Detalle de la implementación

### AST y tabla de símbolos (`program/AST/`)

- `nodes.py`: define nodos con metadata (tipos inferidos, valores literales, etc.).
- `symbol_table.py`: scopes anidados, detección de redeclaraciones, exportación a JSON y utilidades para anotaciones de memoria.
- `ast_to_dot.py`: genera Graphviz DOT con etiquetas claras (nombre del nodo, atributos y tipos).

### Módulos semánticos (`program/semantic/`)

- `types.py`: normaliza nombres de tipos y construye `TypeNode(base, dimensions)`.
- `expressions.py`: valida expresiones aritméticas, lógicas, arrays, `new`, `this`, `call`.
- `statements.py`: maneja declaraciones, asignaciones, loops, `try/catch`, `switch`, `break`, `continue`, `return`.
- `classes.py`: registra clases, verifica herencia, constructores, métodos y sobrescrituras.
- `helpers.py`: compatibilidad de tipos, coerciones y reportes de error.
- `state.py`: `SemanticState` centraliza `global_scope`, `current_scope`, pila de tipos de retorno y profundidades de loops/switch.

### Generación de TAC (`program/tac/`)

- Infraestructura: `temp_manager`, `label_manager`, `address_manager`.
- `expression_generator`: instrucciones para expresiones, llamadas, literales y arreglos.
- `control_flow_generator`: condicionales, loops, `switch`, `try/catch`, `break` y `continue`.
- `function_generator`: prólogos/epílogos, registros de activación, métodos de clase (nombres calificados `Clase_metodo`).
- `integrated_generator.py`: coordina generadores, registra funciones antes de visitarlas, expone estadísticas y validaciones (`validate_tac()`).
- `symbol_annotator`: enriquece la tabla de símbolos con offsets concretos (stack/heap/global).

Ejemplo TAC:

```
# TAC Code Generation - CompilScript Compiler
@function main
  t0 = 1
  x = t0
  param x
  call print, 1
  return
endfunc
```

### Backend MIPS (`program/mips/`)

- `integrated_mips_generator.py`: punto de entrada que consume `output.tac`.
- `register_allocator.py`, `address_descriptor.py`, `register_descriptor.py`: asignación de registros con spilling controlado.
- `activation_record.py` y `calling_convention.py`: construyen stack frames y manejan parámetros/retornos.
- Traductores especializados (`expression_translator.py`, `control_flow_translator.py`, `loop_translator.py`, `function_translator.py`, `class_translator.py`).
- `peephole_optimizer.py`: elimina cargas redundantes, stores muertos, simplifica operaciones algebraicas y colapsa saltos triviales.
- `runtime_library.py`: funciones auxiliares (`print`, manejo de strings, utilidades de arrays).

### IDE React (`IDE-compiscript/`)

- `CompiscriptIU.jsx`: editor personalizado con manejo de tabs, auto indentación, resaltado usando sentinelas (`\uE000` – `\uE00B`) y cálculo preciso de columnas en pixeles.
- `styles.css`: diseño responsivo inspirado en los laboratorios del curso.
- Fetch al servidor: `fetch('http://localhost:8000/analyze', {...})` con JSON, manejo de `isRunning`, toasts y paneles de TAC/diagnósticos.

## Artefactos generados

| Archivo        | Descripción                                                     | Cómo visualizarlo                                   |
|----------------|-----------------------------------------------------------------|-----------------------------------------------------|
| `ast.dot`      | AST en formato Graphviz                                         | `dot -Tpng ast.dot -o ast.png`                      |
| `output.tac`   | Código intermedio TAC completo                                  | Editor de texto / panel TAC del IDE                 |
| `scopes.json`  | Tabla de símbolos anotada con offsets y metadata                | Cualquier visor JSON                                |
| `output.s`     | Ensamblador MIPS listo para SPIM/MARS + runtime                 | Simuladores MIPS (SPIM, QtSPIM, MARS)               |
| Respuesta API  | `diagnostics`, `tac`, `scopes`, `ast_dot`                       | Consumido por el IDE o integraciones externas       |

## Pruebas y aseguramiento de calidad

- **PyTest completo**  
  ```bash
  pytest program/tests
  ```

- **Suite semántica** (`test_semantic_analysis.py`)  
  Cobertura de:
  - Sistema de tipos (operaciones válidas/invalidas, inferencia, asignaciones).
  - Manejo de scopes (redeclaraciones, uso de variables, closures).
  - Funciones/procedimientos (argumentos, retornos, recursión).
  - Control de flujo (condiciones, break/continue/return).
  - Clases/objetos (constructores, herencia, `this`, miembros inexistentes).
  - Arreglos y casos generales (código muerto, operaciones sin sentido).

- **Suite TAC/MIPS** (`program/tests/tac` y `test_mips_*.py`)  
  Valida temporales, etiquetas, registros de activación, asignación de registros y optimizaciones peephole.

- **Harness CLI** (`program/tests/run_tests.py`)  
  Ejecuta cada `.cps` dentro de `program/tests`, reporta tiempos y resultados agregados para regresiones rápidas.

## Regenerar lexer/parser

Si cambias `program/Compiscript.g4`:

```bash
cd program
java -jar ../antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -no-listener Compiscript.g4
```

Sobrescribe `CompiscriptLexer.py`, `CompiscriptParser.py` y `CompiscriptVisitor.py`. Asegúrate de reinstalar `antlr4-python3-runtime` si cambias la versión.

## Solución de problemas y preguntas frecuentes

- **`antlr4` no encontrado**: instala `antlr4-python3-runtime` en el mismo entorno Python. El JAR ya está en la raíz (`antlr-4.13.1-complete.jar`).
- **`dot` no está en PATH**: instala Graphviz y agrega su carpeta `bin`. Sin esto no podrás convertir `ast.dot` a PNG.
- **El IDE no se conecta al servidor**: confirma que FastAPI siga en `http://localhost:8000`, sin proxys ni puertos bloqueados. Verifica CORS (está abierto por defecto).
- **Errores TAC al compilar**: revisa `validation_errors` y corre `pytest program/tests/tac` para ubicar regresiones en generadores de expresiones/control de flujo.
- **Advertencias de MIPS**: normalmente indican registros derramados o instrucciones no soportadas por el simulador. Ejecuta `pytest program/tests/test_mips_*.py` para confirmar.
- **Docker en Windows**: usa PowerShell y respeta las comillas en el `-v "%cd%/program":/program`. Desde WSL, comparte la ruta del repo.
- **Registros temporales agotados**: simplifica expresiones largas o divide funciones; el generador recicla temporales pero reporta warnings si detecta fugas.

## Recursos adicionales

- `README_RUN_PROJECT.md`: guía paso a paso centrada en Docker + FastAPI.
- `readmes/README_SEMANTIC_ANALYSIS.md`: requisitos y rúbrica de la fase semántica.
- `readmes/README_TAC_GENERATION.md`: expectativas de la fase de código intermedio.
- `readmes/README_TESTS.md`: documentación de la batería de pruebas.
- `readmes/README_CODE_GENERATION.md` y `readmes/README_NOTES.md`: decisiones de diseño y notas históricas.

---

Con esta información puedes entender y reproducir el estado final del proyecto: compilador CompilScript con pipeline completo, servicio REST e IDE interactivo. Si extiendes el lenguaje o el backend, mantén este README sincronizado para que la documentación siga reflejando el comportamiento real del repositorio. ¡Feliz compilación!
