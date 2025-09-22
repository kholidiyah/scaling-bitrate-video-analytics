# Scaling Bitrate in Video Compression Using Tuned Parameters for Efficient Video Analytics

This repository contains scripts, datasets (links), results, and demo videos accompanying the paper:

**Scaling Bitrate in Video Compression Using Tuned Parameters for Efficient Video Analytics**  
*Kholidiyah Masykuroh, Hendrawan, Eueung Mulyana*  

---

## 📖 Abstract
Efficient video analytics is crucial for smart cities, traffic monitoring, and intelligent transportation systems.  
This work introduces a **dynamic bitrate optimization framework** that fine-tunes video compression parameters —  
Frame Rate (FPS), Resolution, Quantization Parameter (QP), Entropy Coding, Motion Estimation, and Macroblock Partitioning —  
to balance **video quality, computational complexity, and bandwidth efficiency** in resource-constrained environments.

---

### Requirements
- Python 3.7+
- PyTorch 1.9.1
- FFmpeg (2018+)
- Ubuntu 22.04 (tested environment)
- NVIDIA GPU with CUDA 11.1

### Experimental Videos
The following videos were used in computational complexity analysis:
- `traffic72030.mp4` → Traffic dataset (720p, 30 FPS): https://youtu.be/JmJ6tsbEWmw
- `pedestrian72030.mp4` → Pedestrian dataset (720p, 30 FPS): https://youtu.be/bdPKHyiKPV0
