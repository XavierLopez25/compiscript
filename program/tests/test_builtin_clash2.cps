// Test: Built-in Function Clash - len
// Expected: Semantic error when trying to redefine 'len'

function len(arr: integer[]): integer {
    // This should fail - 'len' is a built-in
    return 0;
}

let nums: integer[] = [1, 2, 3];
let size: integer = len(nums);
