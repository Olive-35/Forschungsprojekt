with open("input.jsonl", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

with open("output.json", "w", encoding="utf-8") as f:
    f.write("[\n")
    f.write(",\n".join(lines))
    f.write("\n]")