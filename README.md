# compiscript

## 🧰 Instrucciones de Configuración

1. **Construir y Ejecutar el Contenedor Docker:** Desde el directorio raíz, ejecuta el siguiente comando para construir la imagen y lanzar un contenedor interactivo:

   ```bash
   docker build --rm . -t csp-image && docker run --rm -ti -v "$(pwd)/program":/program csp-image
   ```
2. **Entender el Entorno**

   - El directorio `program` se monta dentro del contenedor.
   - Este contiene la **gramática de ANTLR de Compiscript y una versión en BNF**, un archivo `Driver.py` (punto de entrada principal) y un archivo `program.cps` (entrada de prueba con la extensión de archivos de Compiscript).
3. **Generar Archivos de Lexer y Parser:** Dentro del contenedor, compila la gramática ANTLR a Python con:

   ```bash
   antlr -Dlanguage=Python3 -visitor -no-listener Compiscript.g4
   ```
4. **Ejecutar el Analizador**
   Usa el driver para analizar el archivo de prueba:

   ```bash
   python3 Driver.py program.cps
   ```

   - ✅ Si el archivo es sintácticamente correcto, se mostrará:
    ```bash
    Semantic analysis completed successfully.
    AST -> ast.dot (usa: dot -Tpng ast.dot -o ast.png)
    ```
   - ❌ Si existen errores, ANTLR los mostrará en la consola.

5. **Generar el AST en .png**
    Corre el comando para generar el AST como imagen:
    ```bash
    dot -Tpng ast.dot -o ast.png
    ```
