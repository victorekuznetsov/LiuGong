import os, json

MODEL = {
 "08F0096C011B002": ("9125F",  "экскаватор"),
 "10F0302C007B001": ("922FW",  "экскаватор"),
 "12F01890011B001": ("975F",   "экскаватор"),
 "12F02860006B001": ("942EHD", "экскаватор"),
 "23F00630017B002": ("6614E",  "каток"),
 "65F01260034B001": ("862H",   "погрузчик"),
 "68F00030217B001": ("890H",   "погрузчик"),
 "69F00080022B001": ("8128H",  "погрузчик"),
}

def nfiles(p):
    n = 0
    for _, _, fs in os.walk(p):
        n += len(fs)
    return n

print(f"{'модель':9} {'тип':11} {'узлы':>6} {'черт.':>6} {'карточки':>9} {'фото':>6}  статус")
print("-" * 68)
tot = [0, 0, 0, 0]
for d, (model, kind) in MODEL.items():
    p = f"rawdata/{d}"
    legends = 0
    lp = f"{p}/legends.json"
    if os.path.exists(lp):
        try:
            legends = len(json.load(open(lp, encoding="utf-8")))
        except Exception:
            pass
    draw  = nfiles(f"{p}/drawings")
    cards = nfiles(f"{p}/partinfo")
    ph    = nfiles(f"{p}/photos")
    st = "готово" if cards and draw else ("нет карточек" if draw else "частично")
    print(f"{model:9} {kind:11} {legends:>6} {draw:>6} {cards:>9} {ph:>6}  {st}")
    for i, v in enumerate([legends, draw, cards, ph]):
        tot[i] += v
print("-" * 68)
print(f"{'ИТОГО':9} {'':11} {tot[0]:>6} {tot[1]:>6} {tot[2]:>9} {tot[3]:>6}")
