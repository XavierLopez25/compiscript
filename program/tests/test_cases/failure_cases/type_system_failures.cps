// TYPE SYSTEM FAILURE CASES
// These should fail semantic analysis

// ===== ARITHMETIC OPERATIONS WITH INCOMPATIBLE TYPES =====

// String arithmetic (should fail)
var str_a: string = "hello";
var str_b: string = "world"; 
var str_result: string = str_a + str_b;  // ERROR: strings don't support arithmetic

// Boolean arithmetic (should fail)
var bool_a: boolean = true;
var bool_b: boolean = false;
var bool_result: boolean = bool_a + bool_b;  // ERROR: booleans don't support arithmetic

// Mixed incompatible arithmetic
var string_num: string = "5" + 3;  // ERROR: string + integer

// ===== LOGICAL OPERATIONS WITH NON-BOOLEAN TYPES =====

// Integer logical operations (should fail)
var int_a: integer = 5;
var int_b: integer = 3;
var logical_result: boolean = int_a && int_b;  // ERROR: integers in logical operation

// String logical operations (should fail)
var str_logical: boolean = "true" && "false";  // ERROR: strings in logical operation

// ===== COMPARISON OPERATIONS WITH INCOMPATIBLE TYPES =====

// Comparing different types (should fail)
var int_val: integer = 5;
var str_val: string = "hello";
var invalid_comparison: boolean = int_val == str_val;  // ERROR: comparing integer with string

// ===== ASSIGNMENT TYPE INCOMPATIBILITY =====

// Wrong type assignments (should fail)
var int_var: integer = "hello";  // ERROR: string assigned to integer
var bool_var: boolean = 42;      // ERROR: integer assigned to boolean
var str_var: string = 42;       // ERROR: integer assigned to string

// ===== CONST WITHOUT INITIALIZATION =====

// Const without initialization (should fail)
const uninitialized_const: integer;  // ERROR: const must be initialized