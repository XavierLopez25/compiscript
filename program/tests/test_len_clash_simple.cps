// Test simplificado: redefinir 'len' como función

function len(x: integer): integer {
    return x;
}

let nums: integer[] = [1, 2, 3];
let size: integer = len(nums);
