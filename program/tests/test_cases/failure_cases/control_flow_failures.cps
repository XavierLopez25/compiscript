// CONTROL FLOW FAILURE CASES
// These should fail semantic analysis

// ===== NON-BOOLEAN CONDITIONS =====

var number: integer = 5;
var str: string = "test";

// Non-boolean condition in if statement (should fail)
if (number) {  // ERROR: integer used as condition
    // body
}

if (str) {  // ERROR: string used as condition
    // body
}

// Non-boolean condition in while loop (should fail)
while (number) {  // ERROR: integer used as condition
    number = number - 1;
}

// Non-boolean condition in for loop (should fail)
for (var i: integer = 0; number; i = i + 1) {  // ERROR: integer used as condition
    // body
}

// ===== BREAK AND CONTINUE OUTSIDE LOOPS =====

// Break outside loop (should fail)
function test_break(): void {
    break;  // ERROR: break outside loop
}

// Continue outside loop (should fail)
function test_continue(): void {
    continue;  // ERROR: continue outside loop
}

// Break in function but not in loop (should fail)
function another_test(): void {
    if (true) {
        break;  // ERROR: break not in loop
    }
}

// ===== RETURN OUTSIDE FUNCTION =====

// Return statement in global scope (should fail)
return 42;  // ERROR: return outside function


// ===== INVALID SWITCH CASES =====

var test_value: integer = 5;

switch (test_value) {
    case "string":  // ERROR: case type doesn't match switch expression type
        break;
    default:
        break;
}