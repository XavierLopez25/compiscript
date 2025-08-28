# 🧪 Batería de Pruebas de Análisis Semántico de CompilScript

## 📋 Resumen

El directorio (tests) contiene una batería de pruebas integral para validar todas las reglas de análisis semántico especificadas en `README_SEMANTIC_ANALYSIS.md`. El conjunto de pruebas cubre tanto **casos exitosos** (código válido que debe pasar) como **casos de fallo** (código inválido que debe generar errores semánticos).

## 📁 Estructura de Pruebas
```
tests/
├── README_TESTS.md                    # This documentation
├── test_semantic_analysis.py          # Main Python test suite
└── test_cases/
    ├── success_cases.cps              # Valid CompilScript code
    └── failure_cases/
        ├── type_system_failures.cps   # Type system error cases
        ├── scope_failures.cps         # Scope management error cases
        ├── function_failures.cps      # Function/procedure error cases
        ├── control_flow_failures.cps  # Control flow error cases
        ├── class_failures.cps         # Class/object error cases
        ├── array_failures.cps         # Array/data structure error cases
        └── general_failures.cps       # General semantic rule error cases
```

## 🧪 Categorías de Pruebas

### 1. Pruebas del Sistema de Tipos

#### ✅ Casos Exitosos
- **Operaciones aritméticas**: Aritmética de enteros (`+`, `-`, `*`, `/`)
- **Promoción de tipos**: Operaciones mixtas entre enteros con promoción automática
- **Operaciones lógicas**: Lógica booleana (`&&`, `||`, `!`)
- **Operaciones de comparación**: Comparaciones compatibles por tipo (`==`, `!=`, `<`, `<=`, `>`, `>=`)
- **Compatibilidad de asignación**: Asignaciones de tipo correctas
- **Inicialización de constantes**: Declaración adecuada de constantes con inicialización

#### ❌ Casos de Fallo
- **Aritmética inválida**: Operaciones aritméticas con cadenas o booleanos
- **Tipos lógicos incorrectos**: Operandos no booleanos en operaciones lógicas
- **Incompatibilidad de tipos**: Comparación de tipos incompatibles (entero vs cadena)
- **Errores de asignación**: Asignaciones de tipo incorrecto (cadena a entero, etc.)
- **Constantes no inicializadas**: Declaraciones de constantes sin inicialización

### 2. Pruebas de Gestión de Alcance

#### ✅ Casos Exitosos
- **Resolución de variables**: Acceso adecuado a variables locales/globales
- **Acceso a alcances anidados**: Alcances internos accediendo a variables externas
- **Aislamiento de alcance**: Variables correctamente aisladas entre alcances

#### ❌ Casos de Fallo
- **Variables no declaradas**: Uso de variables antes de su declaración
- **Redefinición**: Múltiples declaraciones del mismo identificador en un alcance
- **Fuga de alcance**: Acceso a variables de alcance interno desde el externo
- **Reasignación de constantes**: Intento de modificar variables constantes

### 3. Pruebas de Funciones y Procedimientos

#### ✅ Casos Exitosos
- **Llamadas a funciones**: Cantidad y tipos de argumentos correctos
- **Tipos de retorno**: Coincidencia adecuada de tipo de retorno
- **Funciones recursivas**: Funciones que se llaman a sí mismas
- **Funciones void**: Funciones sin valores de retorno

#### ❌ Casos de Fallo
- **Desajuste de argumentos**: Número o tipos de argumentos incorrectos
- **Errores de tipo de retorno**: Retorno de tipo incorrecto o faltante
- **Llamadas inválidas**: Llamar variables que no son funciones
- **Parámetros duplicados**: Funciones con nombres de parámetros duplicados

### 4. Pruebas de Control de Flujo

#### ✅ Casos Exitosos
- **Condiciones booleanas**: Expresiones booleanas adecuadas en `if`, `while`, `for`
- **Control de bucles**: Uso válido de `break` y `continue` dentro de bucles
- **Retornos en funciones**: Sentencias `return` dentro de cuerpos de función

#### ❌ Casos de Fallo
- **Condiciones no booleanas**: Uso de expresiones no booleanas como condiciones
- **Break/Continue inválidos**: Uso de `break`/`continue` fuera de bucles
- **Retornos inválidos**: Sentencias `return` fuera de funciones
- **Desajuste de tipos en switch**: Tipos de casos que no coinciden con la expresión del switch

### 5. Pruebas de Clases y Objetos

#### ✅ Casos Exitosos
- **Acceso a propiedades**: Acceso válido a miembros y métodos mediante notación de punto
- **Llamadas a constructores**: Invocación adecuada de constructores
- **Referencia this**: Uso correcto de `this` dentro de métodos de clase
- **Herencia**: Herencia de clases y sobrescritura de métodos

#### ❌ Casos de Fallo
- **Miembros inexistentes**: Acceso a propiedades/métodos no definidos
- **Errores de constructor**: Argumentos incorrectos en constructores
- **This inválido**: Uso de `this` fuera del contexto de clase
- **Errores de herencia**: Herencia circular, sobrescritura inválida

### 6. Pruebas de Arreglos y Estructuras de Datos

#### ✅ Casos Exitosos
- **Literales de arreglos**: Tipos de elementos consistentes en arreglos
- **Acceso por índice**: Acceso válido a elementos de arreglos
- **Declaraciones de tipo**: Anotaciones de tipo de arreglo adecuadas

#### ❌ Casos de Fallo
- **Tipos mezclados**: Arreglos con tipos de elementos inconsistentes
- **Indexación inválida**: Acceso a arreglos en tipos que no son arreglos
- **Desajuste de tipos**: Tipos incorrectos en asignaciones de arreglos

### 7. Pruebas de Reglas Semánticas Generales

#### ✅ Casos Exitosos
- **Expresiones significativas**: Operaciones semánticamente válidas
- **Inferencia de tipos**: Deducción automática de tipo para variables sin tipo
- **Declaraciones válidas**: Declaraciones adecuadas de variables y funciones

#### ❌ Casos de Fallo
- **Operaciones sin sentido**: Operaciones inválidas (función * número)
- **Declaraciones duplicadas**: Múltiples declaraciones del mismo identificador
- **Código muerto**: Código inalcanzable después de `return`, `break`, etc.
- **Operaciones inválidas**: Llamar no-funciones, acceso a propiedades en primitivos

## 🚀 Ejecución de las Pruebas

### Suite de Pruebas en Python

```bash
# Navega al directorio de pruebas
cd tests

# Ejecuta toda la suite de pruebas
python test_semantic_analysis.py

# Ejecuta con salida detallada
python test_semantic_analysis.py -v
```

### Archivos de Prueba Individuales

Los archivos `.cps` pueden probarse individualmente usando el analizador semántico:

```bash
# Prueba casos exitosos (deben pasar)
python ../program/Driver.py test_cases/success_cases.cps

# Prueba casos de fallo (deben reportar errores)
python ../program/Driver.py test_cases/failure_cases/type_system_failures.cps
python ../program/Driver.py test_cases/failure_cases/scope_failures.cps
# ... etc.
```

## 📊 Cobertura de Pruebas

La batería de pruebas cubre **100%** de las reglas semánticas especificadas en los requisitos:

### Sistema de Tipos (Cobertura 100%)
- ✅ Verificación de tipos en operaciones aritméticas
- ✅ Verificación de tipos en operaciones lógicas  
- ✅ Compatibilidad de tipos en comparaciones
- ✅ Verificación de tipo en asignaciones
- ✅ Validación de inicialización de constantes
- ✅ Verificación de tipos en arreglos y estructuras

### Gestión de Alcance (Cobertura 100%)
- ✅ Resolución de nombres (local/global)
- ✅ Detección de variables no declaradas
- ✅ Prevención de redefinición
- ✅ Control de acceso a bloques anidados
- ✅ Creación de entorno de símbolos

### Funciones y Procedimientos (Cobertura 100%)
- ✅ Validación de argumentos (cantidad y tipos)
- ✅ Validación de tipo de retorno
- ✅ Soporte para funciones recursivas
- ✅ Funciones anidadas y cierres
- ✅ Detección de funciones duplicadas

### Control de Flujo (Cobertura 100%)
- ✅ Validación de condiciones booleanas
- ✅ Validación de alcance de break/continue
- ✅ Validación de sentencias return
- ✅ Validación de sentencias switch

### Clases y Objetos (Cobertura 100%)
- ✅ Validación de existencia de miembros
- ✅ Validación de constructores
- ✅ Manejo de referencia this
- ✅ Soporte de herencia

### Arreglos y Estructuras de Datos (Cobertura 100%)
- ✅ Verificación de tipo de elementos
- ✅ Validación de índices
- ✅ Unificación de tipo en literales de arreglos

### Reglas Generales (Cobertura 100%)
- ✅ Detección de código muerto
- ✅ Validación semántica de expresiones
- ✅ Validación de declaraciones duplicadas
- ✅ Inferencia de tipos

## 📝 Resultados de Pruebas

Cada caso de prueba incluye:

1. **Descripción de la prueba**: Qué valida la prueba
2. **Comportamiento esperado**: Éxito (pasa) o Fallo (se espera error)
3. **Mensaje de error**: Para casos de fallo, patrones de mensaje de error esperados
4. **Cobertura**: Qué regla(s) semántica(s) cubre la prueba

## 🔧 Extender las Pruebas

Para agregar nuevos casos de prueba:

1. **Casos exitosos**: Agrega código válido a `success_cases.cps`
2. **Casos de fallo**: Agrega código inválido al archivo de fallo correspondiente
3. **Pruebas en Python**: Agrega métodos de prueba correspondientes en `test_semantic_analysis.py`
4. **Documentación**: Actualiza este README con nuevas descripciones de pruebas

## 🎯 Criterios de Validación

La batería de pruebas garantiza:

- **Completitud**: Todas las reglas semánticas son probadas
- **Precisión**: Las pruebas identifican correctamente código válido vs inválido
- **Cobertura**: Casos positivos y negativos
- **Mantenibilidad**: Organización y documentación clara
- **Automatización**: Suite de pruebas ejecutable para validación continua

Esta batería de pruebas integral valida que el analizador semántico de CompilScript implementa correctamente todas las reglas de análisis semántico requeridas según la especificación.