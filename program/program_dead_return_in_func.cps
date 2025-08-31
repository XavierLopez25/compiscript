function f(): void {
  for (let i: integer = 0; i < 3; i = i + 1) {
    continue;
    print("después de continue");
  }
}
