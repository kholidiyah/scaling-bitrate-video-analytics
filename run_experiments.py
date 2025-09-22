#!/usr/bin/env python3
import subprocess, shlex, re, csv, math, json
from pathlib import Path
from datetime import datetime

# ====== (A) DAFTAR KLIP SAMPEL ======
# Ganti path ke klipmu (T1 = traffic, P1 = pedestrian)
CLIPS = [
    {"id": "T1", "path": "traffic_720p30.mp4"},
    {"id": "P1", "path": "pedestrian_720p30.mp4"},
]

# ====== (B) SETELAN KUNCI (DIKUNCI SERAGAM) ======
QP = 30
FPS = 30
GOP = 60
PIX_FMT = "yuv420p"
PROFILE = "high"
X264_BASE = f"-qp {QP} -r {FPS} -g {GOP} -profile:v {PROFILE} -pix_fmt {PIX_FMT}"

# ====== (C) KONFIGURASI UJI (ENTROPY / ME / PARTITIONING) ======
# Satu knob berubah, lainnya dijaga tetap.
TESTS = [
    # --- Entropy coding (A) ---
    {"group":"entropy", "name":"CAVLC + dia + p16x16",
     "x264":"cabac=0:me=dia:subme=4:partitions=p16x16,none"},
    {"group":"entropy", "name":"CABAC + dia + p16x16",
     "x264":"cabac=1:me=dia:subme=4:partitions=p16x16,none"},

    # --- Motion estimation (B) ---
    {"group":"me", "name":"CABAC + diamond + p16x16",
     "x264":"cabac=1:me=dia:subme=4:partitions=p16x16,none"},
    {"group":"me", "name":"CABAC + hex + p16x16",
     "x264":"cabac=1:me=hex:subme=6:partitions=p16x16,none"},
    {"group":"me", "name":"CABAC + umh + p16x16",
     "x264":"cabac=1:me=umh:subme=7:partitions=p16x16,none"},
    {"group":"me", "name":"CABAC + esa + p16x16",
     "x264":"cabac=1:me=esa:subme=7:partitions=p16x16,none"},

    # --- Macroblock partitioning (C) ---
    {"group":"part", "name":"CABAC + dia + p16x16",
     "x264":"cabac=1:me=dia:subme=4:partitions=p16x16,none"},
    {"group":"part", "name":"CABAC + dia + p8x8,b8x8,i8x8",
     "x264":"cabac=1:me=dia:subme=7:partitions=p8x8,b8x8,i8x8"},
    {"group":"part", "name":"CABAC + dia + p4x4,b4x4,i4x4",
     "x264":"cabac=1:me=dia:subme=7:partitions=p4x4,b4x4,i4x4"},
]

REPEATS = 3  # jalankan 3x ambil median nanti

# ====== (D) UTIL ======
def ffprobe_info(path):
    """kembalikan width, height, fps_num/fps_den, dur (s), nb_frames (estimasi kalau N/A)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames",
        "-show_entries", "format=duration",
        "-of", "json", path
    ]
    out = subprocess.check_output(cmd).decode("utf-8")
    data = json.loads(out)
    st = data["streams"][0]
    fmt = data["format"]
    w, h = int(st["width"]), int(st["height"])
    fr = st.get("avg_frame_rate", "0/0")
    n, d = fr.split("/")
    fps = float(n)/float(d) if d != "0" else float(FPS)
    dur = float(fmt.get("duration", 0.0))
    nb = st.get("nb_frames", "0")
    if nb in ("0", "N/A", "", None) and dur > 0 and fps > 0:
        nb = int(round(dur * fps))
    else:
        nb = int(nb)
    return w, h, fps, dur, nb

def parse_time_v(text):
    """ambil elapsed(s), user(s), sys(s), maxrss(kB) dari output /usr/bin/time -v"""
    def get(pattern, default=None, conv=lambda x:x):
        m = re.search(pattern, text)
        return conv(m.group(1)) if m else default
    # Elapsed format: H:MM:SS or M:SS
    elapsed = get(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([0-9:\.]+)")
    def to_seconds(s):
        parts = s.split(":")
        if len(parts)==3:
            h,m,sec = int(parts[0]), int(parts[1]), float(parts[2])
            return h*3600 + m*60 + sec
        elif len(parts)==2:
            m,sec = int(parts[0]), float(parts[1])
            return m*60 + sec
        return float(s)
    elapsed_s = to_seconds(elapsed) if elapsed else None
    user_s   = get(r"User time \(seconds\):\s*([\d\.]+)", conv=float)
    sys_s    = get(r"System time \(seconds\):\s*([\d\.]+)", conv=float)
    maxrss_kb= get(r"Maximum resident set size \(kbytes\):\s*([\d]+)", conv=int)
    return elapsed_s, user_s, sys_s, maxrss_kb

def median(lst):
    s = sorted(x for x in lst if x is not None)
    n = len(s)
    if n==0: return None
    mid = n//2
    return (s[mid-1]+s[mid])/2 if n%2==0 else s[mid]

# ====== (E) EKSEKUSI ======
outdir = Path("exp_logs"); outdir.mkdir(exist_ok=True)
csv_path = Path("complexity_raw.csv")

with csv_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ts","clip_id","clip_path","group","name","repeat",
                "width","height","fps","duration_s","frames",
                "elapsed_s","user_s","sys_s","maxrss_kb",
                "time_per_frame_ms","time_per_MP_per_frame_ms",
                "bitrate_Mbps","psnr_dB"])  # bitrate/PSNR opsional (isi 0 dulu)

    for clip in CLIPS:
        w0, h0, fps0, dur0, nb0 = ffprobe_info(clip["path"])
        MP = (w0*h0)/1e6

        for test in TESTS:
            # siapkan command
            x264_params = f"-x264-params {test['x264']}"
            out_video = outdir / f"{clip['id']}__{test['name'].replace(' ','_').replace('/','_')}.mp4"

            times, users, syss, rss = [], [], [], []

            for r in range(1, REPEATS+1):
                log_file = outdir / f"log__{clip['id']}__{test['name'].replace(' ','_').replace('/','_')}__r{r}.txt"
                cmd = f"/usr/bin/time -v ffmpeg -y -i {shlex.quote(clip['path'])} -c:v libx264 {X264_BASE} {x264_params} -f mp4 {shlex.quote(str(out_video))}"
                print("RUN:", cmd)
                proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                log_text = proc.stdout
                log_file.write_text(log_text)
                el,user,sy,maxrss = parse_time_v(log_text)
                times.append(el); users.append(user); syss.append(sy); rss.append(maxrss)

            el_m = median(times); user_m = median(users); sys_m = median(syss); rss_m = median(rss)
            tpf_ms  = (el_m / nb0 * 1000.0) if (el_m and nb0>0) else None
            tpmpf_ms= (el_m / (nb0*MP) * 1000.0) if (el_m and nb0>0 and MP>0) else None

            w.writerow([datetime.now().isoformat(), clip["id"], clip["path"], test["group"], test["name"], REPEATS,
                        w0, h0, round(fps0,3), round(dur0,3), nb0,
                        round(el_m,6) if el_m else "", round(user_m,6) if user_m else "",
                        round(sys_m,6) if sys_m else "", rss_m if rss_m else "",
                        round(tpf_ms,6) if tpf_ms else "", round(tpmpf_ms,6) if tpmpf_ms else "",
                        "", ""  # bitrate/PSNR bisa diisi nanti jika diukur
                        ])
print(f"\nSelesai. Hasil mentah → {csv_path}")
