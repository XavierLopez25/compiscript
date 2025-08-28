// FUNCTION AND PROCEDURE FAILURE CASES
// These should fail semantic analysis

// ===== FUNCTION CALL ARGUMENT VALIDATION =====

function add_two_numbers(a: integer, b: integer): integer {
    return a + b;
}

// Wrong number of arguments (should fail)
var result1 = add_two_numbers(5);           // ERROR: missing argument
var result2 = add_two_numbers(5, 3, 7);     // ERROR: too many arguments

// Wrong argument types (should fail)
var result3 = add_two_numbers("hello", 3);  // ERROR: wrong type for first argument
var result4 = add_two_numbers(5, true);     // ERROR: wrong type for second argument

// ===== RETURN TYPE VALIDATION =====

// Return type mismatch (should fail)
function get_integer(): integer {
    return "hello";  // ERROR: returning string instead of integer
}

function get_string(): string {
    return 42;  // ERROR: returning integer instead of string
}

function get_boolean(): boolean {
    return 42;  // ERROR: returning integer instead of boolean
}

// Missing return in non-void function (should fail)
function missing_return(): integer {
    var x: integer = 5;
    // ERROR: no return statement
}

// Return in void function with value (should fail)
function void_with_return(): void {
    return 42;  // ERROR: void function returning value
}

// ===== FUNCTION CALLS ON NON-FUNCTIONS =====

var not_a_function: integer = 42;
var invalid_call = not_a_function(5, 3);  // ERROR: calling variable as function

// ===== INVALID FUNCTION DECLARATIONS =====

// Function with duplicate parameter names (should fail)
function duplicate_params(x: integer, x: string): void { }  // ERROR: duplicate parameter names