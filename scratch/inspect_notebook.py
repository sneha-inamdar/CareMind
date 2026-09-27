import json

with open('CareMind_PhysioNet2019_Exploration.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

out_lines = []
out_lines.append(f"Total cells in notebook: {len(nb['cells'])}\n")
for i, cell in enumerate(nb['cells']):
    ctype = cell.get('cell_type')
    src = ''.join(cell.get('source', []))
    out_lines.append(f"==================== CELL {i+1} ({ctype}) ====================")
    out_lines.append(src)
    if 'outputs' in cell and cell['outputs']:
        out_lines.append("---- OUTPUTS ----")
        for out in cell['outputs']:
            if 'text' in out:
                out_lines.append(''.join(out['text']))
            elif 'data' in out and 'text/plain' in out['data']:
                out_lines.append(''.join(out['data']['text/plain']))
    out_lines.append("\n")

with open('scratch/notebook_summary.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))

print("Notebook dumped to scratch/notebook_summary.txt successfully!")
