import sys, os, subprocess
d = sys.argv[1]; sys.path.insert(0, d)
from digitos import soma_digitos
assert soma_digitos(0) == 0 and soma_digitos(12345) == 15 and soma_digitos(-907) == 16 and soma_digitos(9) == 9
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", d, "-p", "test*.py"], capture_output=True, text=True, cwd=d)
assert r.returncode == 0 and "Ran 0 tests" not in r.stderr, r.stderr[-500:]
print("T1_OK")
