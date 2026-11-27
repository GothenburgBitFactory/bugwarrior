#!/usr/bin/env bash
set -euo pipefail

taskwarrior_version="${1:?Usage: build-taskwarrior.sh <version>}"
taskwarrior_source="${RUNNER_TEMP}/taskwarrior"

sudo apt-get update -qq
sudo apt-get install -qq -y \
  build-essential \
  cmake \
  libgnutls28-dev \
  uuid-dev

git clone --branch "v${taskwarrior_version}" --depth 1 \
  https://github.com/GothenburgBitFactory/taskwarrior.git \
  "${taskwarrior_source}"
cmake -S "${taskwarrior_source}" -B "${taskwarrior_source}/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/opt/taskwarrior \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# https://www.mail-archive.com/debian-bugs-rc%40lists.debian.org/msg727626.html
if [[ "${taskwarrior_version}" == "2.6.2" ]]; then
  sed -i '/#include <Pig.h>/a #include <cstdint>' \
    "${taskwarrior_source}/src/libshared/src/JSON.h"
fi

cmake --build "${taskwarrior_source}/build" --parallel "$(nproc)"
sudo cmake --install "${taskwarrior_source}/build"
/opt/taskwarrior/bin/task --version
sudo tar -C /opt/taskwarrior -czf \
  "${RUNNER_TEMP}/taskwarrior-${taskwarrior_version}.tar.gz" .
