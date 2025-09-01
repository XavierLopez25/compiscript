// PASA
let n: integer = 2;
switch (n) {
  case 1: print("uno");
  case 2: print("dos");
  default: print("otro");
}

// FALLA
let n: integer = 1;
switch (n) {
  case "1": print("string");
  default: print("ok");
}