#!/usr/bin/env python3
import base64
import json
import unittest

import send_report
from email_brand import LOGO_CID, LOGO_CONTENT_TYPE, LOGO_FILENAME


class SendReportTests(unittest.TestCase):
    def test_logo_is_attached_as_inline_cid_image(self):
        logo_bytes = b"logo-de-prueba"
        payload = send_report.build_payload(
            "<p>cid:" + LOGO_CID + "</p>",
            "Asunto",
            "Eco <orreo@example.com>",
            "destinatario@example.com",
            logo_bytes,
        )
        data = json.loads(payload.decode("utf-8"))

        self.assertEqual(data["html"], "<p>cid:" + LOGO_CID + "</p>")
        self.assertEqual(data["to"], ["destinatario@example.com"])
        self.assertEqual(len(data["attachments"]), 1)
        attachment = data["attachments"][0]
        self.assertEqual(attachment["filename"], LOGO_FILENAME)
        self.assertEqual(attachment["content_type"], LOGO_CONTENT_TYPE)
        self.assertEqual(attachment["content_id"], LOGO_CID)
        self.assertEqual(base64.b64decode(attachment["content"]), logo_bytes)

    def test_default_logo_path_points_to_tracked_asset(self):
        self.assertTrue(send_report.DEFAULT_LOGO_PATH.is_file())
        self.assertEqual(send_report.DEFAULT_LOGO_PATH.name, LOGO_FILENAME)


if __name__ == "__main__":
    unittest.main()
