// SCOPE MANAGEMENT FAILURE CASES
// These should fail semantic analysis

// ===== UNDECLARED VARIABLE USAGE =====

function test_undeclared(): void {
    undeclared_var = 5;  // ERROR: variable not declared
}

var another_test = unknown_variable;  // ERROR: variable not declared

// ===== IDENTIFIER REDECLARATION IN SAME SCOPE =====

// Variable redeclaration (should fail)
var duplicate_var: integer = 5;
var duplicate_var: string = "hello";  // ERROR: identifier already exists

// Function redeclaration (should fail)
function duplicate_function(): void { }
function duplicate_function(): integer { return 1; }  // ERROR: function already exists

// Parameter redeclaration (should fail)
function test_params(param: integer, param: string): void { }  // ERROR: duplicate parameter

// ===== ACCESSING VARIABLES FROM INNER SCOPE =====

{
    var inner_scope_var: integer = 10;
}
var invalid_access = inner_scope_var;  // ERROR: variable not accessible outside its scope

// ===== CONST REASSIGNMENT =====

const immutable_var: integer = 42;
immutable_var = 100;  // ERROR: cannot reassign const variable