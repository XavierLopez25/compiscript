// Test: Built-in Function Clash in Class Methods
// Expected: Semantic error when using built-in name as method

class MyClass {
    let value: integer;

    function constructor(val: integer) {
        this.value = val;
    }

    // This should fail - 'print' is a built-in
    function print(): void {
        // Cannot use built-in name as method
    }
}

let obj: MyClass = new MyClass(42);
obj.print();
