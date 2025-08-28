// ARRAY AND DATA STRUCTURE FAILURE CASES
// These should fail semantic analysis

// ===== ARRAY ELEMENT TYPE INCONSISTENCY =====

// Mixed types in array literal (should fail)
var mixed_array = [1, "hello", true];  // ERROR: inconsistent element types

var mixed_numbers = [1, 2, 3];  // This should be OK with same type
var really_mixed = [1, "string", [1, 2]];  // ERROR: completely different types

// ===== INVALID ARRAY INDEX ACCESS =====

var not_an_array: integer = 42;

// Indexing non-array type (should fail)
var invalid_index = not_an_array[0];  // ERROR: indexing non-array

var string_var: string = "hello";
var string_index = string_var[0];  // ERROR: indexing string (if not supported)

// ===== ARRAY ASSIGNMENT TYPE MISMATCH =====

var int_array: integer[] = [1, 2, 3];

// Assigning wrong type to array element (should fail)
int_array[0] = "hello";  // ERROR: assigning string to integer array element

// Assigning incompatible array (should fail)
var string_array: string[] = ["hello", "world"];
int_array = string_array;  // ERROR: incompatible array types

// ===== MULTIDIMENSIONAL ARRAY ERRORS =====

var matrix: integer[][] = [[1, 2], [3, 4]];

// Wrong dimensions in assignment (should fail)
var wrong_dims: integer[] = matrix;  // ERROR: dimension mismatch


// ===== ARRAY BOUNDS ERRORS =====

var small_array: integer[] = [1, 2, 3];

// This would be runtime error, but some compilers might catch constant index out of bounds
// var out_of_bounds = small_array[10];  // Potential static analysis error