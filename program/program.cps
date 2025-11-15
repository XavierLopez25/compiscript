// Global constants and variables
const PI: integer = 314;
let greeting: string = "Hello, Compiscript!";
let flag: boolean;
let numbers: integer[] = [1, 2, 3, 4, 5];
let matrix: integer[][] = [[1, 2], [3, 4]];

flag = true;
print("Flag is initially: true");

if (flag) {
  print("Flag is true - condition works!");
  flag = false;
} else {
  print("Flag is false");
}

print("Flag after change: false");

// Boolean comparisons
let isGreater: boolean = (5 > 3);
let isEqual: boolean = (10 == 10);
let isLess: boolean = (7 < 2);

// Print solo los mensajes (los valores ya están implícitos en el mensaje)
print("5 > 3 is: true");
print("10 == 10 is: true");
print("7 < 2 is: false");

// Boolean logic in control flow
let canProceed: boolean = true;
let hasPermission: boolean = false;

if (canProceed) {
  print("Proceeding...");
  if (hasPermission) {
    print("Access granted");
  } else {
    print("Access denied - no permission");
  }
}

// Boolean with while loop
let keepRunning: boolean = false;
let counter: integer = 0;

while (keepRunning) {
  counter = counter + 1;
  print("Counter: " + counter);
  if (counter >= 3) {
    keepRunning = false;
  }
}

print("Loop finished when keepRunning became false");

// Simple closure-style function (no nested type signatures)
function makeAdder(x: integer): integer {
  return x + 1;
}

let addFive: integer = (makeAdder(5));
print("5 + 1 = " + addFive);

// Control structures
if (addFive > 5) {
  print("Greater than 5");
} else {
  print("5 or less");
}

while (addFive < 10) {
  addFive = addFive + 1;
}

do {
  print("Result is now " + addFive);
  addFive = addFive - 1;
} while (addFive > 7);

for (let i: integer = 0; i < 3; i = i + 1) {
  print("Loop index: " + i);
}

foreach (n in numbers) {
  if (n == 3) {
    continue;
  }
  print("Number: " + n);
  if (n > 4) {
    break;
  }
}

// Switch-case structure
switch (addFive) {
  case 7:
    print("It's seven");
  case 6:
    print("It's six");
  default:
    print("Something else");
}

// Try-catch structure
try {
  let risky: integer = numbers[10];
  print("Risky access: " + risky);
} catch (err) {
  print("Caught an error: " + err);
}

// Class definition and usage
class Animal {
  let name: string;

  function constructor(name: string) {
    this.name = name;
  }

  function speak(): string {
    return this.name + " makes a sound.";
  }
}

class Dog : Animal {
  function speak(): string {
    return this.name + " barks.";
  }
}

let dog: Dog = new Dog("Rex");
print(dog.speak());

// Object property access and array indexing
let first: integer = numbers[0];
print("First number: " + first);

// Function returning an array
function getMultiples(n: integer): integer[] {
  let result: integer[] = [n * 1, n * 2, n * 3, n * 4, n * 5];
  return result;
}

let multiples: integer[] = getMultiples(2);
print("Multiples of 2: " + multiples[0] + ", " + multiples[1]);

// Recursion
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

//Tests de scope
let x: integer = 1;
{
  let x: integer = 2;
  print(x);
}
print(x);
let n: integer = 1;
switch (n) {
  case 1:
    let k: integer = 5;
    print(k);
  default:
    print(0);
}

//---- RECURSION
function fact(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * fact(n - 1);
}
let f5: integer = fact(5);
print("fact(5) = " + f5);


// FUNCION ANIDADA
function foo(): integer { return 1; }
{
  function foo(): integer { return 2; }    
  let v: integer = foo();                
  print("inner foo = " + v);
}
let w2: integer = foo();     
print("outer foo = " + w2);
//------------

// Program end
print("Program finished.");
