// Test: Scoped Variables Memory Annotation
// This test should PASS and generate correct scopes.json with memory assignments

// Global variable
let x: integer = 10;
print("Global x: " + x);

// Nested block with shadowing
{
    let x: integer = 20;  // This should have memory_address assigned
    let y: integer = 30;  // This should also have memory_address
    print("Nested x: " + x);
    print("Nested y: " + y);
}

print("Global x again: " + x);

// For loop variable
for (let i: integer = 0; i < 3; i = i + 1) {
    // 'i' should have memory_address assigned
    print("Loop i: " + i);
}

// Switch case variable
let n: integer = 1;
switch (n) {
    case 1:
        let k: integer = 100;  // Should have memory_address
        print("k in case 1: " + k);
    default:
        print("default");
}

// Try-catch variables
try {
    let risky: integer = 42;  // Should have memory_address
    print("risky: " + risky);
} catch (err) {
    // 'err' should have memory_address
    print("Error: " + err);
}

print("Test completed successfully!");
