import json

with open("ativos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

new_data = []
for a in data:
    codigo = str(a.get("codigo", "")).upper()
    if codigo.endswith("F"):
        continue

    if any(codigo.endswith(s) for s in ["31", "32", "33", "34", "35", "39"]):
        a["tipo"] = "bdrs"
    elif codigo.endswith("11"):
        a["tipo"] = "fiis"

    new_data.append(a)

with open("ativos.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=4)

print(f"Limpeza completa. Ativos reduzidos de {len(data)} para {len(new_data)}")
