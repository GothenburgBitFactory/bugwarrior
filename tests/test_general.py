import subprocess


class TestGeneral:
    def test_ruff_check(self):
        subprocess.run(['ruff', 'check'], check=True)

    def test_ruff_format(self):
        subprocess.run(['ruff', 'format', '--check'], check=True)

    def test_ty_check(self):
        subprocess.run(['ty', 'check'], check=True)
