// Ejemplos de funcionamiento correcto para break y continue 

let t: boolean = true;

while (t) {
  continue; // OK (dentro de while)
}

for (let i: integer = 0; t; i = i + 1) {
  if (t) {
    break; // OK (dentro de for)
  }
}

// Ejemplos de error para break y continue 

break;    // Debe fallar: "break out of loop" (marca el keyword 'break')
continue; // Debe fallar: "continue out of loop" (marca el keyword 'continue')

// Ejemplos correctos para return 

function f1(): void {
  print("hola");
  return; // ok: void con return sin valor
}

function f2(a: integer, b: integer): integer {
  return a + b; // ok: retorna integer
}

function f3(x: boolean): boolean {
  if (x) return true; // ok
  return false;       // ok
}

// Ejemplos con error para return 

// Return fuera de función
return 5;

// Return con valor en función void → debe marcar la expresión del return
function bad1(): void {
  return 10; // incompatible: void no acepta valor
}

// Return sin valor en función no-void (integer)
function bad2(): integer {
  return; // debe fallar
}

// Return tipo incompatible en función integer → debe marcar la expresión
function bad3(): integer {
  let s: string = "hola";
  return s; // incompatible return type
}
