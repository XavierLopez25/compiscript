// Test: Array Memory Management
// This test validates that arrays are correctly handled in memory

// Simple array
let numbers: integer[] = [1, 2, 3, 4, 5];
print("First number: " + numbers[0]);

// Multidimensional array
let matrix: integer[][] = [[1, 2], [3, 4]];
print("Matrix element: " + matrix[0][0]);

// Array as function parameter
function sumFirst(arr: integer[]): integer {
    // 'arr' is a pointer (4 bytes) to heap-allocated array
    if (len(arr) > 0) {
        return arr[0];
    }
    return 0;
}

let result: integer = sumFirst(numbers);
print("Sum result: " + result);

// Array returned from function
function createArray(n: integer): integer[] {
    let arr: integer[] = [n, n * 2, n * 3];
    return arr;  // Returns pointer
}

let myArray: integer[] = createArray(5);
print("Created array first: " + myArray[0]);

print("Array memory test completed!");
