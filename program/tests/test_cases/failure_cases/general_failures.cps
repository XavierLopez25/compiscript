// GENERAL SEMANTIC RULE FAILURE CASES
// These should fail semantic analysis

// ===== MEANINGLESS EXPRESSIONS =====

function test_function(): void { }
var number: integer = 5;

// Arithmetic with functions (should fail)
var invalid_expr1 = test_function * 5;      // ERROR: multiplying function by number
var invalid_expr2 = number + test_function; // ERROR: adding function to number

// Logical operations with non-boolean expressions
var invalid_logic1 = test_function && true; // ERROR: function in logical operation
var invalid_logic2 = 5 || false;           // ERROR: number in logical operation

// ===== DUPLICATE DECLARATIONS =====

// Duplicate variable names in same scope (should fail)
var duplicate: integer = 5;
var duplicate: string = "hello";  // ERROR: duplicate variable name

// Duplicate function names (should fail)
function duplicate_func(): void { }
function duplicate_func(): integer { return 1; }  // ERROR: duplicate function name

// Duplicate parameter names in function (should fail)
function bad_params(x: integer, x: string): void { }  // ERROR: duplicate parameter

// ===== TYPE INFERENCE FAILURES =====

// Unable to infer type from null or undefined (should fail)
var uninferable;  // ERROR: cannot infer type without initialization

// Conflicting type inference (should fail)
var conflicted = 5;
conflicted = "hello";  // ERROR: type mismatch after inference

// ===== DEAD CODE DETECTION =====

function dead_code_test(): integer {
    return 42;
    var unreachable: integer = 5;  // ERROR: dead code after return
}

function loop_dead_code(): void {
    while (true) {
        break;
        var also_unreachable: integer = 10;  // ERROR: dead code after break
    }
}

// ===== INVALID OPERATIONS =====

// Trying to call non-callable expressions
var not_callable: string = "hello";
var invalid_call = not_callable();  // ERROR: calling non-function

// Invalid property access on primitives
var primitive: integer = 42;
var invalid_property = primitive.someProperty;  // ERROR: property access on primitive

// Invalid array access on non-arrays
var not_array: boolean = true;
var invalid_array_access = not_array[0];  // ERROR: array access on non-array