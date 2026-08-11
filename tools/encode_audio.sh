#!/usr/bin/env bash
# audio/wav/*.wav -> audio/*.m4a
#
# AAC in an .m4a container, because it decodes everywhere the campaign runs
# including iOS Safari, with no second fallback file to ship. See SOUND.md.
#
# afconvert is part of macOS -- no brew install needed. The loop stems get a
# higher bitrate because they are music and they are on screen the longest;
# everything else is a short mono one-shot where 64k is transparent enough.
#
#   tools/encode_audio.sh
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p audio
[ -d audio/wav ] || { echo "run tools/make_audio.py first" >&2; exit 1; }

# VBR, not CBR: under CBR the size is just bitrate x duration, so the encoder
# cannot spend less on the tonal angklung bed than on the broadband crowd wash.
# Quality is set per asset by what the asset has to survive.
total=0
for src in audio/wav/*.wav; do
  name=$(basename "$src" .wav)
  case "$name" in
    pulse)  q=70 ;;   # drum transients, and it is the tap grid -- do not smear it
    hook)   q=55 ;;   # tonal brass, cheap for VBR
    payoff) q=55 ;;
    sfx)    q=60 ;;   # short transients, but 14 cues share one file
    bed)    q=45 ;;   # tonal and quiet
    crowd)  q=35 ;;   # a -26 dBFS noise wash; nobody can hear the artefacts
    *)      q=55 ;;
  esac
  out="audio/$name.m4a"
  afconvert -f m4af -d aac -s 3 -u vbrq "$q" "$src" "$out"
  bytes=$(stat -f%z "$out")
  total=$((total + bytes))
  printf '  %-14s %6.1f KB  vbrq %d\n' "$name.m4a" "$(echo "$bytes" | awk '{print $1/1024}')" "$q"
done

printf '\n  %-14s %6.1f KB   (SOUND.md budget: 200 KB)\n' "TOTAL" \
  "$(echo "$total" | awk '{print $1/1024}')"
