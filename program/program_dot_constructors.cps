
// Ejemplo correcto de uso de dot 
class A {
  let x: integer;
  function foo(): void { print("foo"); }
}

let a: A = new A();
a.x = 10;
a.foo();
print(a.x);


// Ejemplo con error de dot 

class A { let x: integer; }

let a: A = new A();
print(a.y);      // member 'y' does not exist
a.bar();         // method 'bar' does not exist

let n: integer = 5;
print(n.len);    // member access on non-class value

class B { let x: integer; }
let b: B = new B();
b.x();           // 'x' is not callable

let s: string = "hola";
s.length = 3;    // property assignment on non-class value


// Ejemplo correcto para constructores

class Persona {
  let nombre: string;
  let edad: integer;

  function constructor(nombre: string, edad: integer) {
    this.nombre = nombre;
    this.edad = edad;
  }
}

let p: Persona = new Persona("Ana", 30);  

class Vacio {
  let value: integer;
}

let v: Vacio = new Vacio();          


// Ejemplo con errores para constructores 

class C {
  function constructor(a: integer, b: integer) {}
}

let c1: C = new C(1);            // Constructor of 'C' expects 2 arguments
let c2: C = new C(1, 2, 3);      // Constructor of 'C' expects 2 arguments

class C {
  function constructor(a: integer, b: integer) {}
}

let c: C = new C("x", 2);        // Incompatible argument in constructor of 'C'

class D {
  function constructor(n: integer) {}
}

let d: D = D(10);                // Constructor of class 'D' must be called with 'new'


class E {}

let e: E = new E(1);             // Class 'E' does not define a constructor; 0 arguments expected

// Ejemplo correcto con this

class Persona {
  let nombre: string;

  function constructor(n: string) { this.nombre = n; }

  function saludar(): void {
    print("Hola " + this.nombre);
  }
}

let p: Persona = new Persona("Ana");
p.saludar();  


// Ejemplo con errores con this

print(this);  // 'this' can only be used within class methods


// Ejemplo correcto con constructor y método 

class Caja {
  let v: integer;

  function constructor(x: integer) { this.v = x; }

  function dup(): integer { return this.v + this.v; }
}

let c: Caja = new Caja(7);
print(c.dup()); 
