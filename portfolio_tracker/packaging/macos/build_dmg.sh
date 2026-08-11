#!/usr/bin/env bash
set -euo pipefail

dist_dir="${1:-dist}"
release_dir="${2:-release}"
version="${3:-1.0.0}"
app_name="Portföy Takip.app"
app_path="${dist_dir}/${app_name}"

if [[ ! -d "${app_path}" ]]; then
    echo "Uygulama paketi bulunamadı: ${app_path}" >&2
    exit 1
fi

architecture="$(uname -m)"
mkdir -p "${release_dir}"
release_dir="$(cd "${release_dir}" && pwd)"
dmg_path="${release_dir}/PortfolioTracker-${version}-macOS-${architecture}.dmg"
staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/portfolio-tracker-dmg.XXXXXX")"

cleanup() {
    rm -rf "${staging_dir}"
}
trap cleanup EXIT

ditto "${app_path}" "${staging_dir}/${app_name}"
ln -s /Applications "${staging_dir}/Applications"
codesign --verify --deep --strict "${staging_dir}/${app_name}"
hdiutil create \
    -volname "Portföy Takip" \
    -srcfolder "${staging_dir}" \
    -format UDZO \
    -ov \
    "${dmg_path}"
hdiutil verify "${dmg_path}"
shasum -a 256 "${dmg_path}" > "${dmg_path}.sha256"

echo "DMG hazır: ${dmg_path}"
