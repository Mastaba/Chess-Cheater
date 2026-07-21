#!/usr/bin/env bash
set -euo pipefail

APP_ID="chess-cheater"
APP_NAME="Chess Cheater"
VERSION="${1:-0.1.0}"
ARCH="${ARCH:-all}"
MAINTAINER="${MAINTAINER:-Chess Cheater Maintainers <noreply@example.com>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_ROOT="$PROJECT_ROOT/dist/deb/${APP_ID}_${VERSION}_${ARCH}"
PKG_ROOT="$BUILD_ROOT/pkg"
OUT_DEB="$PROJECT_ROOT/dist/${APP_ID}_${VERSION}_${ARCH}.deb"
APP_ROOT="$PKG_ROOT/opt/chess-cheater"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb is required. Build this on Debian, Ubuntu, or WSL with dpkg-deb installed." >&2
  exit 1
fi

rm -rf "$BUILD_ROOT"
mkdir -p "$APP_ROOT" "$PKG_ROOT/DEBIAN"

install -Dm644 "$PROJECT_ROOT/main.py" "$APP_ROOT/main.py"
install -Dm644 "$PROJECT_ROOT/stockfish_engine.py" "$APP_ROOT/stockfish_engine.py"
install -Dm644 "$PROJECT_ROOT/README.md" "$APP_ROOT/README.md"
install -Dm644 "$PROJECT_ROOT/LICENSE" "$APP_ROOT/LICENSE"

cp -a "$PROJECT_ROOT/assets" "$APP_ROOT/assets"
cp -a "$PROJECT_ROOT/images" "$APP_ROOT/images"
cp -a "$PROJECT_ROOT/openings" "$APP_ROOT/openings"

if compgen -G "$PROJECT_ROOT/ChatGPT Image*.png" >/dev/null; then
  cp "$PROJECT_ROOT"/ChatGPT\ Image*.png "$APP_ROOT/"
fi

install -Dm755 "$SCRIPT_DIR/chess-cheater" "$PKG_ROOT/usr/bin/chess-cheater"
install -Dm644 "$SCRIPT_DIR/chess-cheater.desktop" "$PKG_ROOT/usr/share/applications/chess-cheater.desktop"

cat > "$PKG_ROOT/DEBIAN/control" <<CONTROL
Package: $APP_ID
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Depends: python3 (>= 3.10), python3-pygame, python3-tk, stockfish
Description: Local chess opening study and Stockfish analysis tool
 $APP_NAME is a local chess learning app for reviewing games, exploring
 openings, and analyzing positions with Stockfish. It is not intended for
 use during live games or anywhere engine assistance is against the rules.
CONTROL

mkdir -p "$(dirname "$OUT_DEB")"
dpkg-deb --build "$PKG_ROOT" "$OUT_DEB"
echo "Built $OUT_DEB"
