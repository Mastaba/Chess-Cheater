import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path


class StockfishError(Exception):
    """Base error for Stockfish integration failures."""


class StockfishUnavailable(StockfishError):
    """Raised when a Stockfish executable cannot be found or started."""


class StockfishEngine:
    def __init__(self, executable_path, default_movetime_ms=750):
        self.executable_path = str(executable_path)
        self.default_movetime_ms = default_movetime_ms
        self.process = None
        self._lines = queue.Queue()
        self._reader_thread = None

    @classmethod
    def discover(cls):
        project_root = Path(__file__).resolve().parent
        env_path = os.environ.get("STOCKFISH_PATH")
        candidates = []

        if env_path:
            candidates.append(Path(env_path))

        candidates.extend(
            [
                project_root / "engines" / "stockfish" / "stockfish.exe",
                project_root / "engines" / "stockfish" / "stockfish-windows-x86-64.exe",
                project_root / "engines" / "stockfish" / "stockfish-windows-x86-64-avx2.exe",
                project_root / "engines" / "stockfish" / "stockfish",
                Path("/usr/games/stockfish"),
                Path("/usr/bin/stockfish"),
                Path("/usr/local/bin/stockfish"),
            ]
        )

        for candidate in candidates:
            if candidate.is_file():
                return cls(candidate)

        bundled_engine_dir = project_root / "engines" / "stockfish"
        if bundled_engine_dir.is_dir():
            discovered = sorted(bundled_engine_dir.rglob("stockfish*.exe"))
            if discovered:
                return cls(discovered[0])

        path_on_env = shutil.which("stockfish") or shutil.which("stockfish.exe")
        if path_on_env:
            return cls(path_on_env)

        return None

    def start(self):
        if self.process and self.process.poll() is None:
            return

        try:
            self.process = subprocess.Popen(
                [self.executable_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise StockfishUnavailable(str(exc)) from exc

        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        self._send("uci")
        self._read_until("uciok", timeout=10)
        self._send("isready")
        self._read_until("readyok", timeout=10)

    def best_move(self, fen, movetime_ms=None):
        self.start()
        movetime = movetime_ms or self.default_movetime_ms

        self._send("setoption name MultiPV value 1")
        self._send("isready")
        self._read_until("readyok", timeout=10)
        self._drain_lines()
        self._send(f"position fen {fen}")
        self._send(f"go movetime {movetime}")
        lines = self._read_until("bestmove", timeout=max(5, movetime / 1000 + 5))

        for line in reversed(lines):
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "(none)":
                    return parts[1]
                return None

        return None

    def analyze_top_moves(self, fen, multipv=5, movetime_ms=1200):
        """Return Stockfish's principal variations for the current position."""
        self.start()
        multipv = max(1, min(multipv, 10))
        movetime = movetime_ms or self.default_movetime_ms

        self._send(f"setoption name MultiPV value {multipv}")
        self._send("isready")
        self._read_until("readyok", timeout=10)
        self._drain_lines()
        self._send(f"position fen {fen}")
        self._send(f"go movetime {movetime}")
        lines = self._read_until("bestmove", timeout=max(5, movetime / 1000 + 5))

        variations = {}
        bestmove = None

        for line in lines:
            tokens = line.split()
            if not tokens:
                continue

            if tokens[0] == "bestmove" and len(tokens) >= 2:
                bestmove = tokens[1]
                continue

            if tokens[0] != "info" or "pv" not in tokens:
                continue

            pv_index = tokens.index("pv")
            pv = tokens[pv_index + 1:]
            if not pv:
                continue

            variation_number = self._read_int_token(tokens, "multipv", default=1)
            score = self._read_score(tokens)
            depth = self._read_int_token(tokens, "depth", default=None)

            variations[variation_number] = {
                "rank": variation_number,
                "move": pv[0],
                "pv": pv,
                "score": score,
                "depth": depth,
            }

        ordered = [variations[key] for key in sorted(variations)]
        if not ordered and bestmove and bestmove != "(none)":
            ordered.append(
                {
                    "rank": 1,
                    "move": bestmove,
                    "pv": [bestmove],
                    "score": "",
                    "depth": None,
                }
            )

        return ordered

    def close(self):
        if not self.process:
            return

        if self.process.poll() is None:
            try:
                self._send("quit")
                self.process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired, StockfishError):
                self.process.terminate()

        self.process = None

    def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            self._lines.put(line.strip())

    def _send(self, command):
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            raise StockfishUnavailable("Stockfish process is not running.")

        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _read_until(self, prefix, timeout):
        deadline = time.monotonic() + timeout
        lines = []

        while time.monotonic() < deadline:
            if self.process and self.process.poll() is not None:
                raise StockfishUnavailable("Stockfish exited unexpectedly.")

            remaining = max(0.01, deadline - time.monotonic())
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                break

            lines.append(line)
            if line.startswith(prefix):
                return lines

        raise StockfishError(f"Timed out waiting for {prefix!r} from Stockfish.")

    def _drain_lines(self):
        while True:
            try:
                self._lines.get_nowait()
            except queue.Empty:
                return

    def _read_int_token(self, tokens, name, default):
        if name not in tokens:
            return default

        index = tokens.index(name) + 1
        if index >= len(tokens):
            return default

        try:
            return int(tokens[index])
        except ValueError:
            return default

    def _read_score(self, tokens):
        if "score" not in tokens:
            return ""

        index = tokens.index("score")
        if index + 2 >= len(tokens):
            return ""

        score_type = tokens[index + 1]
        score_value = tokens[index + 2]

        if score_type == "cp":
            try:
                return f"{int(score_value) / 100:+.2f}"
            except ValueError:
                return score_value

        if score_type == "mate":
            return f"M{score_value}"

        return f"{score_type} {score_value}"
