import unittest
import base64
import os


APP_IMPORT_ERROR = None
try:
    import app
except Exception as exc:  # pragma: no cover - environment dependent import guard
    app = None
    APP_IMPORT_ERROR = exc


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class AppearancePreferenceTests(unittest.TestCase):
    def test_theme_and_language_normalization(self):
        self.assertEqual(app._normalize_ui_theme("midnight"), "midnight")
        self.assertEqual(app._normalize_ui_theme("unknown"), app.DEFAULT_UI_THEME)
        self.assertEqual(app._normalize_ui_language("hi"), "hi")
        self.assertEqual(app._normalize_ui_language("es"), app.DEFAULT_UI_LANGUAGE)

    def test_appearance_defaults_from_missing_user_fields(self):
        prefs = app._appearance_preferences_from_user({})
        self.assertEqual(prefs["theme"], app.DEFAULT_UI_THEME)
        self.assertEqual(prefs["language"], app.DEFAULT_UI_LANGUAGE)


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class AvatarPresetTests(unittest.TestCase):
    def test_avatar_preset_and_style_fallback(self):
        self.assertEqual(app._normalize_avatar_preset("forest"), "forest")
        self.assertEqual(app._normalize_avatar_preset("invalid"), app.DEFAULT_AVATAR_PRESET)
        style = app._avatar_style("invalid")
        self.assertEqual(style["start"], app.AVATAR_PRESET_MAP[app.DEFAULT_AVATAR_PRESET]["start"])

    def test_avatar_preset_from_user_doc(self):
        preset = app._avatar_preset_from_user({"avatar": {"preset": "sunset"}})
        self.assertEqual(preset, "sunset")
        fallback_preset = app._avatar_preset_from_user({"avatar": {"preset": "bad"}})
        self.assertEqual(fallback_preset, app.DEFAULT_AVATAR_PRESET)

    def test_avatar_image_path_normalization(self):
        valid_path = f"{app.PROFILE_IMAGE_UPLOAD_SUBDIR_URL}/profile.png"
        self.assertEqual(app._normalize_avatar_image_path(valid_path), valid_path)
        self.assertEqual(app._normalize_avatar_image_path(f"/{valid_path}"), valid_path)
        self.assertIsNone(app._normalize_avatar_image_path("uploads/avatars/profile.svg"))
        self.assertIsNone(app._normalize_avatar_image_path("../profile.png"))

    def test_save_avatar_image_data_url(self):
        payload = base64.b64encode(b"sample-image-bytes").decode("ascii")
        data_url = f"data:image/png;base64,{payload}"
        image_path = app._save_avatar_image_data_url(data_url, "unit-test-user")
        self.assertTrue(image_path.startswith(f"{app.PROFILE_IMAGE_UPLOAD_SUBDIR_URL}/"))
        absolute_path = os.path.join(app.app.static_folder, image_path.replace("/", os.sep))
        self.assertTrue(os.path.isfile(absolute_path))
        app._delete_avatar_image_file(image_path)


if __name__ == "__main__":
    unittest.main()
