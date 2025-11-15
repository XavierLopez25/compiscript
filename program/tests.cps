// ========================================
// COMPISCRIPT COMPREHENSIVE TEST SUITE
// ========================================
// This file tests all major language features

print("=== STARTING COMPISCRIPT TESTS ===");

// ========================================
// TEST 1: BASIC TYPES AND LITERALS
// ========================================
print("");
print("--- TEST 1: Basic Types ---");

let intVar: integer = 42;
let strVar: string = "Hello";
let boolVar: boolean = true;
const PI: integer = 314;

print("Integer: " + intVar);
print("String: " + strVar);
print("Constant PI: " + PI);

// ========================================
// TEST 2: ARITHMETIC OPERATIONS
// ========================================
print("");
print("--- TEST 2: Arithmetic ---");

let a: integer = 10;
let b: integer = 3;

let sum2: integer = a + b;
let diff: integer = a - b;
let prod: integer = a * b;
let quot: integer = a / b;
let rem: integer = a % b;
let negA: integer = -a;

print("10 + 3 = " + sum2);
print("10 - 3 = " + diff);
print("10 * 3 = " + prod);
print("10 / 3 = " + quot);
print("10 % 3 = " + rem);
print("-10 = " + negA);

// ========================================
// TEST 3: BOOLEAN OPERATIONS
// ========================================
print("");
print("--- TEST 3: Boolean Logic ---");

let t: boolean = true;
let f: boolean = false;

if (t && t) { print("true && true = true"); }
if (t && f) { print("ERROR: true && false should be false"); } else { print("true && false = false"); }
if (f || t) { print("false || true = true"); }
if (f || f) { print("ERROR: false || false should be false"); } else { print("false || false = false"); }
if (!t) { print("ERROR: !true should be false"); } else { print("!true = false"); }
if (!f) { print("!false = true"); }

// ========================================
// TEST 4: COMPARISONS
// ========================================
print("");
print("--- TEST 4: Comparisons ---");

if (5 > 3) { print("5 > 3 = true"); }
if (5 < 3) { print("ERROR"); } else { print("5 < 3 = false"); }
if (5 >= 5) { print("5 >= 5 = true"); }
if (5 <= 3) { print("ERROR"); } else { print("5 <= 3 = false"); }
if (5 == 5) { print("5 == 5 = true"); }
if (5 != 3) { print("5 != 3 = true"); }

// ========================================
// TEST 5: STRING CONCATENATION
// ========================================
print("");
print("--- TEST 5: String Concatenation ---");

print("String: " + strVar);

let num: integer = 123;
print("Number: " + num);

// ========================================
// TEST 6: ARRAYS
// ========================================
print("");
print("--- TEST 6: Arrays ---");

let numbers: integer[] = [10, 20, 30, 40, 50];
print("Array[0]: " + numbers[0]);
print("Array[2]: " + numbers[2]);
print("Array[4]: " + numbers[4]);

let matrix: integer[][] = [[1, 2], [3, 4]];
print("Matrix[0][1]: " + matrix[0][1]);
print("Matrix[1][0]: " + matrix[1][0]);

let empty = [];
print("Empty array created");

// ========================================
// TEST 7: IF-ELSE
// ========================================
print("");
print("--- TEST 7: If-Else ---");

let x: integer = 10;
if (x > 5) {
  print("x is greater than 5");
} else {
  print("x is 5 or less");
}

if (x < 5) {
  print("This should not print");
} else {
  print("x is not less than 5");
}

// Nested if
if (x > 0) {
  if (x < 20) {
    print("x is between 0 and 20");
  }
}

// ========================================
// TEST 8: WHILE LOOP
// ========================================
print("");
print("--- TEST 8: While Loop ---");

let i: integer = 0;
while (i < 3) {
  print("While iteration: " + i);
  i = i + 1;
}
print("While loop done");

// ========================================
// TEST 9: DO-WHILE LOOP
// ========================================
print("");
print("--- TEST 9: Do-While Loop ---");

let j: integer = 0;
do {
  print("Do-While iteration: " + j);
  j = j + 1;
} while (j < 2);
print("Do-While loop done");

// ========================================
// TEST 10: FOR LOOP
// ========================================
print("");
print("--- TEST 10: For Loop ---");

for (let k: integer = 0; k < 3; k = k + 1) {
  print("For iteration: " + k);
}
print("For loop done");

// ========================================
// TEST 11: FOREACH LOOP
// ========================================
print("");
print("--- TEST 11: Foreach Loop ---");

let items: integer[] = [100, 200, 300];
foreach (item in items) {
  print("Item: " + item);
}
print("Foreach done");

// ========================================
// TEST 12: BREAK AND CONTINUE
// ========================================
print("");
print("--- TEST 12: Break and Continue ---");

for (let m: integer = 0; m < 5; m = m + 1) {
  if (m == 2) {
    continue;
  }
  if (m == 4) {
    break;
  }
  print("Loop m: " + m);
}
print("Break/Continue done");

// ========================================
// TEST 13: SWITCH STATEMENT
// ========================================
print("");
print("--- TEST 13: Switch Statement ---");

let day: integer = 2;
switch (day) {
  case 1:
    print("Monday");
  case 2:
    print("Tuesday");
    print("Wednesday");
  case 3:
    print("Thursday");
  default:
    print("Other day");
}

let color: integer = 5;
switch (color) {
  default:
    print("Unknown color");
}

// ========================================
// TEST 14: FUNCTIONS
// ========================================
print("");
print("--- TEST 14: Functions ---");

function addNumbers(a: integer, b: integer): integer {
  return a + b;
}

function greet(name: string): string {
  return "Hello, " + name;
}

function noReturn(): void {
  print("This function returns nothing");
}

let sum: integer = addNumbers(5, 7);
print("5 + 7 = " + sum);

let greeting: string = greet("Alice");
print(greeting);

noReturn();

// ========================================
// TEST 15: RECURSION
// ========================================
print("");
print("--- TEST 15: Recursion ---");

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function fibonacci(n: integer): integer {
  if (n <= 1) {
    return n;
  }
  return fibonacci(n - 1) + fibonacci(n - 2);
}

let fact5: integer = factorial(5);
let fact6: integer = factorial(6);
let fib7: integer = fibonacci(7);

print("factorial(5) = " + fact5);
print("factorial(6) = " + fact6);
print("fibonacci(7) = " + fib7);

// ========================================
// TEST 16: NESTED FUNCTIONS
// ========================================
print("");
print("--- TEST 16: Nested Functions ---");

function foo(): integer { return 1; }
{
  function foo(): integer { return 2; }    
  let v: integer = foo();                
  print("inner foo = " + v);
}
let w2: integer = foo();     
print("outer foo = " + w2);

// ========================================
// TEST 17: ARRAYS FROM FUNCTIONS
// ========================================
print("");
print("--- TEST 17: Array Functions ---");

function makeArray(size: integer): integer[] {
  let arr: integer[] = [1, 2, 3, 4, 5];
  return arr;
}

function getFirst(arr: integer[]): integer {
  return arr[0];
}

let myArr: integer[] = makeArray(5);
print("First element: " + myArr[0]);
print("Third element: " + myArr[2]);

let firstElem: integer = getFirst(myArr);
print("getFirst result: " + firstElem);

// ========================================
// TEST 18: CLASSES AND OBJECTS
// ========================================
print("");
print("--- TEST 18: Classes ---");

class Person {
  let name: string;
  let age: integer;

  function constructor(name: string, age: integer) {
    this.name = name;
    this.age = age;
  }

  function introduce(): string {
    return "I am " + this.name;
  }

  function getAge(): integer {
    return this.age;
  }
}

let person: Person = new Person("Bob", 25);
let intro: string = person.introduce();
let personAge: integer = person.getAge();

print(intro);
print("Age: " + personAge);

// ========================================
// TEST 19: INHERITANCE
// ========================================
print("");
print("--- TEST 19: Inheritance ---");

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

// ========================================
// TEST 20: PROPERTY ACCESS AND ASSIGNMENT
// ========================================
print("");
print("--- TEST 20: Property Access ---");

class Counter {
  let value: integer;

  function constructor() {
    this.value = 0;
  }

  function increment(): void {
    this.value = this.value + 1;
  }

  function getValue(): integer {
    return this.value;
  }
}

let counter: Counter = new Counter();
counter.increment();
counter.increment();
let counterVal: integer = counter.getValue();
print("Counter: " + counterVal);

// ========================================
// TEST 21 TRY-CATCH
// ========================================
print("");
print("--- TEST 21: Try-Catch ---");

try {
  let arr: integer[] = [1, 2, 3];
  let bad: integer = arr[10];
  print("This should not print");
} catch (error) {
  print("Caught error: " + error);
}

try {
  print("Normal execution");
} catch (e) {
  print("No error");
}

// ========================================
// TEST 22: SCOPE TESTS
// ========================================
print("");
print("--- TEST 22: Scopes ---");

let global: integer = 1;
{
  let global: integer = 2;
  print("Inner scope: " + global);
}
print("Outer scope: " + global);

let n: integer = 10;
{
  let n: integer = 20;
  {
    let n: integer = 30;
    print("Innermost: " + n);
  }
  print("Middle: " + n);
}
print("Outermost: " + n);

// ========================================
// TEST 23: SWITCH SCOPE
// ========================================
print("");
print("--- TEST 23: Switch Scope ---");

let sw: integer = 1;
switch (sw) {
  case 1:
    let caseVar: integer = 100;
    print("Case var: " + caseVar);
  default:
    print("Default");
}

// ========================================
// TEST 24: COMPLEX EXPRESSIONS
// ========================================
print("");
print("--- TEST 24: Complex Expressions ---");

let expr1: integer = (5 + 3) * 2;
print("(5 + 3) * 2 = " + expr1);

let expr2: integer = 10 - 2 * 3;
print("10 - 2 * 3 = " + expr2);

if ((5 > 3) && (10 < 20)) {
  print("(5 > 3) && (10 < 20) = true");
}

if ((5 > 10) || (3 < 7)) {
  print("(5 > 10) || (3 < 7) = true");
}

// ========================================
// TEST 25: MODULO OPERATOR
// ========================================
print("");
print("--- TEST 25: Modulo ---");

let mod1: integer = 10 % 3;
let mod2: integer = 15 % 4;
let mod3: integer = 20 % 5;

print("10 % 3 = " + mod1);
print("15 % 4 = " + mod2);
print("20 % 5 = " + mod3);

// ========================================
// TEST 26: NEGATIVE NUMBERS
// ========================================
print("");
print("--- TEST 26: Negative Numbers ---");

let neg: integer = -42;
let pos: integer = -neg;

print("Negative: " + neg);
print("Positive: " + pos);

let result1: integer = -5 + 10;
print("-5 + 10 = " + result1);

// ========================================
// TEST 27: EDGE CASES
// ========================================
print("");
print("--- TEST 27: Edge Cases ---");

// Empty blocks
if (true) {
}
print("Empty if block ok");

// Multiple returns
function multiReturn(x: integer): integer {
  if (x > 0) {
    return 1;
  }
  return -1;
}

let multiRet: integer = multiReturn(5);
print("Multi return: " + multiRet);

// ========================================
// TEST 28: COMPLEX ARRAY OPERATIONS
// ========================================
print("");
print("--- TEST 28: Complex Arrays ---");

function getMultiples(n: integer): integer[] {
  let result: integer[] = [n * 1, n * 2, n * 3, n * 4, n * 5];
  return result;
}

let multiples: integer[] = getMultiples(2);
print("Multiples of 2: " + multiples[0] + ", " + multiples[1]);

print("");
print("=== ALL TESTS COMPLETED ===");
