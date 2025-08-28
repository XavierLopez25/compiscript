// Success test cases for semantic analysis
// This file contains valid CompilScript code that should pass semantic analysis

// ===== TYPE SYSTEM SUCCESS CASES =====

// Arithmetic operations with compatible types
var int_a: integer = 5;
var int_b: integer = 3;
var int_result1: integer = int_a + int_b;
var int_result2: integer = int_a - int_b;
var int_result3: integer = int_a * int_b;
var int_result4: integer = int_a / int_b;

var float_a: integer = 5;
var float_b: integer = 3;
var float_result1: integer = float_a + float_b;
var float_result2: integer = float_a - float_b;
var float_result3: integer = float_a * float_b;
var float_result4: integer = float_a / float_b;

// Mixed arithmetic with integer types
var mixed_result: integer = int_a + float_a;

// Logical operations with boolean types
var bool_a: boolean = true;
var bool_b: boolean = false;
var logical_and: boolean = bool_a && bool_b;
var logical_or: boolean = bool_a || bool_b;
var logical_not: boolean = !bool_a;

// Comparison operations
var comparison1: boolean = int_a == int_b;
var comparison2: boolean = int_a != int_b;
var comparison3: boolean = int_a < int_b;
var comparison4: boolean = int_a <= int_b;
var comparison5: boolean = int_a > int_b;
var comparison6: boolean = int_a >= int_b;

// Type-compatible assignments
var assign_int: integer = 42;
var assign_string: string = "hello world";
var assign_bool: boolean = true;

// Const initialization
const const_int: integer = 100;
const const_string: string = "constant";

// ===== SCOPE MANAGEMENT SUCCESS CASES =====

var global_var: integer = 10;

function scope_test(): void {
    var local_var: integer = 5;
    global_var = local_var;  // Access global from local scope
}

// Nested scope access
{
    var outer_block: integer = 20;
    {
        var inner_block: integer = 30;
        outer_block = inner_block;  // Access outer from inner
    }
}

// ===== FUNCTIONS SUCCESS CASES =====

// Function with correct arguments and return type
function add_numbers(a: integer, b: integer): integer {
    return a + b;
}

var function_result: integer = add_numbers(10, 20);

// Recursive function
function factorial(n: integer): integer {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// Void function
function print_message(): void {
    // do something
}

// ===== CONTROL FLOW SUCCESS CASES =====

// Boolean conditions in control structures
var condition: boolean = true;

if (condition) {
    // if body
}

while (condition) {
    condition = false;
}

for (var i: integer = 0; i < 10; i = i + 1) {
    if (i == 5) {
        break;
    }
    if (i == 3) {
        continue;
    }
}

// ===== CLASSES AND OBJECTS SUCCESS CASES =====

class Person {
    var name: string;
    var age: integer;
    
    function constructor(name: string, age: integer): void {
        this.name = name;
        this.age = age;
    }
    
    function getName(): string {
        return this.name;
    }
    
    function getAge(): integer {
        return this.age;
    }
    
    function setAge(new_age: integer): void {
        this.age = new_age;
    }
}

var person: Person = new Person("John", 25);
var person_name: string = person.getName();
var person_age: integer = person.getAge();
person.setAge(26);

// Class inheritance
class Student : Person {
    var student_id: integer;
    
    function constructor(name: string, age: integer, id: integer): void {
        this.name = name;
        this.age = age;
        this.student_id = id;
    }
    
    function getStudentId(): integer {
        return this.student_id;
    }
}

var student: Student = new Student("Alice", 20, 12345);

// ===== ARRAYS SUCCESS CASES =====

var int_array: integer[] = [1, 2, 3, 4, 5];
var string_array: string[] = ["hello", "world", "test"];
var bool_array: boolean[] = [true, false, true];

var first_element: integer = int_array[0];
var second_element: integer = int_array[1];

// ===== TYPE INFERENCE SUCCESS CASES =====

var inferred_int = 42;
var inferred_string = "inferred";
var inferred_bool = true;