"""Testes offline: nenhum modelo ou download necessario."""
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "auditoria" / "scripts"))
import common  # noqa: E402


class BenchmarkModelTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(common)

    def test_2b_usa_id_do_servidor_e_nao_4b(self):
        with mock.patch.dict(os.environ, {"BONSAI_MODEL": "bonsai-2-2b"}):
            importlib.reload(common)
            with mock.patch.object(common, "get", return_value={"data": [{"id": "bonsai-2-2b"}]}) as probe:
                with mock.patch.object(common, "post", return_value={"choices": []}) as post:
                    common.chat([{"role": "user", "content": "teste"}])
                    common.chat([{"role": "user", "content": "teste 2"}])
                    self.assertEqual(post.call_args.args[1]["model"], "bonsai-2-2b")
                    probe.assert_called_once_with("/v1/models")

    def test_falha_antes_de_enviar_ao_modelo_errado(self):
        with mock.patch.dict(os.environ, {"BONSAI_MODEL": "bonsai-2-2b"}):
            importlib.reload(common)
            with mock.patch.object(common, "get", return_value={"data": [{"id": "bonsai-2-4b"}]}):
                with mock.patch.object(common, "post") as post:
                    with self.assertRaisesRegex(RuntimeError, "bonsai-2-2b"):
                        common.chat([{"role": "user", "content": "teste"}])
                    post.assert_not_called()

    def test_nome_de_modelo_vazio_falha(self):
        with mock.patch.dict(os.environ, {"BONSAI_MODEL": "  "}):
            with self.assertRaisesRegex(ValueError, "BONSAI_MODEL"):
                importlib.reload(common)


class LinuxMemoryTests(unittest.TestCase):
    def test_proc_retornar_rss_sem_fingir_private_commit(self):
        fake = {
            "server.pid": "135\n",
            "/proc/135/status": "Name:\tllama-server\nVmRSS:\t524288 kB\n",
            "/proc/135/stat": "135 (llama-server) S " + " ".join(["0"] * 30),
            "/proc/meminfo": "MemAvailable: 2097152 kB\n",
        }

        def fake_open(name, *args, **kwargs):
            name = str(name)
            key = "server.pid" if name.endswith("/logs/server.pid") else name
            return io.StringIO(fake[key])

        with mock.patch("builtins.open", side_effect=fake_open), mock.patch.object(
            common.os.path, "realpath", return_value="/opt/bonsai/llama-server"
        ):
            result = common._linux_proc_stats()
        self.assertEqual(result["ws_mb"], 512)
        self.assertEqual(result["free_mb"], 2048)
        self.assertIsNone(result["priv_mb"])
        self.assertEqual(result["cpu_s"], 0.0)

    def test_nao_atribui_pid_de_outro_programa_ao_modelo(self):
        with mock.patch("builtins.open", return_value=io.StringIO("135")), mock.patch.object(
            common.os.path, "realpath", return_value="/usr/bin/python3"
        ):
            result = common._linux_proc_stats()
        self.assertIn("nao pertence", result["erro"])
        self.assertIsNone(result["ws_mb"])


class OfflineScriptTests(unittest.TestCase):
    def test_start_linux_rejeita_modelo_invalido(self):
        proc = subprocess.run(
            ["bash", str(REPO / "linux" / "iniciar-bonsai.sh"), "--modelo", "3B"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Modelo invalido", proc.stderr)

    def test_setup_linux_rejeita_flag_antes_de_baixar(self):
        proc = subprocess.run(
            ["bash", str(REPO / "linux" / "setup-linux.sh"), "--nao-existe"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Uso:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
