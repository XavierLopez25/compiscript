// Test: Nested Functions with Proper Scoping
// Validates that nested functions work correctly with memory annotation

let globalVar: integer = 100;

function outer(): integer {
    let outerVar: integer = 200;
    print("Outer function");
    return outerVar;
}

// Block with nested function declaration
{
    function inner(): integer {
        let innerVar: integer = 300;
        print("Inner function");
        return innerVar;
    }

    let result: integer = inner();
    print("Inner result: " + result);
}

let outerResult: integer = outer();
print("Outer result: " + outerResult);

print("Nested functions test completed!");
