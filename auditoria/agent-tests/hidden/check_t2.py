import sys, subprocess
d = sys.argv[1]; sys.path.insert(0, d)
from conversor.core import celsius_para_fahrenheit, fahrenheit_para_celsius
assert abs(celsius_para_fahrenheit(100) - 212) < 1e-6 and abs(fahrenheit_para_celsius(32)) < 1e-6
for f, v in ((celsius_para_fahrenheit, -300), (fahrenheit_para_celsius, -500)):
    try:
        f(v); raise SystemExit("faltou ValueError abaixo do zero absoluto")
    except ValueError:
        pass
out = subprocess.run([sys.executable, "-m", "conversor", "c2f", "100"], capture_output=True, text=True, cwd=d)
assert "212" in out.stdout, ("CLI", out.stdout, out.stderr[-300:])
bad = subprocess.run([sys.executable, "-m", "conversor", "c2f", "abc"], capture_output=True, text=True, cwd=d)
assert bad.returncode != 0 and "Traceback" not in bad.stderr, ("erro amigavel", bad.returncode, bad.stderr[-300:])
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."], capture_output=True, text=True, cwd=d)
assert r.returncode == 0 and "Ran 0 tests" not in r.stderr, r.stderr[-500:]
print("T2_OK")
