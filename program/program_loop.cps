// Ejemplos de if con funcionamiento correctos

let a: boolean = true;
if (a) {
  print("ok");
}

function test(b: boolean): void {
  if (b && true) {
    print("ok");
  }
}

// Ejemplos de if con error

// Línea 2: la condición no es booleana → debería marcar el "42" (condición)
if (42) {
  print("nope");
}

// Línea 7: la condición no es booleana (string) → marca el literal "hello"
if ("hello") {
  print("nope");
}

// Ejemplos de while, do while y for correctos

let t: boolean = true;

while (t) {
  print("loop");
}

do {
  print("once");
} while (t);

for (let i: integer = 0; t; i = i + 1) {
  print(i);
}

// Ejemplos de while, do while y for con errores

// while con entero
while (1) {
  print("x");
}

// do-while con string
do {
  print("y");
} while ("nope");

// for con condición no booleana (condición es la PRIMERA expression() del for)
for (let i: integer = 0; 123; i = i + 1) {
  print(i);
}

// Ejemplo de switch correcto 

let f: boolean = false;

switch (f) {
  case false:
    print("is false");
    break;
  case true:
    print("is true");
    break;
  default:
    print("default");
}

// Ejemplo de switch incorrecto 

// Línea 2: switch(100) no es booleano → debe marcar el "100"
switch (100) {
  case true:
    print("x");
    break;
  default:
    print("d");
}

