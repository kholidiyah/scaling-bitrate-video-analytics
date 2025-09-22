#!/usr/bin/env python3
import subprocess, shlex, re, json

VIDEO = "traffic_720p30.mp4"   # ganti sesuai kebutuhan
QP, FPS, GOP = 30, 30, 60

def ffprobe_frames(path):
    out = subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,avg_frame_rate,nb_frames",
        "-show_entries","format=duration","-of","json", path
    ]).decode()
    data = json.loads(out); st=data["streams"][0]; fmt=data["format"]
    w,h=int(st["width"]),int(st["height"])
    n,d=st["avg_frame_rate"].split("/")
    fps=float(n)/float(d)
    dur=float(fmt["duration"])
    nb = st.get("nb_frames","0")
    if nb in ("0","N/A"): nb=int(round(dur*fps))
    else: nb=int(nb)
    MP=(w*h)/1e6
    return nb, MP

def parse_time(text):
    m=re.search(r"Elapsed \(wall clock\).*:\s*([0-9:\.]+)", text)
    def tosec(x):
        p=x.split(":")
        if len(p)==3: return int(p[0])*3600 + int(p[1])*60 + float(p[2])
        if len(p)==2: return int(p[0])*60 + float(p[1])
        return float(x)
    return tosec(m.group(1)) if m else None

def run(name, x264_params):
    out = f"/usr/bin/time -v ffmpeg -y -i {shlex.quote(VIDEO)} -c:v libx264 -qp {QP} -r {FPS} -g {GOP} -profile:v high -pix_fmt yuv420p -x264-params {x264_params} -f mp4 /dev/null"
    res = subprocess.run(out, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    el = parse_time(res.stdout)
    return el

if __name__=="__main__":
    frames, MP = ffprobe_frames(VIDEO)
    configs = {
        "CAVLC+dia+p16x16": "cabac=0:me=dia:subme=4:partitions=p16x16,none",
        "CABAC+dia+p16x16": "cabac=1:me=dia:subme=4:partitions=p16x16,none",
    }
    baseline_key = "CAVLC+dia+p16x16"
    results = {}
    for k,v in configs.items():
        el = run(k, v)
        tpf = el/frames*1000.0
        tpmpf = el/(frames*MP)*1000.0
        results[k] = (el, tpf, tpmpf)

    base_tpmpf = results[baseline_key][2]
    print("\n=== Hasil (ms) ===")
    for k,(el,tpf,tpmpf) in results.items():
        rc = 100.0*tpmpf/base_tpmpf
        print(f"{k:25s} | time/frame={tpf:.2f} | time/MP/frame={tpmpf:.2f} | RC={rc:.1f}%")
