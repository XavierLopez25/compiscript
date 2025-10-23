// Test: Built-in Function Clash - array
// Expected: Semantic error when trying to redefine 'array'

function array(size: integer): integer[] {
    // This should fail - 'array' is a built-in constructor
    let result: integer[] = [1, 2, 3];
    return result;
}

let myArray: integer[] = array(5);
