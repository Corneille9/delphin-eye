#!/usr/bin/env bash
# Wrap the PyInstaller onedir bundle into a .deb.
#
# The point of the package is Depends:: apt pulls in the GTK/WebKit libraries
# the native window needs, which is what a plain tarball cannot do.
#
# Usage: packaging/build_deb.sh <version> [dist-dir] [output.deb]
set -euo pipefail

VERSION="${1:?usage: build_deb.sh <version> [dist-dir] [output.deb]}"
VERSION="${VERSION#v}"
DIST="${2:-dist/DelphinEye}"
OUTPUT="${3:-delphin-eye_${VERSION}_amd64.deb}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

[ -d "$ROOT/$DIST" ] || { echo "bundle introuvable : $ROOT/$DIST" >&2; exit 1; }

install -d "$STAGE/opt/delphin-eye" "$STAGE/usr/bin" \
           "$STAGE/usr/share/applications" \
           "$STAGE/usr/share/icons/hicolor/512x512/apps" \
           "$STAGE/DEBIAN"

cp -a "$ROOT/$DIST/." "$STAGE/opt/delphin-eye/"
cp "$ROOT/src/assets/web-app-manifest-512x512.png" \
   "$STAGE/usr/share/icons/hicolor/512x512/apps/delphin-eye.png"
ln -s /opt/delphin-eye/DelphinEye "$STAGE/usr/bin/delphin-eye"

cat > "$STAGE/usr/share/applications/delphin-eye.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Delphin Eye
Comment=Détection des nageoires dorsales de dauphins par photo-identification
Exec=/opt/delphin-eye/DelphinEye
Icon=delphin-eye
Terminal=false
Categories=Science;Education;
DESKTOP

# python3-gi is pinned to the interpreter the bundle was frozen with: its
# compiled _gi module only loads into a matching Python 3.x. Installing on a
# distribution with another python3 would silently fall back to the browser.
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: delphin-eye
Version: ${VERSION}
Section: science
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.12), python3 (<< 3.13), python3-gi, gir1.2-webkit2-4.1, libwebkit2gtk-4.1-0
Recommends: python3-gi-cairo
Maintainer: GEPOG <davidmahudagba@gmail.com>
Description: Détection automatique des nageoires dorsales de dauphins
 Delphin Eye localise les nageoires dorsales sur des photographies grâce à un
 modèle YOLO, permet de corriger les détections à la main et exporte les
 résultats pour la photo-identification individuelle.
CONTROL

echo "Installed-Size: $(du -sk "$STAGE" | cut -f1)" >> "$STAGE/DEBIAN/control"

dpkg-deb --build --root-owner-group "$STAGE" "$ROOT/$OUTPUT" >/dev/null
echo "$ROOT/$OUTPUT"
