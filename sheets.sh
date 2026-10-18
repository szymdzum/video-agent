#!/usr/bin/env bash
# Contact sheets: one frame every N seconds, 5x4 per sheet (frame k of sheet s = second ((s-1)*20 + k-1) * N).
# Usage: sheets.sh <out_dir> [every_seconds=2] clip1.mp4 [clip2.mp4 ...]
set -euo pipefail
out=$1; shift; every=2
[[ $1 =~ ^[0-9.]+$ ]] && { every=$1; shift; }
mkdir -p "$out"
for f in "$@"; do
  n=$(basename "${f%.*}")
  ffmpeg -v error -y -i "$f" -map 0:v:0 -vf "fps=1/$every,scale=400:-1,tile=5x4:padding=4:color=white" "$out/${n}_%02d.jpg"
  echo "$n: $(ls "$out/${n}"_*.jpg | wc -l | tr -d ' ') sheet(s), ${every}s/frame"
done
