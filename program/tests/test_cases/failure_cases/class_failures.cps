// CLASS AND OBJECT FAILURE CASES
// These should fail semantic analysis

// ===== PROPERTY ACCESS ON NON-EXISTENT MEMBERS =====

class SimplePerson {
    var name: string;
    
    function constructor(name: string): void {
        this.name = name;
    }
}

var person: SimplePerson = new SimplePerson("John");

// Accessing non-existent property (should fail)
var invalid_prop = person.age;  // ERROR: property 'age' does not exist

// Accessing non-existent method (should fail)
var invalid_method = person.getAge();  // ERROR: method 'getAge' does not exist

// ===== CONSTRUCTOR VALIDATION =====

class Point {
    var x: integer;
    var y: integer;
    
    function constructor(x: integer, y: integer): void {
        this.x = x;
        this.y = y;
    }
}

// Wrong number of constructor arguments (should fail)
var point1: Point = new Point(10);        // ERROR: missing argument
var point2: Point = new Point(10, 20, 30); // ERROR: too many arguments

// Wrong constructor argument types (should fail)
var point3: Point = new Point("hello", 20);  // ERROR: wrong type for first argument

// ===== THIS REFERENCE OUTSIDE CLASS =====

// Using 'this' outside class context (should fail)
function global_function(): void {
    var invalid = this.name;  // ERROR: 'this' outside class
}

var global_this = this;  // ERROR: 'this' in global scope

// ===== INVALID CLASS DECLARATIONS =====

// Class with duplicate member names (should fail)
class DuplicateMembers {
    var value: integer;
    var value: string;  // ERROR: duplicate member name
}

// Class with duplicate method names (should fail)
class DuplicateMethods {
    function getValue(): integer { return 1; }
    function getValue(): string { return "hello"; }  // ERROR: duplicate method name
}

// ===== INHERITANCE ERRORS =====

// Inheriting from non-existent class (should fail)
class Child : NonExistentParent {  // ERROR: parent class doesn't exist
    // body
}

// Circular inheritance (should fail)
class A : B { }
class B : A { }  // ERROR: circular inheritance

// ===== METHOD OVERRIDE ERRORS =====

class Parent {
    function getValue(): integer { return 1; }
}

class Child : Parent {
    // Invalid override - different return type (should fail)
    function getValue(): string { return "hello"; }  // ERROR: incompatible override
}