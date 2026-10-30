import contextlib
import io
import json
import unittest

from agent_system.interfaces.cli import main


class CliTests(unittest.TestCase):
    def test_status_does_not_claim_operational_readiness(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["status"])
        self.assertEqual(code, 0)
        status = json.loads(output.getvalue())
        self.assertFalse(status["operational"])
        self.assertEqual(status["stage"], "installer_foundation")

    def test_unimplemented_install_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["install"])
        self.assertEqual(error.exception.code, 2)
