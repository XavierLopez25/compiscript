// Test: Built-in Function Clash Validation
// This file should produce SEMANTIC ERRORS when analyzed

// TEST 1: Redefining 'print' function
// Expected: Error - "Cannot redefine built-in function 'print'"
function print(msg: string): void {
    // This should fail during semantic analysis
}

// This line should never be reached due to error above
print("Hello");
