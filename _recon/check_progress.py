import os, json
VINS = {
  "12F02860006B001": "CLG942EHKSE917908",
  "68F00030217B001": "CLG890HZTSL831819",
}
# discover actual model dirs under rawdata
for d in sorted(os.listdir("rawdata")):
    p = f"rawdata/{d}"
    if not os.path.isdir(p): continue
    meta_path = f"{p}/machine.json"
    detail_dir = f"{p}/partinfo"
    photo_dir = f"{p}/photos"
    ndet = len(os.listdir(detail_dir)) if os.path.isdir(detail_dir) else 0
    nphoto = len(os.listdir(photo_dir)) if os.path.isdir(photo_dir) else 0
    vin = "?"
    if os.path.exists(meta_path):
        try:
            m = json.load(open(meta_path, encoding="utf-8"))
            vin = m.get("vin","?")
        except: pass
    print(d, "vin=", vin, "details=", ndet, "photos=", nphoto)
