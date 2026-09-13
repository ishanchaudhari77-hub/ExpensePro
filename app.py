import os
import re
import secrets
import base64
import binascii
import calendar
import math

from flask import Flask, abort, flash, g, jsonify, render_template, request, redirect, send_from_directory, session, url_for
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, date, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "expensepro-dev-secret-change-me")

# MongoDB connection (configurable for Compass/local/Atlas)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "expense_tracker")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "expenses")
MONGO_CATEGORY_COLLECTION_NAME = os.getenv("MONGO_CATEGORY_COLLECTION_NAME", "categories")
MONGO_INCOME_COLLECTION_NAME = os.getenv("MONGO_INCOME_COLLECTION_NAME", "incomes")
MONGO_BUDGET_COLLECTION_NAME = os.getenv("MONGO_BUDGET_COLLECTION_NAME", "monthly_budgets")
MONGO_USER_COLLECTION_NAME = os.getenv("MONGO_USER_COLLECTION_NAME", "users")
MONGO_NOTIFICATION_COLLECTION_NAME = os.getenv("MONGO_NOTIFICATION_COLLECTION_NAME", "notifications")
MONGO_GOAL_COLLECTION_NAME = os.getenv("MONGO_GOAL_COLLECTION_NAME", "goals")

DEFAULT_CATEGORIES = ["Food", "Education", "Travel", "Shopping", "Bills", "Health", "Other"]

RUPY_MEME_EXPRESSION_PREFERRED_ORDER = [
    "idle",
    "angry",
    "wink",
    "thumbs_up",
    "thinking",
    "confused",
    "lightbulb_idea",
    "analyzing_chart",
    "happy",
    "celebration",
    "hello",
    "shocked",
    "lazy_rich",
    "sunglasses",
    "coffee_spend",
    "broke",
    "login",
    "loading",
    "error",
    "notification",
    "money_rain",
    "proud",
    "sad",
    "warning",
]

RUPY_CHAT_DEFAULT_QUICK_REPLIES = [
    "How much did I spend today?",
    "Budget left this month?",
    "Show weekly summary",
    "How is my streak?",
]
RUPY_CHAT_SESSION_CONTEXT_KEY = "rupy_chat_context"

CATEGORY_UI_MAP = {
    "food": {"icon": "fa-solid fa-utensils", "color": "#ff9800"},
    "transportation": {"icon": "fa-solid fa-car-side", "color": "#7ac21f"},
    "transport": {"icon": "fa-solid fa-car-side", "color": "#7ac21f"},
    "travel": {"icon": "fa-solid fa-plane-departure", "color": "#7ac21f"},
    "shopping": {"icon": "fa-solid fa-bag-shopping", "color": "#f35d6c"},
    "bills": {"icon": "fa-solid fa-file-invoice", "color": "#1f6fc9"},
    "housing": {"icon": "fa-solid fa-house", "color": "#2388e2"},
    "rent": {"icon": "fa-solid fa-house", "color": "#2388e2"},
    "entertainment": {"icon": "fa-solid fa-film", "color": "#9560db"},
    "health": {"icon": "fa-solid fa-heart-pulse", "color": "#ef4444"},
    "education": {"icon": "fa-solid fa-graduation-cap", "color": "#0ea5e9"},
    "salary": {"icon": "fa-solid fa-indian-rupee-sign", "color": "#16a34a"},
    "income": {"icon": "fa-solid fa-indian-rupee-sign", "color": "#16a34a"},
    "other": {"icon": "fa-solid fa-shapes", "color": "#7a93ad"},
    "general": {"icon": "fa-solid fa-shapes", "color": "#7a93ad"},
}

DEFAULT_CATEGORY_UI = {"icon": "fa-solid fa-shapes", "color": "#7a93ad"}

NOTIFICATION_UI_MAP = {
    "alerts": {"icon": "fa-solid fa-triangle-exclamation", "color": "#f97316"},
    "insights": {"icon": "fa-solid fa-lightbulb", "color": "#6366f1"},
    "transactions": {"icon": "fa-solid fa-credit-card", "color": "#0ea5e9"},
}

DEFAULT_NOTIFICATION_UI = {"icon": "fa-solid fa-bell", "color": "#1f6fc9"}

DEFAULT_UI_THEME = "default"
ALLOWED_UI_THEMES = {"default", "midnight", "forest"}
DEFAULT_UI_LANGUAGE = "en"
ALLOWED_UI_LANGUAGES = {"en", "hi"}
DEFAULT_AVATAR_PRESET = "ocean"
AVATAR_PRESET_MAP = {
    "ocean": {
        "label": "Ocean Blue",
        "start": "#2388e2",
        "end": "#1f6fc9",
        "ring": "#c0d5ee",
    },
    "forest": {
        "label": "Forest Green",
        "start": "#22c55e",
        "end": "#15803d",
        "ring": "#bbf7d0",
    },
    "sunset": {
        "label": "Sunset Orange",
        "start": "#fb923c",
        "end": "#ea580c",
        "ring": "#fed7aa",
    },
    "violet": {
        "label": "Royal Violet",
        "start": "#8b5cf6",
        "end": "#6d28d9",
        "ring": "#ddd6fe",
    },
}
PROFILE_IMAGE_UPLOAD_SUBDIR = os.path.join("uploads", "avatars")
PROFILE_IMAGE_UPLOAD_DIR = os.path.join(app.static_folder, PROFILE_IMAGE_UPLOAD_SUBDIR)
PROFILE_IMAGE_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "jfif", "webp", "gif", "avif"}
PROFILE_IMAGE_MAX_SIZE_BYTES = 20 * 1024 * 1024
PROFILE_IMAGE_MAX_SIZE_MB = int(PROFILE_IMAGE_MAX_SIZE_BYTES / (1024 * 1024))
PROFILE_IMAGE_UPLOAD_SUBDIR_URL = PROFILE_IMAGE_UPLOAD_SUBDIR.replace("\\", "/")
FAVICON_FILENAME = "favicon.ico"
FAVICON_SVG_FILENAME = "favicon.svg"
FAVICON_VERSION_FILES = (FAVICON_FILENAME, FAVICON_SVG_FILENAME)

GAMIFICATION_XP_ACTIONS = {
    "add_expense": 10,
    "set_budget": 20,
    "stay_under_budget": 50,
    "savings_goal_reached": 200,
    "streak_milestone": 100,
    "daily_challenge": 40,
}

GOAL_TYPE_SAVINGS = "savings"
GOAL_TYPE_SPENDING_CAP = "spending_cap"
GOAL_STATUS_ACTIVE = "active"
GOAL_STATUS_COMPLETED = "completed"
GOAL_STATUS_ARCHIVED = "archived"
GOAL_RECURRENCE_MONTHLY = "monthly"

GOAL_TYPE_META = {
    GOAL_TYPE_SAVINGS: {
        "label": "Savings Goal",
        "icon": "fa-solid fa-piggy-bank",
    },
    GOAL_TYPE_SPENDING_CAP: {
        "label": "Spending Cap",
        "icon": "fa-solid fa-shield-halved",
    },
}

GOAL_TEMPLATES = [
    {
        "key": "emergency_fund",
        "title": "Build Emergency Fund",
        "goal_type": GOAL_TYPE_SAVINGS,
        "target_amount": 25000,
        "category": "",
        "recurrence": "",
        "due_days": 120,
    },
    {
        "key": "monthly_savings_sprint",
        "title": "Monthly Savings Sprint",
        "goal_type": GOAL_TYPE_SAVINGS,
        "target_amount": 8000,
        "category": "",
        "recurrence": "",
        "due_days": 45,
    },
    {
        "key": "food_spending_cap",
        "title": "Keep Food Spend Under Control",
        "goal_type": GOAL_TYPE_SPENDING_CAP,
        "target_amount": 6000,
        "category": "Food",
        "recurrence": GOAL_RECURRENCE_MONTHLY,
        "due_days": 25,
    },
    {
        "key": "shopping_spending_cap",
        "title": "Reduce Shopping Burn",
        "goal_type": GOAL_TYPE_SPENDING_CAP,
        "target_amount": 3000,
        "category": "Shopping",
        "recurrence": GOAL_RECURRENCE_MONTHLY,
        "due_days": 25,
    },
]

GAMIFICATION_ACHIEVEMENTS = [
    {
        "key": "first_expense",
        "title": "First Expense",
        "description": "Add your first expense entry.",
    },
    {
        "key": "streak_7",
        "title": "7 Day Streak",
        "description": "Track expenses for 7 consecutive days.",
    },
    {
        "key": "budget_hero",
        "title": "Budget Hero",
        "description": "Stay under budget this month.",
    },
    {
        "key": "saving_machine",
        "title": "Saving Machine",
        "description": "Keep monthly savings at ₹5,000 or more.",
    },
    {
        "key": "expense_detective",
        "title": "Expense Detective",
        "description": "Categorize at least 50 expenses.",
    },
    {
        "key": "no_spend_day",
        "title": "No Spend Day",
        "description": "Complete one full day without spending.",
    },
    {
        "key": "smart_planner",
        "title": "Smart Planner",
        "description": "Set a monthly budget plan.",
    },
    {
        "key": "investor_mode",
        "title": "Investor Mode",
        "description": "Add an investment category.",
    },
    {
        "key": "emergency_saver",
        "title": "Emergency Saver",
        "description": "Create an emergency fund category.",
    },
]

I18N_TEXT = {
    "en": {
        "sidebar.account": "My Account",
        "sidebar.dashboard": "Dashboard",
        "sidebar.expenses": "Expenses",
        "sidebar.reports": "Reports",
        "sidebar.goals": "Goals",
        "sidebar.gamification": "Gamification",
        "sidebar.settings": "Settings",
        "sidebar.logout": "Logout",
        "splash.tagline": "Track Smart. Spend Better.",
        "modal.confirm_logout_title": "Confirm Logout",
        "modal.confirm_logout_body": "Do you want to logout from ExpensePro?",
        "modal.confirm_action_title": "Confirm Action",
        "modal.confirm_action_body": "Are you sure you want to continue?",
        "common.cancel": "Cancel",
        "common.logout": "Logout",
        "common.yes_continue": "Yes, continue",
        "login.title": "Login | ExpensePro",
        "login.heading": "Login",
        "login.subtitle": "Access your ExpensePro dashboard",
        "login.email_placeholder": "Email address",
        "login.password_placeholder": "Password",
        "login.button": "Login",
        "login.new_user": "New user?",
        "login.create_account": "Create an account",
        "register.title": "Register | ExpensePro",
        "register.heading": "Create Account",
        "register.subtitle": "Start tracking your expenses securely",
        "register.name_placeholder": "Full name",
        "register.email_placeholder": "Email address",
        "register.password_placeholder": "Password (minimum 6 chars)",
        "register.confirm_password_placeholder": "Confirm password",
        "register.button": "Register",
        "register.have_account": "Already have an account?",
        "register.login": "Login",
        "dashboard.heading": "Dashboard",
        "dashboard.overview": "Overview",
        "profile.group_account": "Account",
        "profile.my_account": "My Account",
        "profile.manage_expenses": "Manage Expenses",
        "profile.view_reports": "View Reports",
        "profile.app_settings": "App Settings",
        "profile.quick_preferences": "Quick Preferences",
        "profile.theme": "Theme",
        "profile.language": "Language",
        "theme.default": "Default",
        "theme.midnight": "Midnight",
        "theme.forest": "Forest",
        "language.english": "English",
        "language.hindi": "Hindi",
        "scope.this_month": "This Month",
        "scope.all_time": "All Time",
        "account.heading": "My Account",
        "account.subtitle": "Manage profile details, security settings, and avatar style",
        "account.profile_details": "Profile Details",
        "account.full_name": "Full Name",
        "account.email_address": "Email Address",
        "account.upload_profile_image": "Upload Profile Photo",
        "account.change_profile_image": "Change Profile Photo",
        "account.no_file_selected": "No file selected",
        "account.profile_image_save_hint": "Apply Crop to save photo instantly.",
        "account.profile_image": "Profile Image",
        "account.profile_image_hint": "PNG, JPG, JPEG, JFIF, WEBP, GIF, or AVIF up to {max_mb} MB.",
        "account.remove_profile_image": "Remove current image",
        "account.avatar_style": "Avatar Style",
        "account.save_profile": "Save Profile",
        "account.security": "Security",
        "account.current_password": "Current Password",
        "account.current_password_placeholder": "Enter current password",
        "account.new_password": "New Password",
        "account.new_password_placeholder": "At least 6 characters",
        "account.confirm_new_password": "Confirm New Password",
        "account.confirm_new_password_placeholder": "Re-enter new password",
        "account.update_password": "Update Password",
        "account.joined": "Joined {date}",
        "account.theme_badge": "Theme: {value}",
        "account.language_badge": "Language: {value}",
    },
    "hi": {
        "sidebar.account": "मेरा अकाउंट",
        "sidebar.dashboard": "डैशबोर्ड",
        "sidebar.expenses": "खर्च",
        "sidebar.reports": "रिपोर्ट्स",
        "sidebar.gamification": "गेमिफिकेशन",
        "sidebar.settings": "सेटिंग्स",
        "sidebar.logout": "लॉगआउट",
        "splash.tagline": "स्मार्ट ट्रैक करें। बेहतर खर्च करें।",
        "modal.confirm_logout_title": "लॉगआउट पुष्टि",
        "modal.confirm_logout_body": "क्या आप ExpensePro से लॉगआउट करना चाहते हैं?",
        "modal.confirm_action_title": "क्रिया की पुष्टि",
        "modal.confirm_action_body": "क्या आप जारी रखना चाहते हैं?",
        "common.cancel": "रद्द करें",
        "common.logout": "लॉगआउट",
        "common.yes_continue": "हाँ, जारी रखें",
        "login.title": "लॉगिन | ExpensePro",
        "login.heading": "लॉगिन",
        "login.subtitle": "अपना ExpensePro डैशबोर्ड खोलें",
        "login.email_placeholder": "ईमेल पता",
        "login.password_placeholder": "पासवर्ड",
        "login.button": "लॉगिन",
        "login.new_user": "नए यूज़र?",
        "login.create_account": "अकाउंट बनाएं",
        "register.title": "रजिस्टर | ExpensePro",
        "register.heading": "अकाउंट बनाएं",
        "register.subtitle": "अपने खर्च सुरक्षित तरीके से ट्रैक करना शुरू करें",
        "register.name_placeholder": "पूरा नाम",
        "register.email_placeholder": "ईमेल पता",
        "register.password_placeholder": "पासवर्ड (कम से कम 6 अक्षर)",
        "register.confirm_password_placeholder": "पासवर्ड पुष्टि करें",
        "register.button": "रजिस्टर",
        "register.have_account": "पहले से अकाउंट है?",
        "register.login": "लॉगिन",
        "dashboard.heading": "डैशबोर्ड",
        "dashboard.overview": "अवलोकन",
        "profile.group_account": "अकाउंट",
        "profile.my_account": "मेरा अकाउंट",
        "profile.manage_expenses": "खर्च प्रबंधित करें",
        "profile.view_reports": "रिपोर्ट देखें",
        "profile.app_settings": "ऐप सेटिंग्स",
        "profile.quick_preferences": "क्विक प्रेफरेंसेस",
        "profile.theme": "थीम",
        "profile.language": "भाषा",
        "theme.default": "डिफ़ॉल्ट",
        "theme.midnight": "मिडनाइट",
        "theme.forest": "फॉरेस्ट",
        "language.english": "अंग्रेज़ी",
        "language.hindi": "हिंदी",
        "scope.this_month": "इस माह",
        "scope.all_time": "सभी समय",
        "account.heading": "मेरा अकाउंट",
        "account.subtitle": "प्रोफाइल, सुरक्षा और अवतार शैली प्रबंधित करें",
        "account.profile_details": "प्रोफाइल विवरण",
        "account.full_name": "पूरा नाम",
        "account.email_address": "ईमेल पता",
        "account.avatar_style": "अवतार शैली",
        "account.save_profile": "प्रोफाइल सेव करें",
        "account.security": "सुरक्षा",
        "account.current_password": "वर्तमान पासवर्ड",
        "account.current_password_placeholder": "वर्तमान पासवर्ड दर्ज करें",
        "account.new_password": "नया पासवर्ड",
        "account.new_password_placeholder": "कम से कम 6 अक्षर",
        "account.confirm_new_password": "नए पासवर्ड की पुष्टि",
        "account.confirm_new_password_placeholder": "नया पासवर्ड फिर से दर्ज करें",
        "account.update_password": "पासवर्ड अपडेट करें",
        "account.joined": "शामिल हुए: {date}",
        "account.theme_badge": "थीम: {value}",
        "account.language_badge": "भाषा: {value}",
    },
}

# VIVA: DB - connect Flask to MongoDB using the configured URI and open the main collections.
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    categories_collection = db[MONGO_CATEGORY_COLLECTION_NAME]
    incomes_collection = db[MONGO_INCOME_COLLECTION_NAME]
    budgets_collection = db[MONGO_BUDGET_COLLECTION_NAME]
    users_collection = db[MONGO_USER_COLLECTION_NAME]
    notifications_collection = db[MONGO_NOTIFICATION_COLLECTION_NAME]
    goals_collection = db[MONGO_GOAL_COLLECTION_NAME]
    # VIVA: DB/PERFORMANCE - create indexes for user/date/search fields so dashboard and APIs stay fast.
    def _safe_create_index(target_collection, keys, **kwargs):
        try:
            target_collection.create_index(keys, **kwargs)
        except OperationFailure as index_exc:
            if int(getattr(index_exc, "code", 0) or 0) in {85, 86}:
                return
            raise

    _safe_create_index(collection, [("user_id", 1), ("date", -1)], name="expense_user_date_idx")
    _safe_create_index(
        collection,
        [("user_id", 1), ("category_search", 1), ("date", -1)],
        name="expense_user_category_date_idx",
    )
    _safe_create_index(
        collection,
        [("user_id", 1), ("merchant_search", 1), ("date", -1)],
        name="expense_user_merchant_date_idx",
    )
    _safe_create_index(
        collection,
        [("user_id", 1), ("amount_value", 1), ("date", -1)],
        name="expense_user_amount_date_idx",
    )
    _safe_create_index(budgets_collection, [("user_id", 1), ("month", 1)], name="budget_user_month_idx")
    _safe_create_index(
        notifications_collection,
        [("user_id", 1), ("notification_id", 1)],
        unique=True,
        name="user_id_1_notification_id_1",
    )
    _safe_create_index(
        goals_collection,
        [("user_id", 1), ("status", 1), ("due_date", 1)],
        name="goal_user_status_due_idx",
    )
    _safe_create_index(
        goals_collection,
        [("user_id", 1), ("goal_type", 1), ("tracking_month", 1)],
        name="goal_user_type_month_idx",
    )
except PyMongoError as exc:
    raise RuntimeError(
        "MongoDB connection failed. Set MONGO_URI to your MongoDB Compass/Atlas URI."
    ) from exc

# -------------------- ROUTES --------------------


PUBLIC_ENDPOINTS = {"login", "register", "favicon", "static"}


# VIVA: SECURITY - allow only same-site redirect targets after login.
def _is_safe_next_url(target):
    if not target:
        return False
    return target.startswith("/") and not target.startswith("//")


def _favicon_version():
    latest_mtime = 0
    for filename in FAVICON_VERSION_FILES:
        favicon_path = os.path.join(app.static_folder, filename)
        try:
            latest_mtime = max(latest_mtime, int(os.path.getmtime(favicon_path)))
        except OSError:
            continue
    return latest_mtime or 1


def _normalize_email(value):
    return str(value or "").strip().lower()


def _coerce_bool(value, field_name="value"):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    abort(400, description=f"Invalid {field_name}")


def _normalize_category_key(value):
    return str(value or "").strip().lower()


def _category_ui(value):
    key = _normalize_category_key(value)
    return CATEGORY_UI_MAP.get(key, DEFAULT_CATEGORY_UI)


def _notification_ui(value):
    key = str(value or "").strip().lower()
    return NOTIFICATION_UI_MAP.get(key, DEFAULT_NOTIFICATION_UI)


def _normalize_ui_theme(value):
    clean_value = str(value or "").strip().lower()
    if clean_value not in ALLOWED_UI_THEMES:
        return DEFAULT_UI_THEME
    return clean_value


def _normalize_ui_language(value):
    clean_value = str(value or "").strip().lower()
    if clean_value not in ALLOWED_UI_LANGUAGES:
        return DEFAULT_UI_LANGUAGE
    return clean_value


def _normalize_avatar_preset(value):
    clean_value = str(value or "").strip().lower()
    if clean_value not in AVATAR_PRESET_MAP:
        return DEFAULT_AVATAR_PRESET
    return clean_value


def _appearance_preferences_from_user(user_doc):
    ui_preferences = (user_doc or {}).get("ui_preferences", {})
    return {
        "theme": _normalize_ui_theme(ui_preferences.get("theme")),
        "language": _normalize_ui_language(ui_preferences.get("language")),
    }


def _avatar_preset_from_user(user_doc):
    avatar_doc = (user_doc or {}).get("avatar", {})
    return _normalize_avatar_preset(avatar_doc.get("preset"))


def _avatar_style(value):
    preset_key = _normalize_avatar_preset(value)
    return AVATAR_PRESET_MAP.get(preset_key, AVATAR_PRESET_MAP[DEFAULT_AVATAR_PRESET])


def _avatar_preset_options():
    return [
        {
            "key": key,
            "label": style.get("label", key.title()),
            "start": style.get("start", "#2388e2"),
            "end": style.get("end", "#1f6fc9"),
            "ring": style.get("ring", "#c0d5ee"),
        }
        for key, style in AVATAR_PRESET_MAP.items()
    ]


def _profile_image_max_size_label():
    return f"{PROFILE_IMAGE_MAX_SIZE_MB} MB"


def _is_allowed_profile_image_extension(filename):
    clean_name = str(filename or "").strip().lower()
    if "." not in clean_name:
        return False
    extension = clean_name.rsplit(".", 1)[-1]
    return extension in PROFILE_IMAGE_ALLOWED_EXTENSIONS


# VIVA: SECURITY - normalize avatar paths and block traversal outside the upload folder.
def _normalize_avatar_image_path(value):
    raw_value = str(value or "").strip().replace("\\", "/")
    if not raw_value:
        return None

    clean_path = raw_value.lstrip("/")
    if ".." in clean_path.split("/"):
        return None

    required_prefix = f"{PROFILE_IMAGE_UPLOAD_SUBDIR_URL}/"
    if not clean_path.startswith(required_prefix):
        return None
    if not _is_allowed_profile_image_extension(clean_path):
        return None
    return clean_path


def _avatar_image_abs_path(value):
    image_path = _normalize_avatar_image_path(value)
    if not image_path:
        return None

    absolute_path = os.path.abspath(
        os.path.join(app.static_folder, image_path.replace("/", os.sep))
    )
    upload_root = os.path.normcase(os.path.abspath(PROFILE_IMAGE_UPLOAD_DIR))
    candidate_path = os.path.normcase(absolute_path)
    try:
        is_within_upload_root = os.path.commonpath([upload_root, candidate_path]) == upload_root
    except ValueError:
        return None
    if not is_within_upload_root:
        return None
    return absolute_path


def _avatar_image_path_from_user(user_doc):
    avatar_doc = (user_doc or {}).get("avatar", {})
    image_path = _normalize_avatar_image_path(avatar_doc.get("image_path"))
    if not image_path:
        return None

    absolute_path = _avatar_image_abs_path(image_path)
    if not absolute_path or not os.path.isfile(absolute_path):
        return None
    return image_path


def _delete_avatar_image_file(image_path):
    absolute_path = _avatar_image_abs_path(image_path)
    if not absolute_path or not os.path.isfile(absolute_path):
        return
    try:
        os.remove(absolute_path)
    except OSError:
        return


def _avatar_storage_targets(user_id, extension):
    safe_user_id = re.sub(r"[^a-zA-Z0-9]", "", str(user_id))
    unique_token = secrets.token_hex(8)
    timestamp = int(datetime.utcnow().timestamp())
    stored_filename = f"{safe_user_id}_{timestamp}_{unique_token}.{extension.lower()}"
    stored_relative_path = f"{PROFILE_IMAGE_UPLOAD_SUBDIR_URL}/{stored_filename}"
    output_path = os.path.join(PROFILE_IMAGE_UPLOAD_DIR, stored_filename)
    return stored_relative_path, output_path


def _save_avatar_image_bytes(image_bytes, user_id, extension):
    normalized_extension = str(extension or "").strip().lower()
    if normalized_extension == "jpg":
        normalized_extension = "jpeg"
    if normalized_extension not in PROFILE_IMAGE_ALLOWED_EXTENSIONS:
        raise ValueError("Image format is not supported.")

    if not isinstance(image_bytes, (bytes, bytearray)):
        raise ValueError("Image data is invalid.")
    if len(image_bytes) > PROFILE_IMAGE_MAX_SIZE_BYTES:
        raise ValueError(f"Profile image must be {_profile_image_max_size_label()} or smaller.")

    stored_relative_path, output_path = _avatar_storage_targets(user_id, normalized_extension)
    os.makedirs(PROFILE_IMAGE_UPLOAD_DIR, exist_ok=True)
    with open(output_path, "wb") as image_file:
        image_file.write(image_bytes)

    try:
        if os.path.getsize(output_path) > PROFILE_IMAGE_MAX_SIZE_BYTES:
            os.remove(output_path)
            raise ValueError(f"Profile image must be {_profile_image_max_size_label()} or smaller.")
    except OSError:
        pass
    return stored_relative_path


# VIVA: SECURITY - validate cropped avatar input and reject malformed base64 image data.
def _save_avatar_image_data_url(data_url, user_id):
    raw_data_url = str(data_url or "").strip()
    match = re.match(
        r"^data:image/(png|jpeg|jpg|jfif|webp|gif|avif);base64,([A-Za-z0-9+/=]+)$",
        raw_data_url,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("Cropped image data is invalid.")

    extension = match.group(1).lower()
    encoded_data = match.group(2)
    try:
        image_bytes = base64.b64decode(encoded_data, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Cropped image data is invalid.") from None
    if not image_bytes:
        raise ValueError("Cropped image data is empty.")

    return _save_avatar_image_bytes(image_bytes, user_id, extension)


# VIVA: SECURITY - uploaded profile images must use allowed extensions and stay under the size limit.
def _save_avatar_image_file(file_storage, user_id):
    if not file_storage:
        return None

    original_filename = secure_filename(file_storage.filename or "")
    if not original_filename:
        raise ValueError("Please choose a valid profile image file.")
    if not _is_allowed_profile_image_extension(original_filename):
        raise ValueError("Profile image must be PNG, JPG, JPEG, JFIF, WEBP, GIF, or AVIF.")

    upload_size = file_storage.content_length
    if upload_size is None or upload_size <= 0:
        upload_stream = getattr(file_storage, "stream", None)
        if upload_stream:
            try:
                current_position = upload_stream.tell()
                upload_stream.seek(0, os.SEEK_END)
                upload_size = upload_stream.tell()
                upload_stream.seek(current_position)
            except Exception:
                upload_size = None
    if upload_size and upload_size > PROFILE_IMAGE_MAX_SIZE_BYTES:
        raise ValueError(f"Profile image must be {_profile_image_max_size_label()} or smaller.")

    extension = original_filename.rsplit(".", 1)[-1].lower()
    stored_relative_path, output_path = _avatar_storage_targets(user_id, extension)

    os.makedirs(PROFILE_IMAGE_UPLOAD_DIR, exist_ok=True)
    file_storage.save(output_path)
    try:
        if os.path.getsize(output_path) > PROFILE_IMAGE_MAX_SIZE_BYTES:
            os.remove(output_path)
            raise ValueError(f"Profile image must be {_profile_image_max_size_label()} or smaller.")
    except OSError:
        pass
    return stored_relative_path


def _translate_text(key, language=None, **kwargs):
    selected_language = _normalize_ui_language(language or DEFAULT_UI_LANGUAGE)
    selected_map = I18N_TEXT.get(selected_language, I18N_TEXT["en"])
    fallback_map = I18N_TEXT["en"]
    message_template = selected_map.get(key) or fallback_map.get(key) or str(key)
    if not kwargs:
        return message_template
    try:
        return str(message_template).format(**kwargs)
    except Exception:
        return str(message_template)


# VIVA: AUTH - load the logged-in user from session and clear stale or invalid sessions.
def _load_current_user_from_session():
    user_id_value = session.get("user_id")
    if not user_id_value:
        return None

    try:
        user_id = ObjectId(user_id_value)
    except (InvalidId, TypeError):
        session.clear()
        return None

    user = users_collection.find_one(
        {"_id": user_id},
        {
            "name": 1,
            "email": 1,
            "created_at": 1,
            "ui_preferences.theme": 1,
            "ui_preferences.language": 1,
            "avatar.preset": 1,
            "avatar.image_path": 1,
        },
    )
    if not user:
        session.clear()
        return None
    return user


def _goal_sidebar_counts(current_user):
    if not current_user or not current_user.get("_id"):
        return {"active": 0, "due_soon": 0}

    user_id = current_user.get("_id")
    today_key = date.today().strftime("%Y-%m-%d")
    soon_key = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    current_month = date.today().strftime("%Y-%m")

    try:
        _apply_recurring_goal_resets(user_id, current_month)
        active_count = goals_collection.count_documents(
            {"user_id": user_id, "status": GOAL_STATUS_ACTIVE}
        )
        due_soon_count = goals_collection.count_documents(
            {
                "user_id": user_id,
                "status": GOAL_STATUS_ACTIVE,
                "due_date": {"$gte": today_key, "$lte": soon_key},
            }
        )
    except PyMongoError:
        active_count = 0
        due_soon_count = 0

    return {
        "active": max(0, _safe_int(active_count, 0)),
        "due_soon": max(0, _safe_int(due_soon_count, 0)),
    }


def _normalize_goal_ui_event(raw_event):
    if not isinstance(raw_event, dict):
        return None

    event_type = str(raw_event.get("type", "")).strip().lower()
    message = str(raw_event.get("message", "")).strip()
    toast_type = str(raw_event.get("toast_type", "")).strip().lower()

    allowed_event_types = {
        "goal_created",
        "goal_completed",
        "goal_deadline_warning",
        "goal_archived",
        "goal_deleted",
        "goal_reactivated",
        "goal_recurring_reset",
    }
    allowed_toast_types = {"success", "warning", "error", "info"}

    if event_type not in allowed_event_types:
        return None
    if not message:
        return None

    return {
        "type": event_type,
        "message": message[:220],
        "toast_type": toast_type if toast_type in allowed_toast_types else "info",
    }


def _build_rupy_meme_expressions():
    mascot_dir = os.path.join(app.static_folder or "", "mascot", "rupy")
    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    expression_map = {}

    try:
        for file_name in os.listdir(mascot_dir):
            full_path = os.path.join(mascot_dir, file_name)
            if not os.path.isfile(full_path):
                continue

            stem, extension = os.path.splitext(file_name)
            extension_lower = extension.lower()
            stem_lower = stem.lower()
            if extension_lower not in allowed_extensions:
                continue
            if not stem_lower.startswith("rupy_"):
                continue

            key = stem_lower.replace("rupy_", "", 1)
            if not key:
                continue

            label = key.replace("_", " ").title()
            expression_map[key] = {
                "key": key,
                "label": label,
                "file_name": file_name,
                "src": url_for("static", filename=f"mascot/rupy/{file_name}"),
            }
    except OSError:
        expression_map = {}

    ordered_keys = []
    for key in RUPY_MEME_EXPRESSION_PREFERRED_ORDER:
        if key in expression_map:
            ordered_keys.append(key)

    for key in sorted(expression_map.keys()):
        if key not in ordered_keys:
            ordered_keys.append(key)

    return [expression_map[key] for key in ordered_keys]


def _build_weekly_spending_summary(expenses, *, today_value=None):
    today = today_value or date.today()
    window_start = today - timedelta(days=6)
    category_totals = {}
    weekly_total = 0.0
    transactions = 0
    weekend_total = 0.0

    for expense in expenses:
        expense_date = _parse_record_date(expense.get("date"))
        if not expense_date or expense_date < window_start or expense_date > today:
            continue

        amount_value = _safe_amount(expense.get("amount"))
        if amount_value <= 0:
            continue

        transactions += 1
        weekly_total += amount_value
        category_name = str(expense.get("category", "")).strip() or "Other"
        category_totals[category_name] = _safe_amount(category_totals.get(category_name)) + amount_value

        if expense_date.weekday() >= 5:
            weekend_total += amount_value

    sorted_categories = sorted(
        category_totals.items(),
        key=lambda item: _safe_amount(item[1]),
        reverse=True,
    )

    top_categories = []
    for category_name, amount_value in sorted_categories[:3]:
        share_percent = (amount_value / weekly_total * 100.0) if weekly_total > 0 else 0.0
        top_categories.append(
            {
                "category": category_name,
                "amount": _safe_amount(amount_value),
                "share_percent": share_percent,
            }
        )

    return {
        "start": window_start.strftime("%Y-%m-%d"),
        "end": today.strftime("%Y-%m-%d"),
        "window_label": f"{window_start.strftime('%d %b')} to {today.strftime('%d %b')}",
        "total": _safe_amount(weekly_total),
        "transactions": max(0, _safe_int(transactions, 0)),
        "weekend_total": _safe_amount(weekend_total),
        "top_categories": top_categories,
        "is_weekend_today": today.weekday() >= 5,
    }


def _build_rupy_coach_payload(
    *,
    expenses,
    current_month,
    current_month_label,
    monthly_budget,
    monthly_expense,
    monthly_remaining,
    monthly_spent_percent,
    monthly_forecast,
    goals_overview,
    gamification,
    weekly_summary,
):
    today_value = date.today()
    monthly_budget_value = _safe_amount(monthly_budget)
    monthly_expense_value = _safe_amount(monthly_expense)
    monthly_remaining_value = _safe_amount(monthly_remaining)
    spent_percent_value = _safe_amount(monthly_spent_percent)
    forecast_over_value = _safe_amount((monthly_forecast or {}).get("forecast_over_by"))
    forecast_total_value = _safe_amount((monthly_forecast or {}).get("projected_total"))
    forecast_confidence = str((monthly_forecast or {}).get("confidence", "low")).strip().lower()

    goal_due_soon_count = _safe_int((goals_overview or {}).get("due_soon_count"), 0)
    goal_overdue_count = _safe_int((goals_overview or {}).get("overdue_count"), 0)
    goal_warning_count = max(0, goal_due_soon_count + goal_overdue_count)
    goal_completed_today = _safe_int((goals_overview or {}).get("completed_today_count"), 0)
    goal_focus = (goals_overview or {}).get("next_focus_goal") or {}
    goal_focus_title = str(goal_focus.get("title", "")).strip()
    goal_eta = str(goal_focus.get("eta_copy", "")).strip()

    daily_challenge = (gamification or {}).get("daily_challenge") or {}
    daily_challenge_key = str(daily_challenge.get("key", "")).strip().lower()
    no_spend_day = daily_challenge_key == "no_spend" and bool(daily_challenge.get("is_complete"))

    streak_days = max(0, _safe_int((gamification or {}).get("streak_days"), 0))
    level_up = bool((gamification or {}).get("level_up"))
    level_value = max(1, _safe_int((gamification or {}).get("level"), 1))
    previous_level_value = max(1, _safe_int((gamification or {}).get("previous_level"), level_value))
    unlocked_achievement_count = max(0, _safe_int((gamification or {}).get("new_achievements_count"), 0))
    unlocked_achievement_count = max(
        unlocked_achievement_count,
        len((gamification or {}).get("new_achievements") or []),
    )
    gamification_events = {
        str(item or "").strip().lower()
        for item in ((gamification or {}).get("events") or [])
        if str(item or "").strip()
    }
    money_apprentice_unlocked = level_up and previous_level_value < 4 <= level_value
    streak_reward_unlocked = "streak_reward" in gamification_events

    latest_expense_date = None
    for expense in expenses:
        parsed_date = _parse_record_date(expense.get("date"))
        if not parsed_date:
            continue
        if latest_expense_date is None or parsed_date > latest_expense_date:
            latest_expense_date = parsed_date
    inactive_24h = latest_expense_date is None or latest_expense_date < today_value

    weekly_total = _safe_amount((weekly_summary or {}).get("total"))
    weekly_transactions = _safe_int((weekly_summary or {}).get("transactions"), 0)
    weekend_total = _safe_amount((weekly_summary or {}).get("weekend_total"))
    weekly_top_categories = (weekly_summary or {}).get("top_categories") or []
    top_weekly_category = weekly_top_categories[0] if weekly_top_categories else {}
    top_weekly_share = _safe_amount(top_weekly_category.get("share_percent"))
    weekend_spike = (
        bool((weekly_summary or {}).get("is_weekend_today"))
        and weekly_total > 0
        and weekend_total >= (weekly_total * 0.45)
    )

    if weekly_total <= 0:
        weekly_reaction = "No weekly activity detected. Add one expense entry today."
    elif monthly_budget_value > 0 and weekly_total > (monthly_budget_value * 0.4):
        focus_category = str(top_weekly_category.get("category", "Food")).strip() or "Food"
        weekly_reaction = f"{focus_category} spending is high this week. Tighten that cap first."
    elif weekend_spike:
        weekly_reaction = "Weekend spending is running fast. Keep one discretionary cap active."
    else:
        weekly_reaction = "Weekly spend pattern is balanced. Keep this pace for the month."

    primary_state = "idle"
    primary_message = f"Welcome back. {current_month_label} tracking is active."

    if money_apprentice_unlocked:
        primary_state = "celebration"
        primary_message = "Money Apprentice unlocked. Mini celebration mode on."
    elif no_spend_day and weekly_transactions > 0:
        primary_state = "money-rain"
        primary_message = "No Spend Day unlocked. Coins rain for discipline."
    elif goal_completed_today > 0:
        primary_state = "celebration"
        if goal_focus_title:
            primary_message = f"Goal complete: {goal_focus_title}. Great momentum."
        else:
            primary_message = f"Great work. {goal_completed_today} goal completed today."
    elif goal_overdue_count > 0:
        primary_state = "warning"
        primary_message = f"{goal_overdue_count} goal deadline missed. Open Goals and recover the plan."
    elif goal_warning_count > 0:
        primary_state = "warning"
        primary_message = f"{goal_warning_count} goal near deadline. Prioritize goals due this week."
    elif monthly_budget_value > 0 and (monthly_remaining_value < 0 or spent_percent_value >= 100):
        primary_state = "warning"
        primary_message = f"Budget crossed for {current_month_label}. Reduce discretionary spend now."
    elif monthly_budget_value > 0 and (spent_percent_value >= 85 or forecast_over_value > 0):
        primary_state = "warning"
        primary_message = (
            f"Budget risk detected: {spent_percent_value:.0f}% used. "
            f"Projected overspend {_format_inr_message(forecast_over_value)}."
            if forecast_over_value > 0
            else f"Budget usage reached {spent_percent_value:.0f}%. Keep spending tight."
        )
    elif inactive_24h:
        primary_state = "thinking"
        primary_message = "No expense has been logged today yet. Track today before your streak breaks."
    elif monthly_budget_value > 0 and spent_percent_value <= 60:
        primary_state = "happy"
        primary_message = f"Nice pace. Only {spent_percent_value:.0f}% budget used for {current_month_label}."
    elif monthly_expense_value > 0:
        primary_state = "happy"
        primary_message = "Tracking is active and your dashboard is synced."

    assistant_state_map = {
        "celebration": "celebrate",
        "money-rain": "celebrate",
        "warning": "warning",
        "error": "error",
        "thinking": "thinking",
        "happy": "success",
        "proud": "success",
        "idle": "idle",
    }
    assistant_state = assistant_state_map.get(primary_state, "idle")

    tip_lines = [
        "Set a budget now so you avoid overspending later.",
        "Track money once. Chill all month.",
        "Financial progress comes from discipline, not random spending.",
    ]

    if monthly_budget_value <= 0:
        tip_lines.append("Monthly budget is missing. Set your budget in Settings to enable alerts.")
    else:
        tip_lines.append(
            f"{current_month_label} budget: {_format_inr_message(monthly_budget_value)} | "
            f"spent: {_format_inr_message(monthly_expense_value)}."
        )

    if monthly_remaining_value < 0:
        tip_lines.append(
            f"Overspend detected: {_format_inr_message(abs(monthly_remaining_value))}. "
            "Cut high-spend category this week."
        )
    elif monthly_remaining_value > 0 and monthly_budget_value > 0:
        tip_lines.append(
            f"Remaining buffer: {_format_inr_message(monthly_remaining_value)}. "
            "Preserve this cushion till month-end."
        )

    if goal_focus_title:
        eta_copy = f" {goal_eta}" if goal_eta else ""
        tip_lines.append(f"Goal focus: {goal_focus_title}.{eta_copy}".strip())

    if weekly_top_categories:
        focus_category = str(top_weekly_category.get("category", "Category")).strip() or "Category"
        tip_lines.append(
            f"Weekly hotspot: {focus_category} at {top_weekly_share:.0f}% share. "
            "Use category cap to control this first."
        )
    else:
        tip_lines.append("No weekly transactions yet. Start with one expense log today.")

    if streak_days > 0:
        tip_lines.append(f"Streak status: {streak_days} day streak active. Do not break it today.")

    if forecast_total_value > 0:
        tip_lines.append(
            f"Forecast ({forecast_confidence} confidence): projected month-end "
            f"{_format_inr_message(forecast_total_value)}."
        )

    if weekend_spike:
        tip_lines.append("Weekend spend spike detected. Run a weekend-only spending cap.")

    trigger_messages = {
        "goal_warning": (
            f"{goal_warning_count} goals near deadline. {goal_eta or 'Review your goals plan now.'}"
            if goal_warning_count > 0
            else ""
        ),
        "goal_complete": (
            f"Goal complete: {goal_focus_title}. Celebration unlocked."
            if goal_focus_title
            else (
                f"{goal_completed_today} goal{'s' if goal_completed_today != 1 else ''} completed today."
                if goal_completed_today > 0
                else ""
            )
        ),
        "no_spend_day": "No Spend Day complete. Rupy is throwing coins for discipline.",
        "inactive_24h": "No expense logged in 24h. Quick reminder: track today's spend.",
        "weekend_tip": "Weekend spending looks high. Keep one cap for shopping and food.",
        "streak_reward": f"{streak_days} day streak unlocked. Keep the chain alive.",
        "money_apprentice": "Money Apprentice unlocked. Mini celebration mode on.",
        "level_up": f"Level {level_value} unlocked. Money skills upgraded.",
        "achievement_unlock": (
            f"{unlocked_achievement_count} new achievement unlocked."
            if unlocked_achievement_count > 0
            else ""
        ),
    }

    return {
        "month": current_month,
        "month_label": current_month_label,
        "primary_state": primary_state,
        "assistant_state": assistant_state,
        "primary_message": primary_message,
        "tip_lines": tip_lines[:12],
        "weekly_summary": {
            **(weekly_summary or {}),
            "reaction": weekly_reaction,
        },
        "triggers": {
            "goal_warning": goal_warning_count > 0,
            "goal_complete": goal_completed_today > 0,
            "no_spend_day": no_spend_day,
            "inactive_24h": inactive_24h,
            "weekend_tip": weekend_spike,
            "streak_reward": streak_reward_unlocked,
            "money_apprentice": money_apprentice_unlocked,
            "level_up": level_up,
            "achievement_unlock": unlocked_achievement_count > 0,
        },
        "trigger_messages": trigger_messages,
    }


def _top_category_payload(category_totals):
    if not isinstance(category_totals, dict) or not category_totals:
        return {
            "category": "",
            "amount": 0.0,
            "share_percent": 0.0,
        }

    normalized_items = []
    for category_name, raw_amount in category_totals.items():
        clean_name = str(category_name or "").strip() or "Other"
        amount_value = _safe_amount(raw_amount)
        if amount_value <= 0:
            continue
        normalized_items.append((clean_name, amount_value))

    if not normalized_items:
        return {
            "category": "",
            "amount": 0.0,
            "share_percent": 0.0,
        }

    total_amount = sum(amount for _, amount in normalized_items)
    top_category, top_amount = sorted(
        normalized_items,
        key=lambda item: _safe_amount(item[1]),
        reverse=True,
    )[0]
    share_percent = ((top_amount / total_amount) * 100.0) if total_amount > 0 else 0.0
    return {
        "category": top_category,
        "amount": _safe_amount(top_amount),
        "share_percent": _safe_amount(share_percent),
    }


# VIVA: CHAT CALC - build the live finance snapshot that powers rule-based Rupy answers.
def _build_rupy_chat_snapshot(user_id, *, today_value=None):
    today = today_value if isinstance(today_value, date) else date.today()
    yesterday = today - timedelta(days=1)
    current_month = today.strftime("%Y-%m")
    month_label = _month_label(current_month)
    week_window_start = today - timedelta(days=6)

    expenses = list(
        collection.find(
            {"user_id": user_id},
            {"amount": 1, "category": 1, "description": 1, "date": 1},
        ).sort("date", -1)
    )
    expense_totals_by_month = _build_monthly_expense_map(expenses)
    monthly_expense = _safe_amount(expense_totals_by_month.get(current_month))

    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )
    monthly_budget = _safe_amount(budget_snapshot.get("effective_budget"))
    monthly_remaining = _safe_amount(budget_snapshot.get("remaining"))
    if monthly_budget > 0:
        monthly_spent_percent = (monthly_expense / monthly_budget) * 100.0
    else:
        monthly_spent_percent = 100.0 if monthly_expense > 0 else 0.0

    monthly_forecast = _build_monthly_forecast(
        current_month,
        monthly_expense,
        monthly_budget,
        reference_date=today,
    )
    days_in_month = max(
        1,
        _safe_int(
            monthly_forecast.get("days_in_month"),
            calendar.monthrange(today.year, today.month)[1],
        ),
    )
    daily_budget_cap = (monthly_budget / days_in_month) if monthly_budget > 0 else 0.0

    today_total = 0.0
    today_count = 0
    today_category_totals = {}
    yesterday_total = 0.0
    yesterday_count = 0
    yesterday_category_totals = {}
    weekly_category_totals = {}
    latest_expense_date = None
    for expense in expenses:
        parsed_date = _parse_record_date(expense.get("date"))
        if not parsed_date:
            continue
        if latest_expense_date is None or parsed_date > latest_expense_date:
            latest_expense_date = parsed_date

        amount_value = _safe_amount(expense.get("amount"))
        if amount_value <= 0:
            continue

        category_name = str(expense.get("category", "")).strip() or "Other"
        if parsed_date == today:
            today_count += 1
            today_total += amount_value
            today_category_totals[category_name] = (
                _safe_amount(today_category_totals.get(category_name)) + amount_value
            )
        if parsed_date == yesterday:
            yesterday_count += 1
            yesterday_total += amount_value
            yesterday_category_totals[category_name] = (
                _safe_amount(yesterday_category_totals.get(category_name)) + amount_value
            )
        if week_window_start <= parsed_date <= today:
            weekly_category_totals[category_name] = (
                _safe_amount(weekly_category_totals.get(category_name)) + amount_value
            )

    weekly_summary = _build_weekly_spending_summary(expenses, today_value=today)
    weekly_top_categories = (weekly_summary or {}).get("top_categories") or []
    weekly_top_category = weekly_top_categories[0] if weekly_top_categories else {}
    monthly_category_totals = _month_category_totals(expenses, current_month)
    top_month_category = _top_category_payload(monthly_category_totals)
    top_today_category = _top_category_payload(today_category_totals)
    top_yesterday_category = _top_category_payload(yesterday_category_totals)

    monthly_income = _sum_amount(
        incomes_collection.find(
            {"user_id": user_id, "date": {"$regex": f"^{current_month}"}},
            {"amount": 1, "date": 1},
        )
    )
    monthly_net = _safe_amount(monthly_income) - _safe_amount(monthly_expense)

    user_doc = users_collection.find_one({"_id": user_id}, {"gamification": 1}) or {}
    gamification = _gamification_state_from_user_doc(user_doc)
    level_progress = _derive_level_progress(gamification.get("xp", 0))
    streak_metrics = _build_streak_metrics(expenses, today_value=today)
    streak_days = _safe_int(streak_metrics.get("streak_days"), 0)
    best_streak = max(
        _safe_int(streak_metrics.get("best_streak"), 0),
        _safe_int(gamification.get("best_streak"), 0),
    )

    return {
        "today": today.strftime("%Y-%m-%d"),
        "current_month": current_month,
        "month_label": month_label,
        "today_total": _safe_amount(today_total),
        "today_count": max(0, _safe_int(today_count, 0)),
        "today_category_totals": today_category_totals,
        "top_today_category": top_today_category,
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "yesterday_total": _safe_amount(yesterday_total),
        "yesterday_count": max(0, _safe_int(yesterday_count, 0)),
        "yesterday_category_totals": yesterday_category_totals,
        "top_yesterday_category": top_yesterday_category,
        "monthly_budget": monthly_budget,
        "monthly_expense": monthly_expense,
        "monthly_remaining": monthly_remaining,
        "monthly_spent_percent": _safe_amount(monthly_spent_percent),
        "monthly_forecast": monthly_forecast,
        "daily_budget_cap": _safe_amount(daily_budget_cap),
        "monthly_category_totals": monthly_category_totals,
        "top_month_category": top_month_category,
        "weekly_summary": weekly_summary,
        "weekly_top_category": weekly_top_category,
        "weekly_category_totals": weekly_category_totals,
        "monthly_income": _safe_amount(monthly_income),
        "monthly_net": _safe_amount(monthly_net),
        "streak_days": streak_days,
        "best_streak": best_streak,
        "level": _safe_int(level_progress.get("level"), 1),
        "level_title": _gamification_level_title(_safe_int(level_progress.get("level"), 1)),
        "total_xp": max(0, _safe_int(gamification.get("xp"), 0)),
        "xp_in_level": _safe_int(level_progress.get("xp_in_level"), 0),
        "xp_needed": max(1, _safe_int(level_progress.get("xp_needed"), 100)),
        "inactive_24h": latest_expense_date is None or latest_expense_date < today,
    }


def _normalize_rupy_chat_context(raw_context=None):
    raw = raw_context if isinstance(raw_context, dict) else {}
    allowed_intents = {
        "default",
        "today_spend",
        "yesterday_spend",
        "budget_status",
        "weekly_summary",
        "top_category",
        "category_followup",
        "streak_xp",
        "savings",
        "inactivity",
        "no_spend_day",
    }
    allowed_timeframes = {"today", "yesterday", "weekly", "monthly", "overall", "unknown"}

    intent = str(raw.get("last_intent", "")).strip().lower()
    timeframe = str(raw.get("last_timeframe", "")).strip().lower()
    category = str(raw.get("last_category", "")).strip()

    return {
        "last_intent": intent if intent in allowed_intents else "default",
        "last_timeframe": timeframe if timeframe in allowed_timeframes else "unknown",
        "last_category": category[:60],
        "turn_count": max(0, _safe_int(raw.get("turn_count"), 0)),
    }


def _derive_rupy_chat_context(reply, snapshot=None, previous_context=None):
    previous = _normalize_rupy_chat_context(previous_context)
    reply = reply if isinstance(reply, dict) else {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}

    intent = str(reply.get("intent", "")).strip().lower() or previous.get("last_intent", "default")
    timeframe = previous.get("last_timeframe", "unknown")
    category = previous.get("last_category", "")

    intent_timeframe_map = {
        "today_spend": "today",
        "yesterday_spend": "yesterday",
        "no_spend_day": "today",
        "inactivity": "today",
        "weekly_summary": "weekly",
        "budget_status": "monthly",
        "top_category": "monthly",
        "category_followup": "monthly",
        "savings": "monthly",
        "streak_xp": "overall",
    }
    if intent in intent_timeframe_map:
        timeframe = intent_timeframe_map[intent]

    if intent == "today_spend":
        top_today = snapshot.get("top_today_category") or {}
        category = str(top_today.get("category", "")).strip() or category
    elif intent == "weekly_summary":
        top_weekly = snapshot.get("weekly_top_category") or {}
        category = str(top_weekly.get("category", "")).strip() or category
    elif intent == "top_category":
        top_month = snapshot.get("top_month_category") or {}
        category = str(top_month.get("category", "")).strip() or category
    elif intent == "category_followup":
        category = str(reply.get("focus_category", "")).strip() or category
    elif intent == "yesterday_spend":
        top_yesterday = snapshot.get("top_yesterday_category") or {}
        category = str(top_yesterday.get("category", "")).strip() or category

    return _normalize_rupy_chat_context(
        {
            "last_intent": intent,
            "last_timeframe": timeframe,
            "last_category": category,
            "turn_count": previous.get("turn_count", 0) + 1,
        }
    )


# VIVA: API/CHAT LOGIC - keyword-based intent detection answers questions without an external LLM call.
def _build_rupy_chat_reply(question, snapshot, *, context=None):
    clean_question = _normalize_search_text(question)
    snapshot = snapshot or {}
    context_data = _normalize_rupy_chat_context(context)

    def _contains(*keywords):
        return any(str(keyword).strip().lower() in clean_question for keyword in keywords if str(keyword).strip())

    def _state_event(state_name):
        state_key = str(state_name or "").strip().lower()
        mapping = {
            "money-rain": "no_spend_day",
            "celebration": "saving_money",
            "warning": "high_spending",
            "error": "high_spending",
            "thinking": "budget_planning",
            "happy": "budget_under_control",
            "idle": "tip",
        }
        return mapping.get(state_key, "tip")

    monthly_category_totals = snapshot.get("monthly_category_totals") or {}
    weekly_category_totals = snapshot.get("weekly_category_totals") or {}
    today_category_totals = snapshot.get("today_category_totals") or {}
    yesterday_category_totals = snapshot.get("yesterday_category_totals") or {}

    normalized_category_lookup = {}
    for category_name in monthly_category_totals.keys():
        clean_name = str(category_name or "").strip()
        if not clean_name:
            continue
        normalized_category_lookup[_normalize_search_text(clean_name)] = clean_name

    def _extract_category_from_question():
        for normalized_name, display_name in sorted(
            normalized_category_lookup.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if normalized_name and normalized_name in clean_question:
                return display_name
        return ""

    def _resolve_context_category():
        question_category = _extract_category_from_question()
        if question_category:
            return question_category

        last_category = str(context_data.get("last_category", "")).strip()
        if not last_category:
            return ""

        normalized_last = _normalize_search_text(last_category)
        if normalized_last in normalized_category_lookup:
            return normalized_category_lookup[normalized_last]
        return ""

    month_label = str(snapshot.get("month_label", "this month")).strip() or "this month"
    today_total = _safe_amount(snapshot.get("today_total"))
    today_count = max(0, _safe_int(snapshot.get("today_count"), 0))
    today_top = snapshot.get("top_today_category") or {}
    today_top_category = str(today_top.get("category", "")).strip()
    today_top_amount = _safe_amount(today_top.get("amount"))
    yesterday_total = _safe_amount(snapshot.get("yesterday_total"))
    yesterday_count = max(0, _safe_int(snapshot.get("yesterday_count"), 0))
    yesterday_top = snapshot.get("top_yesterday_category") or {}
    yesterday_top_category = str(yesterday_top.get("category", "")).strip()
    yesterday_top_amount = _safe_amount(yesterday_top.get("amount"))
    monthly_budget = _safe_amount(snapshot.get("monthly_budget"))
    monthly_expense = _safe_amount(snapshot.get("monthly_expense"))
    monthly_remaining = _safe_amount(snapshot.get("monthly_remaining"))
    monthly_spent_percent = _safe_amount(snapshot.get("monthly_spent_percent"))
    daily_budget_cap = _safe_amount(snapshot.get("daily_budget_cap"))
    monthly_forecast = snapshot.get("monthly_forecast") or {}
    forecast_over_by = _safe_amount(monthly_forecast.get("forecast_over_by"))
    weekly_summary = snapshot.get("weekly_summary") or {}
    weekly_total = _safe_amount(weekly_summary.get("total"))
    weekly_transactions = _safe_int(weekly_summary.get("transactions"), 0)
    weekend_total = _safe_amount(weekly_summary.get("weekend_total"))
    weekly_top = snapshot.get("weekly_top_category") or {}
    weekly_top_category = str(weekly_top.get("category", "")).strip()
    weekly_top_share = _safe_amount(weekly_top.get("share_percent"))
    top_month = snapshot.get("top_month_category") or {}
    month_top_category = str(top_month.get("category", "")).strip()
    month_top_amount = _safe_amount(top_month.get("amount"))
    month_top_share = _safe_amount(top_month.get("share_percent"))
    monthly_income = _safe_amount(snapshot.get("monthly_income"))
    monthly_net = _safe_amount(snapshot.get("monthly_net"))
    streak_days = max(0, _safe_int(snapshot.get("streak_days"), 0))
    best_streak = max(0, _safe_int(snapshot.get("best_streak"), 0))
    level = max(1, _safe_int(snapshot.get("level"), 1))
    level_title = str(snapshot.get("level_title", "")).strip() or _gamification_level_title(level)
    total_xp = max(0, _safe_int(snapshot.get("total_xp"), 0))
    xp_in_level = max(0, _safe_int(snapshot.get("xp_in_level"), 0))
    xp_needed = max(1, _safe_int(snapshot.get("xp_needed"), 100))
    inactive_24h = bool(snapshot.get("inactive_24h"))

    response = {
        "intent": "default",
        "state": "thinking",
        "event_type": "tip",
        "answer": "Ask me about spend, budget, streak, or weekly summary and I will guide fast.",
        "quick_replies": list(RUPY_CHAT_DEFAULT_QUICK_REPLIES),
        "focus_category": "",
        "timeframe": "monthly",
    }

    is_no_spend_question = _contains("no spend", "zero spend", "no-spend")
    is_today_spend_question = (
        (_contains("today", "aaj") and _contains("spend", "spent", "expense", "expenses", "kharch"))
        or _contains("spend today", "today spend", "aaj kitna")
    )
    is_budget_question = _contains(
        "budget",
        "limit",
        "remaining",
        "left",
        "bacha",
        "kitna bacha",
        "monthly budget",
    )
    is_weekly_question = _contains("week", "weekly", "hafta", "weekend")
    is_top_spending_question = _contains("top category", "highest", "most", "zyada", "max")
    is_streak_question = _contains("streak", "xp", "level", "rank", "apprentice")
    is_savings_question = _contains("saving", "savings", "save", "income", "net", "bachat")
    is_inactivity_question = _contains("inactive", "remind", "reminder", "miss", "bhool", "forgot")
    is_yesterday_question = _contains("yesterday", "kal", "previous day", "pichla din")
    is_followup_question = _contains("aur", "and", "also", "phir", "then", "next", "what else")
    is_category_followup = _contains(
        "us category",
        "that category",
        "same category",
        "us category ka",
        "that one",
        "uska",
    )

    explicit_intent_detected = any(
        [
            is_no_spend_question,
            is_today_spend_question,
            is_budget_question,
            is_weekly_question,
            is_top_spending_question,
            is_streak_question,
            is_savings_question,
            is_inactivity_question,
        ]
    )
    selected_category = _resolve_context_category()

    if is_category_followup and selected_category:
        response["intent"] = "category_followup"
        response["focus_category"] = selected_category
        response["timeframe"] = "monthly"

        category_month_spend = _safe_amount(monthly_category_totals.get(selected_category))
        category_week_spend = _safe_amount(weekly_category_totals.get(selected_category))
        category_today_spend = _safe_amount(today_category_totals.get(selected_category))
        category_yesterday_spend = _safe_amount(yesterday_category_totals.get(selected_category))
        month_share = (category_month_spend / monthly_expense * 100.0) if monthly_expense > 0 else 0.0

        if category_month_spend <= 0:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"No meaningful spend data is available yet for {selected_category} in {month_label}."
            )
        else:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"{selected_category}: {month_label} spend {_format_inr_message(category_month_spend)} "
                f"({month_share:.0f}% monthly share). "
                f"This week {_format_inr_message(category_week_spend)}, today {_format_inr_message(category_today_spend)}."
            )
            if category_yesterday_spend > 0:
                response["answer"] += f" Yesterday {_format_inr_message(category_yesterday_spend)}."
            if month_share >= 40:
                response["state"] = "warning"
                response["event_type"] = "high_spending"
                response["answer"] += " This category has a high impact, so keep a tight cap."
        response["quick_replies"] = [
            "How much did I spend today?",
            "Budget left this month?",
            "Show weekly summary",
        ]
        return response

    if is_yesterday_question and (
        not explicit_intent_detected
        or context_data.get("last_intent") in {"today_spend", "inactivity", "no_spend_day", "default"}
    ):
        response["intent"] = "yesterday_spend"
        response["timeframe"] = "yesterday"

        if yesterday_count <= 0:
            response["state"] = "thinking"
            response["event_type"] = "user_inactive"
            response["answer"] = "No expenses were logged yesterday."
        else:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"Yesterday you spent {_format_inr_message(yesterday_total)} across {yesterday_count} entries."
            )
            if yesterday_top_category:
                response["focus_category"] = yesterday_top_category
                response["answer"] += (
                    f" Top category: {yesterday_top_category} ({_format_inr_message(yesterday_top_amount)})."
                )
            if today_count > 0:
                delta = today_total - yesterday_total
                if delta > 0:
                    response["answer"] += f" Today is {_format_inr_message(delta)} higher than yesterday."
                elif delta < 0:
                    response["answer"] += f" Today is {_format_inr_message(abs(delta))} lower than yesterday."
                else:
                    response["answer"] += " Today and yesterday spending are almost the same."
        response["quick_replies"] = [
            "How much did I spend today?",
            "Budget left this month?",
            "Show weekly summary",
        ]
        return response

    if is_no_spend_question:
        response["intent"] = "no_spend_day"
        response["timeframe"] = "today"
        if today_total <= 0 and today_count == 0:
            response["state"] = "money-rain"
            response["event_type"] = "no_spend_day"
            response["answer"] = (
                "You are at zero spend today. No Spend Day is active. Keep the streak alive."
            )
        else:
            response["state"] = "warning"
            response["event_type"] = "high_spending"
            response["answer"] = (
                f"No Spend Day was broken today. Spend {_format_inr_message(today_total)} across {today_count} entries."
            )
        response["quick_replies"] = [
            "How much budget left this month?",
            "Show weekly summary",
            "How can I reduce spending this week?",
        ]
        return response

    if is_today_spend_question:
        response["intent"] = "today_spend"
        response["timeframe"] = "today"
        if today_count <= 0:
            response["state"] = "thinking"
            response["event_type"] = "user_inactive"
            response["answer"] = "No expenses have been logged today yet. Did you forget to add one?"
        else:
            response["state"] = "happy"
            response["event_type"] = "budget_under_control"
            response["answer"] = (
                f"Today you spent {_format_inr_message(today_total)} across {today_count} entries."
            )
            if today_top_category:
                response["focus_category"] = today_top_category
                response["answer"] += (
                    f" Top category: {today_top_category} ({_format_inr_message(today_top_amount)})."
                )
            if daily_budget_cap > 0 and today_total > (daily_budget_cap * 1.2):
                response["state"] = "warning"
                response["event_type"] = "high_spending"
                response["answer"] += (
                    f" You are running above the daily cap of {_format_inr_message(daily_budget_cap)}."
                )
        response["quick_replies"] = [
            "Budget left this month?",
            "Which category is highest this month?",
            "Show my streak",
        ]
        return response

    if is_budget_question:
        response["intent"] = "budget_status"
        response["timeframe"] = "monthly"
        if monthly_budget <= 0:
            response["state"] = "thinking"
            response["event_type"] = "budget_planning"
            response["answer"] = (
                "Monthly budget is not set. Configure it in Settings so smart alerts become accurate."
            )
        elif monthly_remaining < 0:
            response["state"] = "warning"
            response["event_type"] = "high_spending"
            response["answer"] = (
                f"{month_label} budget is exceeded. Overspend {_format_inr_message(abs(monthly_remaining))}. "
                "Pause low-priority spending now."
            )
        elif monthly_spent_percent >= 85 or forecast_over_by > 0:
            response["state"] = "warning"
            response["event_type"] = "high_spending"
            response["answer"] = (
                f"{month_label}: {_format_inr_message(monthly_remaining)} left, "
                f"{monthly_spent_percent:.0f}% budget already used."
            )
            if forecast_over_by > 0:
                response["answer"] += f" Forecast overspend risk: {_format_inr_message(forecast_over_by)}."
        else:
            response["state"] = "happy"
            response["event_type"] = "budget_under_control"
            response["answer"] = (
                f"Good pace. {month_label} budget left: {_format_inr_message(monthly_remaining)} "
                f"({monthly_spent_percent:.0f}% used)."
            )
        response["quick_replies"] = [
            "How much did I spend today?",
            "Show weekly summary",
            "How is my streak?",
        ]
        return response

    if is_weekly_question:
        response["intent"] = "weekly_summary"
        response["timeframe"] = "weekly"
        if weekly_total <= 0:
            response["state"] = "thinking"
            response["event_type"] = "user_inactive"
            response["answer"] = "Weekly summary is empty. Add one expense entry this week to unlock insights."
        else:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"This week spend: {_format_inr_message(weekly_total)} across {weekly_transactions} transactions."
            )
            if weekly_top_category:
                response["focus_category"] = weekly_top_category
                response["answer"] += (
                    f" Highest category: {weekly_top_category} ({weekly_top_share:.0f}% share)."
                )
            if monthly_budget > 0 and weekly_total > (monthly_budget * 0.4):
                response["state"] = "warning"
                response["event_type"] = "high_spending"
                response["answer"] += " Weekly pace is high compared to your budget. Tighten your cap."
            elif weekend_total > 0 and weekly_total > 0 and weekend_total >= (weekly_total * 0.45):
                response["answer"] += " Weekend spending spike detected. Keep a weekend cap active."
        response["quick_replies"] = [
            "Which category is highest this month?",
            "Budget left this month?",
            "Give me a spending tip",
        ]
        return response

    if is_top_spending_question:
        response["intent"] = "top_category"
        response["timeframe"] = "monthly"
        if monthly_expense <= 0 or not month_top_category:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = f"No meaningful spend data is available yet for {month_label}. Start logging and ask again."
        else:
            response["focus_category"] = month_top_category
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"{month_label} top category: {month_top_category} at {_format_inr_message(month_top_amount)} "
                f"({month_top_share:.0f}% share)."
            )
            if month_top_share >= 45:
                response["state"] = "warning"
                response["event_type"] = "high_spending"
                response["answer"] += " This category can break your budget fastest, so add a cap."
        response["quick_replies"] = [
            "How much did I spend today?",
            "Budget left this month?",
            "Show weekly summary",
        ]
        return response

    if is_streak_question:
        response["intent"] = "streak_xp"
        response["timeframe"] = "overall"
        xp_to_next = max(0, xp_needed - xp_in_level)
        response["state"] = "happy"
        response["event_type"] = "notification"
        response["answer"] = (
            f"Streak: {streak_days} day(s). Best streak: {best_streak}. "
            f"Level {level} ({level_title}) with {total_xp} XP. Next level in {xp_to_next} XP."
        )
        if streak_days >= 7:
            response["state"] = "celebration"
            response["event_type"] = "streak_milestone"
            response["answer"] += " Great streak. Keep it going today."
        response["quick_replies"] = [
            "How much did I spend today?",
            "Budget left this month?",
            "How much did I save this month?",
        ]
        return response

    if is_savings_question:
        response["intent"] = "savings"
        response["timeframe"] = "monthly"
        if monthly_income <= 0:
            response["state"] = "thinking"
            response["event_type"] = "budget_planning"
            response["answer"] = (
                f"{month_label} income entries are missing. Log income to get precise net savings insights."
            )
        elif monthly_net < 0:
            response["state"] = "warning"
            response["event_type"] = "high_spending"
            response["answer"] = (
                f"{month_label} net is negative by {_format_inr_message(abs(monthly_net))}. "
                "Bring expenses below income to recover."
            )
        else:
            response["state"] = "happy"
            response["event_type"] = "saving_money"
            response["answer"] = (
                f"{month_label} net savings: {_format_inr_message(monthly_net)} "
                f"(income {_format_inr_message(monthly_income)} vs expense {_format_inr_message(monthly_expense)})."
            )
            if monthly_net >= 5000:
                response["state"] = "celebration"
                response["answer"] += " Solid month. Rupy proud."
        response["quick_replies"] = [
            "How is my streak?",
            "Show weekly summary",
            "Budget left this month?",
        ]
        return response

    if is_inactivity_question:
        response["intent"] = "inactivity"
        response["timeframe"] = "today"
        if inactive_24h:
            response["state"] = "thinking"
            response["event_type"] = "user_inactive"
            response["answer"] = "No expense entries were logged in the last 24 hours. Add a quick log so your streak stays intact."
        else:
            response["state"] = "happy"
            response["event_type"] = "tip"
            response["answer"] = "You are active. Continue logging in real time for better weekly insights."
        response["quick_replies"] = [
            "How much did I spend today?",
            "Show my streak",
            "Budget left this month?",
        ]
        return response

    last_intent = str(context_data.get("last_intent", "default")).strip().lower()

    if is_followup_question and last_intent == "today_spend":
        response["intent"] = "yesterday_spend"
        response["timeframe"] = "yesterday"
        if yesterday_count > 0:
            response["state"] = "thinking"
            response["event_type"] = "tip"
            response["answer"] = (
                f"Yesterday you spent {_format_inr_message(yesterday_total)} across {yesterday_count} entries."
            )
            if yesterday_top_category:
                response["focus_category"] = yesterday_top_category
            if today_count > 0:
                delta = today_total - yesterday_total
                if delta > 0:
                    response["answer"] += f" Today is {_format_inr_message(delta)} higher."
                elif delta < 0:
                    response["answer"] += f" Today is {_format_inr_message(abs(delta))} lower."
        else:
            response["state"] = "thinking"
            response["event_type"] = "user_inactive"
            response["answer"] = "No expenses were logged yesterday."
        response["quick_replies"] = [
            "Budget left this month?",
            "Show weekly summary",
            "How is my streak?",
        ]
        return response

    if is_followup_question and last_intent == "budget_status":
        response["intent"] = "budget_status"
        response["timeframe"] = "monthly"
        response["state"] = "thinking"
        response["event_type"] = "budget_planning"
        if forecast_over_by > 0:
            response["state"] = "warning"
            response["event_type"] = "high_spending"
            response["answer"] = (
                f"More detail: forecast shows an overspend risk of {_format_inr_message(forecast_over_by)}. "
                "Add a hard cap to your top spending category."
            )
        else:
            response["answer"] = (
                f"More detail: keep your daily cap around {_format_inr_message(daily_budget_cap)} "
                f"to keep your {month_label} budget safe."
            )
        response["quick_replies"] = [
            "Which category is highest this month?",
            "Show weekly summary",
            "How much did I spend today?",
        ]
        return response

    if is_followup_question and last_intent == "weekly_summary":
        response["intent"] = "weekly_summary"
        response["timeframe"] = "weekly"
        response["state"] = "thinking"
        response["event_type"] = "tip"
        if weekend_total > 0:
            response["answer"] = (
                f"More detail: weekend spend is {_format_inr_message(weekend_total)}. "
                "Adding a weekend cap can improve weekly control."
            )
        elif weekly_top_category:
            response["focus_category"] = weekly_top_category
            response["answer"] = (
                f"More detail: {weekly_top_category} is still the top contributor ({weekly_top_share:.0f}% share)."
            )
        else:
            response["answer"] = "More weekly data is needed for deeper insights."
        response["quick_replies"] = [
            "Budget left this month?",
            "How much did I spend today?",
            "How is my streak?",
        ]
        return response

    response["intent"] = "default"
    response["timeframe"] = "monthly"
    response["state"] = "thinking"
    response["event_type"] = _state_event(response["state"])
    response["answer"] = (
        f"Quick snapshot: today {_format_inr_message(today_total)}, "
        f"{month_label} budget left {_format_inr_message(monthly_remaining)}, "
        f"streak {streak_days} day(s). Ask me for spend, budget, weekly, or streak details."
    )
    return response


# VIVA: AUTH - resolve the current logged-in user's id from Flask's request context.
def _current_user_id():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        abort(401)
    return current_user["_id"]


# VIVA: AUTH - protected routes require a valid session user; public routes stay open.
@app.before_request
def _require_login():
    g.current_user = _load_current_user_from_session()

    if request.endpoint is None:
        return None

    if request.endpoint in PUBLIC_ENDPOINTS:
        if g.current_user and request.endpoint in {"login", "register"}:
            return redirect(url_for("dashboard"))
        return None

    if g.current_user:
        return None

    next_url = request.full_path if request.query_string else request.path
    return redirect(url_for("login", next=next_url))


@app.context_processor
def _inject_current_user():
    current_user = getattr(g, "current_user", None)
    appearance_preferences = _appearance_preferences_from_user(current_user)
    app_language = appearance_preferences.get("language", DEFAULT_UI_LANGUAGE)
    post_login_splash = bool(session.pop("post_login_splash", False))
    favicon_version = _favicon_version()
    goal_counts = _goal_sidebar_counts(current_user)
    goal_ui_event = _normalize_goal_ui_event(session.pop("goal_ui_event", None))

    def _t(key, **kwargs):
        return _translate_text(key, language=app_language, **kwargs)

    return {
        "current_user": current_user,
        "category_ui": _category_ui,
        "notification_ui": _notification_ui,
        "avatar_style": _avatar_style,
        "current_avatar_preset": _avatar_preset_from_user(current_user),
        "current_avatar_image": _avatar_image_path_from_user(current_user),
        "app_theme": appearance_preferences.get("theme", DEFAULT_UI_THEME),
        "app_language": app_language,
        "favicon_version": favicon_version,
        "post_login_splash": post_login_splash,
        "profile_image_max_size_bytes": PROFILE_IMAGE_MAX_SIZE_BYTES,
        "profile_image_max_size_mb": PROFILE_IMAGE_MAX_SIZE_MB,
        "sidebar_goals_active_count": goal_counts.get("active", 0),
        "sidebar_goals_due_soon_count": goal_counts.get("due_soon", 0),
        "goal_ui_event": goal_ui_event,
        "t": _t,
    }


def _redirect_back(default_endpoint="expenses_page"):
    target = request.referrer
    if target and target != "None":
        return redirect(target)
    return redirect(url_for(default_endpoint))


# VIVA: VALIDATION - safely parse Mongo ObjectId values and reject malformed ids with 404.
def _parse_object_id(id_value):
    try:
        return ObjectId(id_value)
    except (InvalidId, TypeError):
        abort(404)


def _safe_amount(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _gamification_defaults():
    return {
        "xp": 0,
        "level": 1,
        "achievements": [],
        "best_streak": 0,
        "last_under_budget_reward_month": "",
        "last_savings_reward_month": "",
        "last_streak_reward_streak": 0,
        "daily_challenge_reward_key": "",
    }


def _gamification_state_from_user_doc(user_doc):
    defaults = _gamification_defaults()
    raw = {}
    if isinstance(user_doc, dict):
        raw = user_doc.get("gamification") or {}
    if not isinstance(raw, dict):
        raw = {}

    state = dict(defaults)
    state["xp"] = max(0, _safe_int(raw.get("xp"), defaults["xp"]))
    state["level"] = max(1, _safe_int(raw.get("level"), defaults["level"]))
    achievements = raw.get("achievements") if isinstance(raw.get("achievements"), list) else []
    state["achievements"] = [
        str(item).strip()
        for item in achievements
        if str(item).strip()
    ]
    state["best_streak"] = max(0, _safe_int(raw.get("best_streak"), 0))
    state["last_under_budget_reward_month"] = str(raw.get("last_under_budget_reward_month", "")).strip()
    state["last_savings_reward_month"] = str(raw.get("last_savings_reward_month", "")).strip()
    state["last_streak_reward_streak"] = max(0, _safe_int(raw.get("last_streak_reward_streak"), 0))
    state["daily_challenge_reward_key"] = str(raw.get("daily_challenge_reward_key", "")).strip()
    return state


def _xp_needed_for_level(level):
    safe_level = max(1, _safe_int(level, 1))
    return safe_level * 100


# VIVA: GAMIFICATION CALC - each level uses cumulative XP buckets where level N needs N * 100 XP.
def _derive_level_progress(total_xp):
    xp_pool = max(0, _safe_int(total_xp, 0))
    level = 1

    while True:
        required = _xp_needed_for_level(level)
        if xp_pool < required:
            break
        xp_pool -= required
        level += 1
        if level > 500:
            break

    xp_needed = _xp_needed_for_level(level)
    progress_percent = (xp_pool / xp_needed) * 100 if xp_needed > 0 else 0.0
    return {
        "level": level,
        "xp_in_level": xp_pool,
        "xp_needed": xp_needed,
        "progress_percent": max(0.0, min(progress_percent, 100.0)),
    }


def _gamification_level_title(level):
    safe_level = max(1, _safe_int(level, 1))
    ladder = [
        (10, "Rupy Legend"),
        (9, "Investor Mindset"),
        (8, "Wealth Builder"),
        (7, "Finance Ninja"),
        (6, "Budget Master"),
        (5, "Saver Pro"),
        (4, "Money Apprentice"),
        (3, "Smart Tracker"),
        (2, "Budget Rookie"),
    ]
    for minimum, title in ladder:
        if safe_level >= minimum:
            return title
    return "New Saver"


def _parse_record_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    raw = str(value or "").strip()
    if not raw:
        return None

    candidate = raw[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def _build_streak_metrics(expenses, today_value=None):
    today = today_value or date.today()
    expense_dates = []
    for item in expenses:
        parsed = _parse_record_date(item.get("date"))
        if parsed:
            expense_dates.append(parsed)

    date_set = set(expense_dates)
    streak = 0
    probe = today
    while probe in date_set:
        streak += 1
        probe -= timedelta(days=1)

    best_streak = 0
    if date_set:
        sorted_dates = sorted(date_set)
        chain = 0
        previous = None
        for day_value in sorted_dates:
            if previous and day_value == (previous + timedelta(days=1)):
                chain += 1
            else:
                chain = 1
            best_streak = max(best_streak, chain)
            previous = day_value

    today_expense_count = sum(1 for day_value in expense_dates if day_value == today)
    today_expense_total = sum(
        _safe_amount(item.get("amount"))
        for item in expenses
        if _parse_record_date(item.get("date")) == today
    )
    return {
        "streak_days": streak,
        "best_streak": best_streak,
        "today_expense_count": today_expense_count,
        "today_expense_total": today_expense_total,
    }


def _build_daily_challenge(stats, today_value=None):
    today = today_value or date.today()
    seed = today.toordinal() % 3
    date_key = today.strftime("%Y-%m-%d")
    month_days = calendar.monthrange(today.year, today.month)[1]

    if seed == 0:
        target = 3
        progress = min(stats.get("today_expense_count", 0), target)
        return {
            "id": f"track3-{date_key}",
            "key": "track3",
            "title": "Track 3 expenses today",
            "description": "Log at least 3 expense entries today.",
            "target": target,
            "progress": progress,
            "reward_xp": 50,
            "is_complete": progress >= target,
        }

    if seed == 1:
        month_budget = _safe_amount(stats.get("monthly_budget"))
        daily_cap = (month_budget / month_days) if month_budget > 0 else 0.0
        today_total = _safe_amount(stats.get("today_expense_total"))
        progress = 1 if month_budget > 0 and today_total <= daily_cap else 0
        return {
            "id": f"daily-cap-{date_key}",
            "key": "daily_cap",
            "title": "Stay under daily budget",
            "description": (
                f"Keep today's spend under ₹{daily_cap:,.0f}."
                if daily_cap > 0
                else "Set a monthly budget to unlock this challenge."
            ),
            "target": 1,
            "progress": progress,
            "reward_xp": 40,
            "is_complete": progress >= 1,
        }

    progress = 1 if _safe_int(stats.get("today_expense_count")) == 0 else 0
    return {
        "id": f"no-spend-{date_key}",
        "key": "no_spend",
        "title": "No Spend Day",
        "description": "Complete today with zero expenses.",
        "target": 1,
        "progress": progress,
        "reward_xp": 30,
        "is_complete": progress >= 1,
    }


def _evaluate_gamification_achievements(stats, unlocked_keys):
    unlocked = set(unlocked_keys or [])
    category_names = [str(item or "").strip().lower() for item in stats.get("categories", [])]

    checks = {
        "first_expense": _safe_int(stats.get("total_expenses")) >= 1,
        "streak_7": _safe_int(stats.get("streak_days")) >= 7,
        "budget_hero": bool(stats.get("has_budget")) and bool(stats.get("monthly_under_budget")),
        "saving_machine": _safe_amount(stats.get("monthly_savings")) >= 5000.0,
        "expense_detective": _safe_int(stats.get("total_expenses")) >= 50,
        "no_spend_day": _safe_int(stats.get("today_expense_count")) == 0,
        "smart_planner": bool(stats.get("has_budget")),
        "investor_mode": any("invest" in name for name in category_names),
        "emergency_saver": any(("emergency" in name) or ("fund" in name) for name in category_names),
    }

    newly_unlocked = []
    achievement_status = []
    for entry in GAMIFICATION_ACHIEVEMENTS:
        key = entry.get("key")
        is_unlocked = bool(checks.get(key)) or (key in unlocked)
        if is_unlocked and key not in unlocked:
            newly_unlocked.append(key)
            unlocked.add(key)
        achievement_status.append(
            {
                "key": key,
                "title": entry.get("title", key),
                "description": entry.get("description", ""),
                "unlocked": is_unlocked,
            }
        )
    return newly_unlocked, achievement_status


def _award_action_xp(user_id, action_key):
    xp_amount = max(0, _safe_int(GAMIFICATION_XP_ACTIONS.get(action_key), 0))
    if xp_amount <= 0:
        return {
            "xp_awarded": 0,
            "level_up": False,
            "new_level": 1,
        }

    user_doc = users_collection.find_one({"_id": user_id}, {"gamification": 1}) or {}
    gamification = _gamification_state_from_user_doc(user_doc)
    before_progress = _derive_level_progress(gamification.get("xp", 0))
    gamification["xp"] = max(0, _safe_int(gamification.get("xp")) + xp_amount)
    after_progress = _derive_level_progress(gamification["xp"])
    gamification["level"] = after_progress["level"]

    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "gamification": gamification,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {
        "xp_awarded": xp_amount,
        "level_up": after_progress["level"] > before_progress["level"],
        "new_level": after_progress["level"],
    }


# VIVA: GAMIFICATION CALC - derive streaks, daily challenge, XP rewards, and achievement unlocks.
def _build_gamification_dashboard_state(
    user_id,
    user_doc,
    *,
    expenses,
    categories,
    current_month,
    monthly_budget,
    monthly_expense,
    monthly_records,
):
    today_value = date.today()
    today_key = today_value.strftime("%Y-%m-%d")
    gamification = _gamification_state_from_user_doc(user_doc)
    streak_metrics = _build_streak_metrics(expenses, today_value=today_value)
    monthly_budget_value = _safe_amount(monthly_budget)
    monthly_expense_value = _safe_amount(monthly_expense)
    monthly_savings = max(0.0, monthly_budget_value - monthly_expense_value)

    stats = {
        "total_expenses": len(expenses),
        "streak_days": streak_metrics.get("streak_days", 0),
        "today_expense_count": streak_metrics.get("today_expense_count", 0),
        "today_expense_total": streak_metrics.get("today_expense_total", 0.0),
        "categories": categories,
        "has_budget": monthly_budget_value > 0,
        "monthly_under_budget": monthly_budget_value > 0 and monthly_expense_value <= monthly_budget_value,
        "monthly_savings": monthly_savings,
        "monthly_budget": monthly_budget_value,
        "monthly_expense": monthly_expense_value,
        "monthly_records": monthly_records,
        "today_key": today_key,
    }

    daily_challenge = _build_daily_challenge(stats, today_value=today_value)
    achievement_keys = set(gamification.get("achievements", []))
    new_achievement_keys, achievement_status = _evaluate_gamification_achievements(stats, achievement_keys)

    xp_gain = 0
    level_events = []

    if stats["monthly_under_budget"] and stats["monthly_records"] >= 5:
        if gamification.get("last_under_budget_reward_month") != current_month:
            xp_gain += GAMIFICATION_XP_ACTIONS["stay_under_budget"]
            gamification["last_under_budget_reward_month"] = current_month
            level_events.append("under_budget_reward")

    if monthly_savings >= 5000.0:
        if gamification.get("last_savings_reward_month") != current_month:
            xp_gain += GAMIFICATION_XP_ACTIONS["savings_goal_reached"]
            gamification["last_savings_reward_month"] = current_month
            level_events.append("savings_goal_reward")

    streak_days = _safe_int(streak_metrics.get("streak_days"))
    streak_milestone = (streak_days // 7) * 7
    if streak_milestone >= 7 and streak_milestone > _safe_int(gamification.get("last_streak_reward_streak"), 0):
        xp_gain += GAMIFICATION_XP_ACTIONS["streak_milestone"]
        gamification["last_streak_reward_streak"] = streak_milestone
        level_events.append("streak_reward")

    if daily_challenge.get("is_complete"):
        challenge_reward_key = str(daily_challenge.get("id", "")).strip()
        if challenge_reward_key and gamification.get("daily_challenge_reward_key") != challenge_reward_key:
            xp_gain += _safe_int(daily_challenge.get("reward_xp"), GAMIFICATION_XP_ACTIONS["daily_challenge"])
            gamification["daily_challenge_reward_key"] = challenge_reward_key
            level_events.append("daily_challenge_reward")

    if new_achievement_keys:
        gamification["achievements"] = sorted(set(gamification.get("achievements", [])) | set(new_achievement_keys))
        xp_gain += len(new_achievement_keys) * 25
        level_events.append("achievement_unlock")

    previous_progress = _derive_level_progress(gamification.get("xp", 0))
    gamification["xp"] = max(0, _safe_int(gamification.get("xp")) + xp_gain)
    current_progress = _derive_level_progress(gamification["xp"])
    gamification["level"] = current_progress["level"]
    gamification["best_streak"] = max(
        _safe_int(gamification.get("best_streak"), 0),
        _safe_int(streak_metrics.get("best_streak"), 0),
    )

    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "gamification": gamification,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {
        "level": current_progress["level"],
        "previous_level": previous_progress["level"],
        "level_title": _gamification_level_title(current_progress["level"]),
        "total_xp": max(0, _safe_int(gamification.get("xp"), 0)),
        "xp_in_level": current_progress["xp_in_level"],
        "xp_needed": current_progress["xp_needed"],
        "xp_progress_percent": current_progress["progress_percent"],
        "xp_gained_today": xp_gain,
        "level_up": current_progress["level"] > previous_progress["level"],
        "events": level_events,
        "streak_days": _safe_int(streak_metrics.get("streak_days"), 0),
        "best_streak": _safe_int(gamification.get("best_streak"), 0),
        "today_expense_count": _safe_int(streak_metrics.get("today_expense_count"), 0),
        "today_expense_total": _safe_amount(streak_metrics.get("today_expense_total"), 0.0),
        "daily_challenge": daily_challenge,
        "achievements": achievement_status,
        "new_achievements": new_achievement_keys,
        "unlocked_achievements_count": sum(1 for item in achievement_status if item.get("unlocked")),
    }


def _format_inr_message(value):
    return f"\u20b9{_safe_amount(value):,.2f}"


@app.template_filter("inr")
def _inr_filter(value):
    amount = _safe_amount(value)
    return f"{amount:,.2f}"


@app.template_filter("pretty_date")
def _pretty_date(value):
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    if isinstance(value, str):
        raw_value = value.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(raw_value, fmt).strftime("%d %b %Y")
            except ValueError:
                continue
        return raw_value if raw_value else "-"
    return "-"


# VIVA: INPUT VALIDATION - amount must be numeric and non-negative before saving.
def _parse_amount_from_form():
    value = request.form.get("amount", "").strip()
    try:
        amount = float(value)
    except (TypeError, ValueError):
        abort(400, description="Invalid amount")
    if amount < 0:
        abort(400, description="Amount cannot be negative")
    return amount


# VIVA: INPUT VALIDATION - dates must match YYYY-MM-DD before records are accepted.
def _parse_date_from_form(field_name="date"):
    raw_date = request.form.get(field_name, "").strip()
    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        abort(400, description=f"Invalid {field_name}")


def _parse_month_from_form(field_name="month"):
    raw_month = request.form.get(field_name, "").strip()
    try:
        return datetime.strptime(raw_month, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        abort(400, description="Invalid month format")


def _format_history_time(value):
    if not value:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%I:%M:%S %p")

    if not isinstance(value, str):
        return str(value)

    raw_value = value.strip()
    if not raw_value:
        return "-"

    for fmt in (
        "%d-%m-%Y %H:%M:%S",      # existing saved format
        "%d-%m-%Y %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%I:%M:%S %p",
        "%H:%M:%S",
    ):
        try:
            return datetime.strptime(raw_value, fmt).strftime("%I:%M:%S %p")
        except ValueError:
            continue

    return raw_value


def _normalize_history(expenses):
    for expense in expenses:
        expense["history"] = _format_history_time(expense.get("history"))


def _format_display_date(value):
    if not value:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")

    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")

    if not isinstance(value, str):
        return str(value)

    raw_value = value.strip()
    if not raw_value:
        return "-"

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw_value, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue

    return raw_value


def _normalize_display_dates(records, source_field="date", target_field="date_display"):
    for item in records:
        item[target_field] = _format_display_date(item.get(source_field))


def _current_history_time():
    return datetime.now().strftime("%I:%M:%S %p")


def _seed_default_categories(user_id):
    if categories_collection.count_documents({"user_id": user_id}) == 0:
        categories_collection.insert_many(
            [{"user_id": user_id, "name": name} for name in DEFAULT_CATEGORIES]
        )


def _get_categories():
    user_id = _current_user_id()
    categories = [
        str(doc.get("name", "")).strip()
        for doc in categories_collection.find({"user_id": user_id}).sort("name", 1)
    ]
    categories = [name for name in categories if name]
    if categories:
        return categories

    _seed_default_categories(user_id)
    categories = [
        str(doc.get("name", "")).strip()
        for doc in categories_collection.find({"user_id": user_id}).sort("name", 1)
    ]
    return [name for name in categories if name]


def _get_total_income():
    user_id = _current_user_id()
    return sum(
        _safe_amount(item.get("amount"))
        for item in incomes_collection.find({"user_id": user_id})
    )


def _sum_amount(records):
    return sum(_safe_amount(item.get("amount")) for item in records)


def _sum_amount_for_month(records, month_key):
    return sum(
        _safe_amount(item.get("amount"))
        for item in records
        if str(item.get("date", "")).startswith(month_key)
    )


def _count_records_for_month(records, month_key):
    return sum(
        1
        for item in records
        if str(item.get("date", "")).startswith(month_key)
    )


def _get_scope(default_scope="this_month"):
    raw_scope = str(request.args.get("scope", default_scope)).strip().lower()
    if raw_scope in ("this_month", "all_time"):
        return raw_scope
    return default_scope


def _month_label(month_key):
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    except (TypeError, ValueError):
        return "Unknown Month"


def _month_key_from_record_date(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")

    if isinstance(value, date):
        return value.strftime("%Y-%m")

    if not isinstance(value, str):
        return ""

    raw_value = value.strip()
    if not raw_value:
        return ""

    if len(raw_value) >= 7:
        candidate = raw_value[:7]
        try:
            datetime.strptime(candidate, "%Y-%m")
            return candidate
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw_value, fmt).strftime("%Y-%m")
        except ValueError:
            continue

    return ""


def _shift_month_key(month_key, delta):
    try:
        parsed = datetime.strptime(str(month_key or "").strip(), "%Y-%m")
    except (TypeError, ValueError):
        return ""

    absolute_month = (parsed.year * 12) + (parsed.month - 1) + int(delta)
    year, month_index = divmod(absolute_month, 12)
    return f"{year:04d}-{month_index + 1:02d}"


def _month_range(start_month, end_month):
    try:
        start_key = datetime.strptime(str(start_month or "").strip(), "%Y-%m").strftime("%Y-%m")
        end_key = datetime.strptime(str(end_month or "").strip(), "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return []

    if start_key > end_key:
        start_key, end_key = end_key, start_key

    months = []
    cursor = start_key
    safety_guard = 0
    while cursor and cursor <= end_key and safety_guard < 600:
        months.append(cursor)
        cursor = _shift_month_key(cursor, 1)
        safety_guard += 1
    return months


def _normalize_search_text(value):
    return " ".join(str(value or "").strip().lower().split())


def _slug_key(value):
    slug = re.sub(r"[^a-z0-9]+", "-", _normalize_search_text(value))
    return slug.strip("-") or "item"


def _parse_flexible_date(raw_value):
    clean_value = str(raw_value or "").strip()
    if not clean_value:
        return ""

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(clean_value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""


def _parse_optional_date_arg(raw_value, field_name):
    clean_value = str(raw_value or "").strip()
    if not clean_value:
        return ""

    parsed = _parse_flexible_date(clean_value)
    if parsed:
        return parsed
    abort(400, description=f"Invalid {field_name}")


def _parse_optional_amount_arg(raw_value, field_name):
    clean_value = str(raw_value or "").strip()
    if not clean_value:
        return None

    try:
        amount = float(clean_value)
    except (TypeError, ValueError):
        abort(400, description=f"Invalid {field_name}")

    if amount < 0:
        abort(400, description=f"{field_name} cannot be negative")
    return amount


def _parse_float_from_form(field_name, minimum=None, maximum=None):
    raw_value = request.form.get(field_name, "").strip()
    try:
        number = float(raw_value)
    except (TypeError, ValueError):
        abort(400, description=f"Invalid {field_name}")

    if minimum is not None and number < minimum:
        abort(400, description=f"{field_name} cannot be less than {minimum}")
    if maximum is not None and number > maximum:
        abort(400, description=f"{field_name} cannot be more than {maximum}")
    return number


def _parse_int_from_form(field_name, minimum=None, maximum=None):
    raw_value = request.form.get(field_name, "").strip()
    try:
        number = int(raw_value)
    except (TypeError, ValueError):
        abort(400, description=f"Invalid {field_name}")

    if minimum is not None and number < minimum:
        abort(400, description=f"{field_name} cannot be less than {minimum}")
    if maximum is not None and number > maximum:
        abort(400, description=f"{field_name} cannot be more than {maximum}")
    return number


def _expense_search_fields(amount_value, category_value, description_value):
    return {
        "amount_value": _safe_amount(amount_value),
        "category_search": _normalize_search_text(category_value),
        "merchant_search": _normalize_search_text(description_value),
    }


def _build_monthly_expense_map(expenses):
    totals_by_month = {}
    for item in expenses:
        month_key = _month_key_from_record_date(item.get("date"))
        if not month_key:
            continue
        totals_by_month[month_key] = totals_by_month.get(month_key, 0.0) + _safe_amount(item.get("amount"))
    return totals_by_month


# VIVA: BUDGET DATA - load month-wise budget limits for the current user from MongoDB.
def _get_budget_limits_map(user_id):
    budget_limits = {}
    for budget_doc in budgets_collection.find({"user_id": user_id}, {"month": 1, "limit": 1}):
        month_key = str(budget_doc.get("month", "")).strip()
        if not month_key:
            continue
        budget_limits[month_key] = _safe_amount(budget_doc.get("limit"))
    return budget_limits


def _normalize_category_limits(raw_limits, allowed_categories=None):
    normalized = {}
    allowed_lookup = {}
    if allowed_categories:
        for value in allowed_categories:
            category_name = str(value or "").strip()
            if not category_name:
                continue
            allowed_lookup[_normalize_category_key(category_name)] = category_name

    def _resolve_name(raw_name):
        clean_name = str(raw_name or "").strip()
        if not clean_name:
            return ""
        if not allowed_lookup:
            return clean_name
        return allowed_lookup.get(_normalize_category_key(clean_name), "")

    if isinstance(raw_limits, dict):
        raw_items = raw_limits.items()
    elif isinstance(raw_limits, list):
        raw_items = []
        for item in raw_limits:
            if not isinstance(item, dict):
                continue
            raw_items.append((item.get("category"), item.get("limit")))
    else:
        raw_items = []

    for raw_name, raw_limit in raw_items:
        resolved_name = _resolve_name(raw_name)
        if not resolved_name:
            continue
        safe_limit = _safe_amount(raw_limit)
        if safe_limit <= 0:
            continue
        normalized[resolved_name] = safe_limit

    return normalized


# VIVA: BUDGET DATA - fetch one month's budget and normalized category limits for calculations.
def _get_month_budget_doc(user_id, month_key, allowed_categories=None):
    normalized_month = str(month_key or "").strip()
    try:
        normalized_month = datetime.strptime(normalized_month, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return {
            "month": normalized_month,
            "limit": 0.0,
            "category_limits": {},
        }

    budget_doc = budgets_collection.find_one(
        {"user_id": user_id, "month": normalized_month},
        {"month": 1, "limit": 1, "category_limits": 1},
    ) or {}

    return {
        "month": normalized_month,
        "limit": _safe_amount(budget_doc.get("limit")),
        "category_limits": _normalize_category_limits(
            budget_doc.get("category_limits"),
            allowed_categories=allowed_categories,
        ),
    }


def _month_category_totals(records, month_key):
    totals = {}
    for item in records:
        item_month = _month_key_from_record_date(item.get("date"))
        if item_month != month_key:
            continue
        category_name = str(item.get("category", "")).strip() or "Other"
        totals[category_name] = totals.get(category_name, 0.0) + _safe_amount(item.get("amount"))
    return totals


# VIVA: FORECAST CALC - run-rate forecast = spent so far / elapsed days, then projected across the month.
def _build_monthly_forecast(month_key, spent_amount, budget_amount=0.0, reference_date=None):
    normalized_month = str(month_key or "").strip()
    try:
        month_date = datetime.strptime(normalized_month, "%Y-%m")
    except (TypeError, ValueError):
        return {
            "month": normalized_month,
            "days_in_month": 0,
            "days_elapsed": 0,
            "days_remaining": 0,
            "run_rate_daily": 0.0,
            "projected_total": 0.0,
            "forecast_over_by": 0.0,
            "forecast_buffer": 0.0,
            "confidence": "low",
        }

    spent = max(_safe_amount(spent_amount), 0.0)
    budget = max(_safe_amount(budget_amount), 0.0)
    today = reference_date if isinstance(reference_date, date) else date.today()

    days_in_month = calendar.monthrange(month_date.year, month_date.month)[1]
    current_month_key = today.strftime("%Y-%m")
    if normalized_month < current_month_key:
        days_elapsed = days_in_month
    elif normalized_month > current_month_key:
        days_elapsed = 0
    else:
        days_elapsed = max(1, min(today.day, days_in_month))

    days_remaining = max(0, days_in_month - days_elapsed)
    run_rate_daily = (spent / days_elapsed) if days_elapsed > 0 else 0.0
    projected_total = (run_rate_daily * days_in_month) if days_elapsed > 0 else 0.0

    if budget > 0:
        forecast_over_by = max(0.0, projected_total - budget)
        forecast_buffer = max(0.0, budget - projected_total)
    else:
        forecast_over_by = 0.0
        forecast_buffer = 0.0

    elapsed_ratio = (days_elapsed / days_in_month) if days_in_month > 0 else 0.0
    confidence = "high" if elapsed_ratio >= 0.55 else ("medium" if elapsed_ratio >= 0.28 else "low")

    return {
        "month": normalized_month,
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "run_rate_daily": run_rate_daily,
        "projected_total": projected_total,
        "forecast_over_by": forecast_over_by,
        "forecast_buffer": forecast_buffer,
        "confidence": confidence,
    }


def _build_category_budget_status(category_totals, category_limits):
    labels = sorted(set(category_totals.keys()) | set(category_limits.keys()))
    status_rows = []
    for category_name in labels:
        spent = max(_safe_amount(category_totals.get(category_name)), 0.0)
        limit = max(_safe_amount(category_limits.get(category_name)), 0.0)
        if limit > 0:
            usage_percent = (spent / limit) * 100.0
            remaining = limit - spent
            if spent > limit:
                tone = "over"
            elif usage_percent >= 85:
                tone = "warning"
            else:
                tone = "safe"
        else:
            usage_percent = 0.0
            remaining = 0.0
            tone = "no-limit"

        status_rows.append(
            {
                "category": category_name,
                "spent": spent,
                "limit": limit,
                "remaining": remaining,
                "usage_percent": usage_percent,
                "tone": tone,
            }
        )

    severity_rank = {"over": 3, "warning": 2, "safe": 1, "no-limit": 0}
    status_rows.sort(
        key=lambda item: (
            -severity_rank.get(item.get("tone"), 0),
            -_safe_amount(item.get("usage_percent")),
            -_safe_amount(item.get("spent")),
        )
    )
    return status_rows


def _build_cut_suggestions(
    category_totals,
    category_limits,
    monthly_budget=0.0,
    monthly_spent=0.0,
    forecast_over_by=0.0,
):
    total_spent = max(_safe_amount(monthly_spent), 0.0)
    monthly_budget = max(_safe_amount(monthly_budget), 0.0)
    forecast_over_by = max(_safe_amount(forecast_over_by), 0.0)
    overshoot_now = max(0.0, total_spent - monthly_budget) if monthly_budget > 0 else 0.0
    urgency_pool = max(overshoot_now, forecast_over_by)

    suggestions = []
    if total_spent <= 0:
        return suggestions

    for category_name, raw_spent in category_totals.items():
        spent = max(_safe_amount(raw_spent), 0.0)
        if spent <= 0:
            continue

        limit = max(_safe_amount(category_limits.get(category_name)), 0.0)
        share_percent = (spent / total_spent) * 100.0 if total_spent > 0 else 0.0
        over_by = max(0.0, spent - limit) if limit > 0 else 0.0

        if limit > 0 and spent > limit:
            suggested_cut = max(over_by * 0.75, spent * 0.12)
            reason = "Over category limit"
            priority = 3
        elif limit > 0 and spent >= (limit * 0.9):
            suggested_cut = max((spent - (limit * 0.85)), spent * 0.08)
            reason = "Close to category limit"
            priority = 2
        elif urgency_pool > 0 and share_percent >= 12:
            suggested_cut = max((urgency_pool * (share_percent / 100.0)), spent * 0.07)
            reason = "High contribution to overspend risk"
            priority = 2
        elif share_percent >= 18:
            suggested_cut = spent * 0.08
            reason = "Highest share this month"
            priority = 1
        else:
            continue

        suggested_cut = min(spent, max(0.0, suggested_cut))
        if suggested_cut < 50:
            continue

        suggestions.append(
            {
                "category": category_name,
                "spent": spent,
                "limit": limit,
                "over_by": over_by,
                "share_percent": share_percent,
                "suggested_cut_week": suggested_cut,
                "reason": reason,
                "priority": priority,
            }
        )

    suggestions.sort(
        key=lambda item: (
            -int(item.get("priority", 0)),
            -_safe_amount(item.get("suggested_cut_week")),
            -_safe_amount(item.get("spent")),
        )
    )
    return suggestions[:4]


def _real_time_budget_alerts(user_id, month_key, category_name=None):
    normalized_month = str(month_key or "").strip()
    try:
        normalized_month = datetime.strptime(normalized_month, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return []

    user_categories = _get_categories()
    budget_doc = _get_month_budget_doc(user_id, normalized_month, allowed_categories=user_categories)
    monthly_limit = _safe_amount(budget_doc.get("limit"))
    category_limits = budget_doc.get("category_limits", {})

    month_expenses = list(
        collection.find(
            {"user_id": user_id, "date": {"$regex": f"^{normalized_month}"}},
            {"amount": 1, "category": 1, "date": 1},
        )
    )
    month_total = _sum_amount(month_expenses)
    category_totals = _month_category_totals(month_expenses, normalized_month)
    alerts = []

    if monthly_limit > 0:
        month_usage_percent = (month_total / monthly_limit) * 100.0
        if month_total > monthly_limit:
            alerts.append(
                f"Monthly budget exceeded by {_format_inr_message(month_total - monthly_limit)}."
            )
        elif month_usage_percent >= 90:
            alerts.append(
                f"Monthly budget usage is {month_usage_percent:.0f}%."
            )

    clean_category_name = str(category_name or "").strip()
    if clean_category_name and category_limits:
        category_limit = _safe_amount(category_limits.get(clean_category_name))
        if category_limit > 0:
            category_spent = _safe_amount(category_totals.get(clean_category_name))
            category_usage_percent = (category_spent / category_limit) * 100.0
            if category_spent > category_limit:
                alerts.append(
                    f"{clean_category_name} limit exceeded by {_format_inr_message(category_spent - category_limit)}."
                )
            elif category_usage_percent >= 90:
                alerts.append(
                    f"{clean_category_name} is at {category_usage_percent:.0f}% of its limit."
                )

    return alerts


def _get_budget_preferences(user_id):
    user_doc = users_collection.find_one(
        {"_id": user_id},
        {
            "ui_preferences.budget_rollover_enabled": 1,
            "ui_preferences.carry_forward_deficit": 1,
        },
    )
    ui_preferences = (user_doc or {}).get("ui_preferences", {})
    rollover_enabled = bool(ui_preferences.get("budget_rollover_enabled", True))
    carry_forward_deficit = bool(ui_preferences.get("carry_forward_deficit", True))
    return {
        "rollover_enabled": rollover_enabled,
        "carry_forward_deficit": carry_forward_deficit,
    }


def _clamp_number(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _get_anomaly_preferences(user_id):
    user_doc = users_collection.find_one(
        {"_id": user_id},
        {
            "ui_preferences.anomaly_threshold_percent": 1,
            "ui_preferences.anomaly_min_delta": 1,
            "ui_preferences.anomaly_baseline_months": 1,
        },
    )
    ui_preferences = (user_doc or {}).get("ui_preferences", {})
    threshold_percent = _safe_amount(ui_preferences.get("anomaly_threshold_percent"), 40.0)
    min_delta = _safe_amount(ui_preferences.get("anomaly_min_delta"), 100.0)
    baseline_months = int(_safe_amount(ui_preferences.get("anomaly_baseline_months"), 3))

    threshold_percent = _clamp_number(threshold_percent, 10.0, 300.0)
    min_delta = _clamp_number(min_delta, 0.0, 1000000.0)
    baseline_months = int(_clamp_number(baseline_months, 2, 12))

    return {
        "threshold_percent": threshold_percent,
        "min_delta": min_delta,
        "baseline_months": baseline_months,
    }


# VIVA: BUDGET CALC - effective budget = base budget + carry_in, and remaining = effective budget - spent.
def _compute_budget_snapshot(month_key, budget_limits_map, expense_totals_by_month, budget_preferences):
    normalized_month = str(month_key or "").strip()
    try:
        normalized_month = datetime.strptime(normalized_month, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return {
            "month": normalized_month,
            "base_budget": 0.0,
            "carry_in": 0.0,
            "effective_budget": 0.0,
            "spent": 0.0,
            "remaining": 0.0,
            "carry_out": 0.0,
            "rollover_enabled": bool((budget_preferences or {}).get("rollover_enabled")),
            "carry_forward_deficit": bool((budget_preferences or {}).get("carry_forward_deficit")),
        }

    budget_preferences = budget_preferences or {}
    rollover_enabled = bool(budget_preferences.get("rollover_enabled", True))
    carry_forward_deficit = bool(budget_preferences.get("carry_forward_deficit", True))

    reference_months = set()
    for value in budget_limits_map.keys():
        candidate = str(value or "").strip()
        try:
            candidate = datetime.strptime(candidate, "%Y-%m").strftime("%Y-%m")
            reference_months.add(candidate)
        except (TypeError, ValueError):
            continue
    for value in expense_totals_by_month.keys():
        candidate = str(value or "").strip()
        try:
            candidate = datetime.strptime(candidate, "%Y-%m").strftime("%Y-%m")
            reference_months.add(candidate)
        except (TypeError, ValueError):
            continue
    reference_months = {value for value in reference_months if value <= normalized_month}

    if reference_months:
        start_month = min(reference_months)
    else:
        start_month = normalized_month

    carry_balance = 0.0
    snapshot = {
        "month": normalized_month,
        "base_budget": 0.0,
        "carry_in": 0.0,
        "effective_budget": 0.0,
        "spent": 0.0,
        "remaining": 0.0,
        "carry_out": 0.0,
        "rollover_enabled": rollover_enabled,
        "carry_forward_deficit": carry_forward_deficit,
    }

    for candidate_month in _month_range(start_month, normalized_month):
        base_budget = _safe_amount(budget_limits_map.get(candidate_month))
        spent = _safe_amount(expense_totals_by_month.get(candidate_month))
        carry_in = carry_balance if rollover_enabled else 0.0
        if carry_in < 0 and not carry_forward_deficit:
            carry_in = 0.0

        effective_budget = base_budget + carry_in
        remaining = effective_budget - spent

        if rollover_enabled:
            if remaining >= 0:
                carry_balance = remaining
            elif carry_forward_deficit:
                carry_balance = remaining
            else:
                carry_balance = 0.0
        else:
            carry_balance = 0.0

        if candidate_month == normalized_month:
            snapshot = {
                "month": candidate_month,
                "base_budget": base_budget,
                "carry_in": carry_in,
                "effective_budget": effective_budget,
                "spent": spent,
                "remaining": remaining,
                "carry_out": carry_balance,
                "rollover_enabled": rollover_enabled,
                "carry_forward_deficit": carry_forward_deficit,
            }

    return snapshot


# VIVA: ANOMALY CALC - compare current spending against prior-month averages using percent and amount thresholds.
def _analyze_spending_anomalies(
    expenses,
    current_month,
    threshold_percent=40.0,
    min_amount_delta=100.0,
    baseline_months_count=3,
):
    threshold_percent = _clamp_number(_safe_amount(threshold_percent, 40.0), 10.0, 300.0)
    min_amount_delta = _clamp_number(_safe_amount(min_amount_delta, 100.0), 0.0, 1000000.0)
    baseline_months_count = int(_clamp_number(_safe_amount(baseline_months_count, 3), 2, 12))

    monthly_totals = _build_monthly_expense_map(expenses)
    category_monthly_totals = {}
    for item in expenses:
        month_key = _month_key_from_record_date(item.get("date"))
        if not month_key:
            continue
        category_name = str(item.get("category", "")).strip() or "General"
        category_monthly_totals.setdefault(month_key, {})
        category_monthly_totals[month_key][category_name] = (
            category_monthly_totals[month_key].get(category_name, 0.0) + _safe_amount(item.get("amount"))
        )

    baseline_months = []
    for offset in range(1, baseline_months_count + 1):
        candidate = _shift_month_key(current_month, -offset)
        if candidate:
            baseline_months.append(candidate)

    baseline_values = [monthly_totals.get(month_key, 0.0) for month_key in baseline_months]
    baseline_average = (sum(baseline_values) / len(baseline_values)) if baseline_values else 0.0
    current_total = _safe_amount(monthly_totals.get(current_month))

    overall = None
    threshold_multiplier = 1 + (threshold_percent / 100.0)
    if baseline_average > 0 and current_total >= (baseline_average * threshold_multiplier):
        increase_percent = ((current_total - baseline_average) / baseline_average) * 100
        overall = {
            "percent": increase_percent,
            "current_total": current_total,
            "baseline_average": baseline_average,
        }

    current_category_totals = category_monthly_totals.get(current_month, {})
    category_alerts = []
    for category_name, current_value in current_category_totals.items():
        baseline_category_values = [
            category_monthly_totals.get(month_key, {}).get(category_name, 0.0)
            for month_key in baseline_months
        ]
        baseline_category_average = (
            sum(baseline_category_values) / len(baseline_category_values)
            if baseline_category_values
            else 0.0
        )
        if baseline_category_average <= 0:
            continue
        if current_value < (baseline_category_average * threshold_multiplier):
            continue
        if (current_value - baseline_category_average) < min_amount_delta:
            continue

        increase_percent = ((current_value - baseline_category_average) / baseline_category_average) * 100
        category_alerts.append(
            {
                "category": category_name,
                "percent": increase_percent,
                "current_total": current_value,
                "baseline_average": baseline_category_average,
            }
        )

    category_alerts.sort(key=lambda item: item.get("percent", 0.0), reverse=True)
    return {
        "overall": overall,
        "categories": category_alerts[:3],
        "baseline_months": baseline_months,
        "baseline_month_labels": [_month_label(month_key) for month_key in baseline_months],
        "baseline_average": baseline_average,
        "current_total": current_total,
        "threshold_percent": threshold_percent,
        "min_amount_delta": min_amount_delta,
        "baseline_months_count": baseline_months_count,
        "triggered": bool(overall or category_alerts),
    }


def _get_month_filter(param_name, default_value="all"):
    raw_value = str(request.args.get(param_name, default_value)).strip().lower()
    if raw_value == "all":
        return "all"

    try:
        return datetime.strptime(raw_value, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return default_value


def _filter_records_by_month(records, month_filter):
    if month_filter == "all":
        return records

    return [
        item
        for item in records
        if _month_key_from_record_date(item.get("date")) == month_filter
    ]


def _group_records_by_month(records):
    grouped = {}
    ordered_months = []

    for item in records:
        month_key = _month_key_from_record_date(item.get("date")) or "unknown"
        if month_key not in grouped:
            grouped[month_key] = {
                "month_key": month_key,
                "month_label": _month_label(month_key),
                "records": [],
                "total": 0.0,
                "count": 0,
            }
            ordered_months.append(month_key)

        grouped[month_key]["records"].append(item)
        grouped[month_key]["total"] += _safe_amount(item.get("amount"))
        grouped[month_key]["count"] += 1

    return [grouped[month_key] for month_key in ordered_months]


def _build_month_options(*record_sets):
    month_keys = set()
    for records in record_sets:
        for item in records:
            month_key = _month_key_from_record_date(item.get("date"))
            if month_key:
                month_keys.add(month_key)

    return [
        {"value": month_key, "label": _month_label(month_key)}
        for month_key in sorted(month_keys, reverse=True)
    ]


def _normalize_goal_type(value):
    clean_value = str(value or "").strip().lower()
    if clean_value not in GOAL_TYPE_META:
        return GOAL_TYPE_SAVINGS
    return clean_value


def _normalize_goal_status(value):
    clean_value = str(value or "").strip().lower()
    if clean_value not in {GOAL_STATUS_ACTIVE, GOAL_STATUS_COMPLETED, GOAL_STATUS_ARCHIVED}:
        return GOAL_STATUS_ACTIVE
    return clean_value


def _normalize_goal_recurrence(value):
    clean_value = str(value or "").strip().lower()
    if clean_value == GOAL_RECURRENCE_MONTHLY:
        return GOAL_RECURRENCE_MONTHLY
    return ""


def _goal_type_meta(goal_type):
    normalized_type = _normalize_goal_type(goal_type)
    return GOAL_TYPE_META.get(normalized_type, GOAL_TYPE_META[GOAL_TYPE_SAVINGS])


def _goal_templates_for_form(categories, current_month, *, today_value=None):
    today = today_value or date.today()
    category_map = {str(name).strip().lower(): str(name).strip() for name in categories or []}
    template_items = []

    for template in GOAL_TEMPLATES:
        due_days = max(0, _safe_int(template.get("due_days"), 0))
        due_date = ""
        if due_days > 0:
            due_date = (today + timedelta(days=due_days)).strftime("%Y-%m-%d")

        raw_category = str(template.get("category", "")).strip()
        normalized_category = category_map.get(raw_category.lower(), "") if raw_category else ""

        template_items.append(
            {
                "key": str(template.get("key", "")).strip(),
                "title": str(template.get("title", "")).strip() or "Goal Template",
                "goal_type": _normalize_goal_type(template.get("goal_type")),
                "target_amount": max(0.01, _safe_amount(template.get("target_amount"), 0.0)),
                "category": normalized_category,
                "tracking_month": current_month,
                "is_recurring": _normalize_goal_recurrence(template.get("recurrence")) == GOAL_RECURRENCE_MONTHLY,
                "due_date": due_date,
            }
        )

    return template_items


def _goal_due_context(due_date_value, *, today_value=None):
    today = today_value or date.today()
    due_date = _parse_record_date(due_date_value)
    if not due_date:
        return {
            "days_left": None,
            "is_due_soon": False,
            "is_overdue": False,
            "due_label": "No deadline",
            "due_date": "",
            "due_date_display": "-",
        }

    days_left = (due_date - today).days
    is_overdue = days_left < 0
    is_due_soon = 0 <= days_left <= 7

    if days_left < 0:
        due_label = f"Overdue by {abs(days_left)} day{'s' if abs(days_left) != 1 else ''}"
    elif days_left == 0:
        due_label = "Due today"
    elif days_left == 1:
        due_label = "Due in 1 day"
    else:
        due_label = f"Due in {days_left} days"

    return {
        "days_left": days_left,
        "is_due_soon": is_due_soon,
        "is_overdue": is_overdue,
        "due_label": due_label,
        "due_date": due_date.strftime("%Y-%m-%d"),
        "due_date_display": due_date.strftime("%d %b %Y"),
    }


def _goal_due_date_for_month(due_date_value, month_key):
    base_due_date = _parse_record_date(due_date_value)
    if not base_due_date:
        return ""

    try:
        month_anchor = datetime.strptime(str(month_key or "").strip(), "%Y-%m").date()
    except (TypeError, ValueError):
        return base_due_date.strftime("%Y-%m-%d")

    max_days = calendar.monthrange(month_anchor.year, month_anchor.month)[1]
    target_day = min(base_due_date.day, max_days)
    return date(month_anchor.year, month_anchor.month, target_day).strftime("%Y-%m-%d")


def _goal_current_progress(goal_doc, *, monthly_totals_by_category, total_income, total_expense, current_month):
    goal_type = _normalize_goal_type(goal_doc.get("goal_type"))
    target_amount = max(0.01, _safe_amount(goal_doc.get("target_amount"), 0.0))
    category_label = str(goal_doc.get("category", "")).strip()
    category_key = category_label.lower()
    tracking_month = str(goal_doc.get("tracking_month", "")).strip()

    if goal_type == GOAL_TYPE_SPENDING_CAP:
        try:
            tracking_month = datetime.strptime(tracking_month, "%Y-%m").strftime("%Y-%m")
        except (TypeError, ValueError):
            tracking_month = current_month
    else:
        tracking_month = current_month

    if goal_type == GOAL_TYPE_SAVINGS:
        current_value = max(0.0, total_income - total_expense)
        remaining_value = max(0.0, target_amount - current_value)
        progress_percent = min((current_value / target_amount) * 100, 100.0)
        progress_title = (
            f"Saved {_format_inr_message(current_value)} of {_format_inr_message(target_amount)}"
        )
        detail_copy = "Tracked from total income minus total expenses."
        is_over_limit = False
    else:
        month_bucket = monthly_totals_by_category.get(tracking_month, {})
        current_value = _safe_amount(month_bucket.get(category_key)) if category_key else _safe_amount(month_bucket.get("__all__"))
        remaining_value = target_amount - current_value
        progress_percent = min(max((current_value / target_amount) * 100, 0.0), 100.0)
        scope_label = category_label if category_label else "All categories"
        progress_title = (
            f"Spent {_format_inr_message(current_value)} of {_format_inr_message(target_amount)} cap"
        )
        detail_copy = f"{scope_label} in {_month_label(tracking_month)}."
        is_over_limit = remaining_value < 0

    return {
        "goal_type": goal_type,
        "target_amount": target_amount,
        "current_value": max(0.0, _safe_amount(current_value)),
        "remaining_value": remaining_value,
        "progress_percent": progress_percent,
        "is_over_limit": is_over_limit,
        "category_label": category_label,
        "tracking_month": tracking_month,
        "tracking_month_label": _month_label(tracking_month),
        "progress_title": progress_title,
        "detail_copy": detail_copy,
        "is_recurring": bool(goal_doc.get("is_recurring", False)),
        "recurrence": _normalize_goal_recurrence(goal_doc.get("recurrence")),
    }


def _goal_eta_insight(
    goal_doc,
    progress,
    *,
    today_value,
    current_month,
    monthly_totals_by_category,
    monthly_income_totals,
    record_start_date,
):
    goal_type = _normalize_goal_type(progress.get("goal_type"))
    target_amount = max(0.01, _safe_amount(progress.get("target_amount"), 0.0))
    current_value = max(0.0, _safe_amount(progress.get("current_value"), 0.0))
    due_date = _parse_record_date(goal_doc.get("due_date"))

    if current_value >= target_amount and goal_type == GOAL_TYPE_SAVINGS:
        return {
            "eta_copy": "Target already achieved.",
            "eta_tone": "safe",
            "projected_days_delta": 0,
            "projected_finish_date": today_value.strftime("%Y-%m-%d"),
        }

    if goal_type == GOAL_TYPE_SAVINGS:
        created_date = _parse_record_date(goal_doc.get("created_at")) or record_start_date or today_value
        elapsed_days = max(1, (today_value - created_date).days + 1)
        daily_gain = current_value / elapsed_days
        if daily_gain <= 0:
            return {
                "eta_copy": "No savings pace yet. Add income or cut spend to start ETA.",
                "eta_tone": "warning",
                "projected_days_delta": None,
                "projected_finish_date": "",
            }

        days_to_target = max(0, int(math.ceil(max(0.0, target_amount - current_value) / daily_gain)))
        projected_finish = today_value + timedelta(days=days_to_target)
        if due_date:
            delta_days = (projected_finish - due_date).days
            if delta_days > 0:
                eta_copy = f"At this pace, about {delta_days} days late."
                eta_tone = "warning"
            elif delta_days < 0:
                eta_copy = f"At this pace, about {abs(delta_days)} days early."
                eta_tone = "safe"
            else:
                eta_copy = "On pace to hit the exact deadline."
                eta_tone = "safe"
        else:
            eta_copy = f"At current pace, target in about {days_to_target} days."
            eta_tone = "neutral"

        return {
            "eta_copy": eta_copy,
            "eta_tone": eta_tone,
            "projected_days_delta": (projected_finish - due_date).days if due_date else days_to_target,
            "projected_finish_date": projected_finish.strftime("%Y-%m-%d"),
        }

    tracking_month = str(progress.get("tracking_month", "")).strip() or current_month
    try:
        month_anchor = datetime.strptime(tracking_month, "%Y-%m").date()
    except (TypeError, ValueError):
        month_anchor = datetime.strptime(current_month, "%Y-%m").date()
    month_days = calendar.monthrange(month_anchor.year, month_anchor.month)[1]
    month_end = date(month_anchor.year, month_anchor.month, month_days)

    if current_value >= target_amount:
        return {
            "eta_copy": "Cap already exceeded. Reduce spend pace immediately.",
            "eta_tone": "warning",
            "projected_days_delta": 0,
            "projected_finish_date": today_value.strftime("%Y-%m-%d"),
        }

    if month_anchor.year == today_value.year and month_anchor.month == today_value.month:
        elapsed_days = max(1, today_value.day)
        remaining_days_in_month = max(0, (month_end - today_value).days)
    else:
        elapsed_days = month_days
        remaining_days_in_month = 0

    daily_spend = current_value / elapsed_days
    if daily_spend <= 0:
        return {
            "eta_copy": "Spend pace is stable. Cap risk is low.",
            "eta_tone": "safe",
            "projected_days_delta": None,
            "projected_finish_date": "",
        }

    days_until_cap = max(0, int(math.ceil(max(0.0, target_amount - current_value) / daily_spend)))
    projected_cross_date = today_value + timedelta(days=days_until_cap)

    if due_date:
        days_to_due = (due_date - today_value).days
        if days_until_cap < days_to_due:
            eta_copy = f"At this pace cap may break about {max(0, days_to_due - days_until_cap)} days before deadline."
            eta_tone = "warning"
        else:
            eta_copy = "At this pace, cap should hold until deadline."
            eta_tone = "safe"
    elif days_until_cap <= remaining_days_in_month:
        eta_copy = f"At this pace cap may break in about {days_until_cap} days."
        eta_tone = "warning"
    else:
        eta_copy = "At this pace, monthly cap looks safe."
        eta_tone = "safe"

    return {
        "eta_copy": eta_copy,
        "eta_tone": eta_tone,
        "projected_days_delta": days_until_cap,
        "projected_finish_date": projected_cross_date.strftime("%Y-%m-%d"),
    }


def _apply_recurring_goal_resets(user_id, current_month):
    try:
        current_month_key = datetime.strptime(str(current_month or "").strip(), "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        current_month_key = date.today().strftime("%Y-%m")

    reset_count = 0
    query = {
        "user_id": user_id,
        "goal_type": GOAL_TYPE_SPENDING_CAP,
        "is_recurring": True,
        "recurrence": GOAL_RECURRENCE_MONTHLY,
        "status": {"$in": [GOAL_STATUS_ACTIVE, GOAL_STATUS_COMPLETED]},
    }

    for goal_doc in goals_collection.find(query):
        last_reset_month = str(goal_doc.get("last_reset_month", "")).strip()
        tracking_month = str(goal_doc.get("tracking_month", "")).strip()
        if last_reset_month == current_month_key or tracking_month == current_month_key:
            continue

        due_date_next = _goal_due_date_for_month(goal_doc.get("due_date"), current_month_key)
        update_fields = {
            "tracking_month": current_month_key,
            "last_reset_month": current_month_key,
            "status": GOAL_STATUS_ACTIVE,
            "completed_at": None,
            "updated_at": datetime.utcnow(),
        }
        if due_date_next:
            update_fields["due_date"] = due_date_next

        goals_collection.update_one(
            {"_id": goal_doc.get("_id"), "user_id": user_id},
            {"$set": update_fields},
        )
        reset_count += 1

    return reset_count


# VIVA: GOALS CALC - build goal progress, ETA hints, overdue counts, and recurring reset state.
def _build_goals_state(user_id, *, expenses, incomes, current_month=None):
    today_value = date.today()
    month_key = current_month or today_value.strftime("%Y-%m")
    recurring_resets = 0
    try:
        recurring_resets = _safe_int(_apply_recurring_goal_resets(user_id, month_key), 0)
    except PyMongoError:
        recurring_resets = 0

    total_income = _sum_amount(incomes)
    total_expense = _sum_amount(expenses)

    monthly_totals_by_category = {}
    monthly_income_totals = {}
    earliest_record_date = None

    for income in incomes:
        income_month = _month_key_from_record_date(income.get("date"))
        if income_month:
            monthly_income_totals[income_month] = _safe_amount(monthly_income_totals.get(income_month)) + _safe_amount(income.get("amount"))
        parsed_income_date = _parse_record_date(income.get("date"))
        if parsed_income_date and (earliest_record_date is None or parsed_income_date < earliest_record_date):
            earliest_record_date = parsed_income_date

    for expense in expenses:
        expense_month = _month_key_from_record_date(expense.get("date"))
        if not expense_month:
            continue
        amount_value = _safe_amount(expense.get("amount"))
        if amount_value <= 0:
            continue

        bucket = monthly_totals_by_category.setdefault(expense_month, {"__all__": 0.0})
        bucket["__all__"] = _safe_amount(bucket.get("__all__")) + amount_value

        category_key = str(expense.get("category", "")).strip().lower()
        if category_key:
            bucket[category_key] = _safe_amount(bucket.get(category_key)) + amount_value
        parsed_expense_date = _parse_record_date(expense.get("date"))
        if parsed_expense_date and (earliest_record_date is None or parsed_expense_date < earliest_record_date):
            earliest_record_date = parsed_expense_date

    try:
        goal_docs = list(goals_collection.find({"user_id": user_id}).sort("created_at", -1))
    except PyMongoError:
        goal_docs = []

    active_goals = []
    completed_goals = []
    archived_goals = []
    due_soon_count = 0
    overdue_count = 0
    completed_today_titles = []

    for goal_doc in goal_docs:
        goal_status = _normalize_goal_status(goal_doc.get("status"))
        due_context = _goal_due_context(goal_doc.get("due_date"), today_value=today_value)
        progress = _goal_current_progress(
            goal_doc,
            monthly_totals_by_category=monthly_totals_by_category,
            total_income=total_income,
            total_expense=total_expense,
            current_month=month_key,
        )
        goal_meta = _goal_type_meta(progress.get("goal_type"))
        eta_context = _goal_eta_insight(
            goal_doc,
            progress,
            today_value=today_value,
            current_month=month_key,
            monthly_totals_by_category=monthly_totals_by_category,
            monthly_income_totals=monthly_income_totals,
            record_start_date=earliest_record_date,
        )

        created_at = goal_doc.get("created_at")
        completed_at = goal_doc.get("completed_at")

        if isinstance(created_at, datetime):
            created_sort_value = created_at.timestamp()
        elif isinstance(created_at, date):
            created_sort_value = datetime.combine(created_at, datetime.min.time()).timestamp()
        else:
            created_sort_value = 0.0

        if isinstance(completed_at, datetime):
            completed_sort_value = completed_at.timestamp()
        elif isinstance(completed_at, date):
            completed_sort_value = datetime.combine(completed_at, datetime.min.time()).timestamp()
        else:
            completed_sort_value = 0.0

        goal_item = {
            "id": str(goal_doc.get("_id")),
            "title": str(goal_doc.get("title", "")).strip() or "Goal",
            "status": goal_status,
            "type_label": goal_meta.get("label", "Goal"),
            "type_icon": goal_meta.get("icon", "fa-solid fa-bullseye"),
            "goal_type": progress.get("goal_type"),
            "target_amount": progress.get("target_amount", 0.0),
            "current_value": progress.get("current_value", 0.0),
            "remaining_value": progress.get("remaining_value", 0.0),
            "progress_percent": progress.get("progress_percent", 0.0),
            "is_over_limit": bool(progress.get("is_over_limit")),
            "is_recurring": bool(progress.get("is_recurring", False)),
            "recurrence": progress.get("recurrence", ""),
            "recurrence_label": "Monthly reset" if progress.get("recurrence") == GOAL_RECURRENCE_MONTHLY else "",
            "category_label": progress.get("category_label", ""),
            "tracking_month": progress.get("tracking_month", month_key),
            "tracking_month_label": progress.get("tracking_month_label", _month_label(month_key)),
            "progress_title": progress.get("progress_title", ""),
            "detail_copy": progress.get("detail_copy", ""),
            "eta_copy": eta_context.get("eta_copy", ""),
            "eta_tone": eta_context.get("eta_tone", "neutral"),
            "projected_finish_date": eta_context.get("projected_finish_date", ""),
            "days_left": due_context.get("days_left"),
            "is_due_soon": bool(due_context.get("is_due_soon")),
            "is_overdue": bool(due_context.get("is_overdue")),
            "due_label": due_context.get("due_label", "No deadline"),
            "due_date": due_context.get("due_date", ""),
            "due_date_display": due_context.get("due_date_display", "-"),
            "created_at_display": _pretty_date(created_at),
            "completed_at_display": _pretty_date(completed_at),
            "created_sort_value": created_sort_value,
            "completed_sort_value": completed_sort_value,
        }

        if goal_status == GOAL_STATUS_ACTIVE:
            if goal_item["is_overdue"]:
                overdue_count += 1
            elif goal_item["is_due_soon"]:
                due_soon_count += 1
            active_goals.append(goal_item)
        elif goal_status == GOAL_STATUS_COMPLETED:
            completed_goals.append(goal_item)
            completed_date = _parse_record_date(completed_at)
            if completed_date == today_value:
                completed_today_titles.append(goal_item["title"])
        else:
            archived_goals.append(goal_item)

    active_goals.sort(
        key=lambda item: (
            0 if item.get("is_overdue") else (1 if item.get("is_due_soon") else 2),
            item.get("days_left") if item.get("days_left") is not None else 999999,
            -_safe_amount(item.get("created_sort_value"), 0.0),
        )
    )
    completed_goals.sort(key=lambda item: -_safe_amount(item.get("completed_sort_value"), 0.0))
    archived_goals.sort(key=lambda item: -_safe_amount(item.get("created_sort_value"), 0.0))

    return {
        "active": active_goals,
        "completed": completed_goals,
        "archived": archived_goals,
        "active_count": len(active_goals),
        "completed_count": len(completed_goals),
        "archived_count": len(archived_goals),
        "total_count": len(goal_docs),
        "due_soon_count": due_soon_count,
        "overdue_count": overdue_count,
        "completed_today_count": len(completed_today_titles),
        "completed_today_titles": completed_today_titles[:3],
        "recurring_resets": recurring_resets,
        "next_focus_goal": active_goals[0] if active_goals else None,
    }


def _set_goal_ui_event(event_type, message, toast_type="info"):
    session["goal_ui_event"] = {
        "type": str(event_type or "").strip().lower(),
        "message": str(message or "").strip(),
        "toast_type": str(toast_type or "info").strip().lower(),
    }


def _normalize_notification_id(value):
    clean_value = str(value or "").strip()
    if not clean_value:
        abort(400, description="Notification id is required")
    if len(clean_value) > 120:
        abort(400, description="Notification id is too long")
    if any(ch in clean_value for ch in ("/", "\\", "\x00")):
        abort(400, description="Invalid notification id")
    return clean_value


def _sync_dashboard_notifications(user_id, notifications):
    if not notifications:
        return []

    utc_now = datetime.utcnow()
    normalized_notifications = []
    notification_ids = []

    for item in notifications:
        notification_id = _normalize_notification_id(item.get("id"))
        normalized = {
            "id": notification_id,
            "group": str(item.get("group", "")).strip() or "alerts",
            "title": str(item.get("title", "")).strip() or "Notification",
            "message": str(item.get("message", "")).strip(),
            "time": str(item.get("time", "")).strip() or "Recent",
            "url": str(item.get("url", "")).strip() or url_for("dashboard"),
        }
        normalized_notifications.append(normalized)
        notification_ids.append(notification_id)

        notifications_collection.update_one(
            {"user_id": user_id, "notification_id": notification_id},
            {
                "$set": {
                    "group": normalized["group"],
                    "title": normalized["title"],
                    "message": normalized["message"],
                    "time_label": normalized["time"],
                    "target_url": normalized["url"],
                    "updated_at": utc_now,
                },
                "$setOnInsert": {
                    "is_read": False,
                    "created_at": utc_now,
                },
            },
            upsert=True,
        )

    stored_docs = notifications_collection.find(
        {
            "user_id": user_id,
            "notification_id": {"$in": notification_ids},
        },
        {"notification_id": 1, "is_read": 1},
    )
    read_map = {
        str(doc.get("notification_id")): bool(doc.get("is_read", False))
        for doc in stored_docs
    }

    synced_notifications = []
    for item in normalized_notifications:
        item_copy = dict(item)
        item_copy["is_read"] = read_map.get(item["id"], False)
        synced_notifications.append(item_copy)

    return synced_notifications


def _get_monthly_budget(month_key, user_id=None):
    target_user_id = user_id or _current_user_id()
    budget_doc = budgets_collection.find_one({"user_id": target_user_id, "month": month_key})
    if not budget_doc:
        return 0.0
    return _safe_amount(budget_doc.get("limit"))


def _get_monthly_expense_total(expenses, month_key):
    return sum(
        _safe_amount(item.get("amount"))
        for item in expenses
        if str(item.get("date", "")).startswith(month_key)
    )


def _ensure_expense_category(category_name):
    clean_name = str(category_name or "").strip()
    if not clean_name:
        return
    user_id = _current_user_id()
    existing_names = [
        str(doc.get("name", "")).strip().lower()
        for doc in categories_collection.find({"user_id": user_id}, {"name": 1})
    ]
    if clean_name.lower() not in existing_names:
        categories_collection.insert_one({"user_id": user_id, "name": clean_name})


def _assign_legacy_records_to_user(user_id):
    legacy_filter = {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]}
    collection.update_many(legacy_filter, {"$set": {"user_id": user_id}})
    incomes_collection.update_many(legacy_filter, {"$set": {"user_id": user_id}})
    categories_collection.update_many(legacy_filter, {"$set": {"user_id": user_id}})
    budgets_collection.update_many(legacy_filter, {"$set": {"user_id": user_id}})


def _backfill_expense_search_fields():
    missing_filter = {
        "$or": [
            {"merchant_search": {"$exists": False}},
            {"category_search": {"$exists": False}},
            {"amount_value": {"$exists": False}},
        ]
    }
    try:
        cursor = collection.find(
            missing_filter,
            {"_id": 1, "amount": 1, "category": 1, "description": 1},
        )
        for expense_doc in cursor:
            search_payload = _expense_search_fields(
                expense_doc.get("amount"),
                expense_doc.get("category"),
                expense_doc.get("description"),
            )
            collection.update_one({"_id": expense_doc["_id"]}, {"$set": search_payload})
    except PyMongoError:
        return


_backfill_expense_search_fields()


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, FAVICON_FILENAME, mimetype="image/x-icon")


# VIVA: AUTH ROUTE - login verifies the stored password hash and creates the session.
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    errors = {}
    next_url = request.args.get("next", "").strip()
    form_email = ""

    if request.method == "POST":
        form_email = request.form.get("email", "").strip()
        email = _normalize_email(form_email)
        password = request.form.get("password", "")
        next_url = request.form.get("next", "").strip()

        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."

        if not errors:
            user = users_collection.find_one({"email": email})
            # VIVA: SECURITY - compare the entered password against the saved hash, not plain text.
            if not user or not check_password_hash(user.get("password_hash", ""), password):
                error = "Invalid email or password."
            else:
                session.clear()
                session["user_id"] = str(user["_id"])
                session["post_login_splash"] = True
                flash(f"Welcome back, {user.get('name', 'there')}.", "success")
                if _is_safe_next_url(next_url):
                    return redirect(next_url)
                return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error=error,
        errors=errors,
        next_url=next_url,
        form_email=form_email,
    )


# VIVA: AUTH ROUTE - registration stores password as a hash, never as plain text.
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
    errors = {}
    form_data = {"name": "", "email": ""}

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw_email = request.form.get("email", "").strip()
        email = _normalize_email(raw_email)
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        form_data["name"] = name
        form_data["email"] = raw_email

        if not name:
            errors["name"] = "Name is required."
        if not email:
            errors["email"] = "Email is required."
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if not errors and users_collection.find_one({"email": email}):
            error = "An account with this email already exists."
        elif not errors:
            is_first_user = users_collection.count_documents({}) == 0
            # VIVA: SECURITY - only the hashed password is saved in MongoDB.
            result = users_collection.insert_one(
                {
                    "name": name,
                    "email": email,
                    "password_hash": generate_password_hash(password),
                    "created_at": datetime.utcnow(),
                    "avatar": {"preset": DEFAULT_AVATAR_PRESET},
                    "ui_preferences": {
                        "theme": DEFAULT_UI_THEME,
                        "language": DEFAULT_UI_LANGUAGE,
                    },
                    "gamification": _gamification_defaults(),
                }
            )
            if is_first_user:
                _assign_legacy_records_to_user(result.inserted_id)
            _seed_default_categories(result.inserted_id)
            session.clear()
            session["user_id"] = str(result.inserted_id)
            flash(f"Account created. Welcome, {name}.", "success")
            return redirect(url_for("dashboard"))

    return render_template("register.html", error=error, errors=errors, form_data=form_data)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/account')
def account_page():
    user_id = _current_user_id()
    user_doc = users_collection.find_one(
        {"_id": user_id},
        {
            "name": 1,
            "email": 1,
            "created_at": 1,
            "avatar.preset": 1,
            "avatar.image_path": 1,
            "ui_preferences.theme": 1,
            "ui_preferences.language": 1,
        },
    )
    if not user_doc:
        abort(404)

    avatar_preset = _avatar_preset_from_user(user_doc)
    appearance = _appearance_preferences_from_user(user_doc)
    return render_template(
        "account.html",
        account_user=user_doc,
        avatar_preset=avatar_preset,
        avatar_ui=_avatar_style(avatar_preset),
        avatar_image=_avatar_image_path_from_user(user_doc),
        avatar_presets=_avatar_preset_options(),
        appearance_preferences=appearance,
    )


@app.route('/account/profile', methods=['POST'])
def account_profile_update():
    user_id = _current_user_id()
    name = request.form.get("name", "").strip()
    raw_email = request.form.get("email", "").strip()
    email = _normalize_email(raw_email)
    avatar_preset = _normalize_avatar_preset(request.form.get("avatar_preset", ""))
    remove_avatar_image = str(request.form.get("remove_avatar_image", "")).strip().lower() in {
        "1",
        "true",
        "on",
        "yes",
    }
    cropped_avatar_data = str(request.form.get("profile_image_cropped_data", "") or "").strip()
    uploaded_avatar = request.files.get("profile_image")
    uploaded_filename = str(getattr(uploaded_avatar, "filename", "") or "").strip()

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("account_page"))
    if not email:
        flash("Email is required.", "error")
        return redirect(url_for("account_page"))

    existing_user = users_collection.find_one(
        {
            "email": email,
            "_id": {"$ne": user_id},
        },
        {"_id": 1},
    )
    if existing_user:
        flash("That email is already linked to another account.", "error")
        return redirect(url_for("account_page"))

    existing_doc = users_collection.find_one(
        {"_id": user_id},
        {"avatar.image_path": 1},
    )
    if not existing_doc:
        abort(404)

    current_image_path = _avatar_image_path_from_user(existing_doc)
    final_image_path = current_image_path
    if remove_avatar_image:
        final_image_path = None

    uploaded_image_path = None
    if cropped_avatar_data:
        try:
            uploaded_image_path = _save_avatar_image_data_url(cropped_avatar_data, user_id)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("account_page"))
        except Exception:
            flash("Could not process cropped profile image. Please retry.", "error")
            return redirect(url_for("account_page"))
        final_image_path = uploaded_image_path
    elif uploaded_filename:
        try:
            uploaded_image_path = _save_avatar_image_file(uploaded_avatar, user_id)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("account_page"))
        except Exception:
            flash("Could not upload profile image. Please retry.", "error")
            return redirect(url_for("account_page"))
        final_image_path = uploaded_image_path

    update_operation = {
        "$set": {
            "name": name,
            "email": email,
            "avatar.preset": avatar_preset,
            "updated_at": datetime.utcnow(),
        }
    }
    if final_image_path:
        update_operation["$set"]["avatar.image_path"] = final_image_path
    else:
        update_operation["$unset"] = {"avatar.image_path": ""}

    try:
        users_collection.update_one({"_id": user_id}, update_operation)
    except Exception:
        if uploaded_image_path:
            _delete_avatar_image_file(uploaded_image_path)
        flash("Could not update profile right now. Please retry.", "error")
        return redirect(url_for("account_page"))

    if current_image_path and current_image_path != final_image_path:
        _delete_avatar_image_file(current_image_path)

    flash("Profile updated successfully.", "success")
    return redirect(url_for("account_page"))


@app.route('/account/profile-image', methods=['POST'])
def account_profile_image_update():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    cropped_avatar_data = str(payload.get("cropped_data", "") or "").strip()
    if not cropped_avatar_data:
        return jsonify({"ok": False, "error": "Cropped image data is required."}), 400

    existing_doc = users_collection.find_one(
        {"_id": user_id},
        {"avatar.image_path": 1},
    )
    if not existing_doc:
        return jsonify({"ok": False, "error": "User not found."}), 404

    current_image_path = _avatar_image_path_from_user(existing_doc)

    try:
        uploaded_image_path = _save_avatar_image_data_url(cropped_avatar_data, user_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "Could not process cropped profile image."}), 500

    try:
        users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "avatar.image_path": uploaded_image_path,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
    except Exception:
        _delete_avatar_image_file(uploaded_image_path)
        return jsonify({"ok": False, "error": "Could not save profile image."}), 500

    if current_image_path and current_image_path != uploaded_image_path:
        _delete_avatar_image_file(current_image_path)

    return jsonify(
        {
            "ok": True,
            "image_path": uploaded_image_path,
            "image_url": url_for("static", filename=uploaded_image_path),
        }
    )


@app.route('/account/password', methods=['POST'])
def account_password_update():
    user_id = _current_user_id()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        flash("All password fields are required.", "error")
        return redirect(url_for("account_page"))
    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("account_page"))
    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("account_page"))
    if current_password == new_password:
        flash("New password must be different from current password.", "warning")
        return redirect(url_for("account_page"))

    user_doc = users_collection.find_one({"_id": user_id}, {"password_hash": 1})
    if not user_doc:
        abort(404)
    # VIVA: SECURITY - verify the current password hash before allowing a password change.
    if not check_password_hash(user_doc.get("password_hash", ""), current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("account_page"))

    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "password_hash": generate_password_hash(new_password),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    flash("Password updated successfully.", "success")
    return redirect(url_for("account_page"))


@app.route('/ui/preferences/sidebar', methods=['GET'])
def get_sidebar_preference():
    user_id = _current_user_id()
    user_doc = users_collection.find_one(
        {"_id": user_id},
        {"ui_preferences.sidebar_collapsed": 1},
    )
    ui_prefs = (user_doc or {}).get("ui_preferences", {})
    collapsed = bool(ui_prefs.get("sidebar_collapsed", False))
    return jsonify({"ok": True, "sidebar_collapsed": collapsed})


@app.route('/ui/preferences/sidebar', methods=['POST'])
def save_sidebar_preference():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    collapsed = _coerce_bool(payload.get("collapsed"), "collapsed")

    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "ui_preferences.sidebar_collapsed": collapsed,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return jsonify({"ok": True, "sidebar_collapsed": collapsed})


@app.route('/ui/preferences/appearance', methods=['POST'])
def save_appearance_preference():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}

    theme = _normalize_ui_theme(payload.get("theme"))
    language = _normalize_ui_language(payload.get("language"))

    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "ui_preferences.theme": theme,
                "ui_preferences.language": language,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return jsonify({"ok": True, "theme": theme, "language": language})


@app.route('/notifications/read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    user_id = _current_user_id()
    clean_notification_id = _normalize_notification_id(notification_id)

    utc_now = datetime.utcnow()
    result = notifications_collection.update_one(
        {
            "user_id": user_id,
            "notification_id": clean_notification_id,
        },
        {
            "$set": {
                "is_read": True,
                "read_at": utc_now,
                "updated_at": utc_now,
            }
        },
    )
    if result.matched_count == 0:
        return jsonify({"ok": False, "error": "Notification not found"}), 404

    return jsonify({"ok": True, "notification_id": clean_notification_id})


@app.route('/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("ids", [])

    clean_ids = []
    if isinstance(raw_ids, list):
        for value in raw_ids:
            clean_value = str(value or "").strip()
            if not clean_value:
                continue
            if len(clean_value) > 120:
                continue
            if any(ch in clean_value for ch in ("/", "\\", "\x00")):
                continue
            clean_ids.append(clean_value)

    query = {"user_id": user_id, "is_read": False}
    if clean_ids:
        query["notification_id"] = {"$in": clean_ids}

    utc_now = datetime.utcnow()
    result = notifications_collection.update_many(
        query,
        {
            "$set": {
                "is_read": True,
                "read_at": utc_now,
                "updated_at": utc_now,
            }
        },
    )

    return jsonify(
        {
            "ok": True,
            "updated": int(result.modified_count),
            "message": "All notifications marked as read.",
        }
    )


# VIVA: API - expense search endpoint with user isolation, filters, and pagination.
@app.route('/api/search/expenses')
def search_expenses():
    user_id = _current_user_id()
    raw_query = str(request.args.get("q", "")).strip()
    merchant_filter = str(request.args.get("merchant", "")).strip()
    category_filter = str(request.args.get("category", "")).strip()
    date_from = _parse_optional_date_arg(request.args.get("date_from", ""), "date_from")
    date_to = _parse_optional_date_arg(request.args.get("date_to", ""), "date_to")
    min_amount = _parse_optional_amount_arg(request.args.get("min_amount", ""), "min_amount")
    max_amount = _parse_optional_amount_arg(request.args.get("max_amount", ""), "max_amount")

    if date_from and date_to and date_from > date_to:
        abort(400, description="date_from cannot be later than date_to")
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        abort(400, description="min_amount cannot be greater than max_amount")

    try:
        limit = int(request.args.get("limit", 16))
    except (TypeError, ValueError):
        abort(400, description="Invalid limit")
    limit = min(max(limit, 1), 40)

    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        abort(400, description="Invalid page")
    page = max(page, 1)
    skip = (page - 1) * limit

    # VIVA: SECURITY - every search query is restricted to the logged-in user's records.
    filters = [{"user_id": user_id}]

    if category_filter:
        normalized_category = _normalize_search_text(category_filter)
        if normalized_category:
            filters.append({"category_search": normalized_category})

    if merchant_filter:
        normalized_merchant = _normalize_search_text(merchant_filter)
        if normalized_merchant:
            filters.append({"merchant_search": {"$regex": f"^{re.escape(normalized_merchant)}"}})

    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        filters.append({"date": date_query})

    if min_amount is not None or max_amount is not None:
        amount_query = {}
        if min_amount is not None:
            amount_query["$gte"] = min_amount
        if max_amount is not None:
            amount_query["$lte"] = max_amount
        filters.append({"amount_value": amount_query})

    if raw_query:
        query_filters = []
        normalized_query = _normalize_search_text(raw_query)
        if normalized_query:
            escaped_query = re.escape(normalized_query)
            query_filters.extend(
                [
                    {"merchant_search": {"$regex": f"^{escaped_query}"}},
                    {"category_search": {"$regex": f"^{escaped_query}"}},
                ]
            )

        parsed_query_date = _parse_flexible_date(raw_query)
        if parsed_query_date:
            query_filters.append({"date": parsed_query_date})

        compact_query = raw_query.replace(",", "")
        try:
            query_amount = float(compact_query)
            if query_amount >= 0:
                query_filters.append(
                    {
                        "amount_value": {
                            "$gte": max(0.0, query_amount - 0.01),
                            "$lte": query_amount + 0.01,
                        }
                    }
                )
        except (TypeError, ValueError):
            pass

        if query_filters:
            filters.append({"$or": query_filters})

    mongo_query = {"$and": filters} if len(filters) > 1 else filters[0]

    try:
        total_count = int(collection.count_documents(mongo_query))
        result_docs = list(
            collection.find(
                mongo_query,
                {"amount": 1, "amount_value": 1, "category": 1, "description": 1, "date": 1},
            ).sort("date", -1).skip(skip).limit(limit)
        )
    except PyMongoError:
        return jsonify({"ok": False, "error": "Search request failed."}), 500

    results = []
    for expense in result_docs:
        amount_value = _safe_amount(expense.get("amount_value", expense.get("amount")))
        month_key = _month_key_from_record_date(expense.get("date")) or "all"
        merchant_text = str(expense.get("description", "")).strip()
        category_text = str(expense.get("category", "")).strip() or "Uncategorized"

        results.append(
            {
                "id": str(expense.get("_id", "")),
                "title": merchant_text or category_text or "Transaction",
                "merchant": merchant_text,
                "category": category_text,
                "amount": amount_value,
                "amount_display": f"\u20b9{amount_value:,.2f}",
                "date": _format_display_date(expense.get("date")),
                "url": url_for("expenses_page", history_month=month_key),
            }
        )

    return jsonify(
        {
            "ok": True,
            "results": results,
            "count": len(results),
            "total_count": total_count,
            "pagination": {
                "page": page,
                "limit": limit,
                "has_more": (skip + len(results)) < total_count,
            },
            "filters": {
                "q": raw_query,
                "merchant": merchant_filter,
                "category": category_filter,
                "date_from": date_from,
                "date_to": date_to,
                "min_amount": min_amount,
                "max_amount": max_amount,
            },
        }
    )


# VIVA: API - backend endpoint for the rule-based Rupy finance chat.
@app.route('/api/rupy/chat', methods=['POST'])
def rupy_chat():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()

    if not question:
        return jsonify({"ok": False, "error": "Question is required."}), 400
    if len(question) > 280:
        question = question[:280]

    session_context = _normalize_rupy_chat_context(session.get(RUPY_CHAT_SESSION_CONTEXT_KEY))
    merged_context = dict(session_context)
    if isinstance(payload.get("context"), dict):
        client_context = _normalize_rupy_chat_context(payload.get("context"))
        has_client_signal = bool(
            client_context.get("last_category")
            or client_context.get("turn_count", 0) > 0
            or client_context.get("last_intent") != "default"
            or client_context.get("last_timeframe") != "unknown"
        )
        if has_client_signal:
            merged_context = _normalize_rupy_chat_context(
                {
                    "last_intent": client_context.get("last_intent", merged_context.get("last_intent")),
                    "last_timeframe": client_context.get("last_timeframe", merged_context.get("last_timeframe")),
                    "last_category": client_context.get("last_category", merged_context.get("last_category")),
                    "turn_count": max(
                        _safe_int(client_context.get("turn_count"), 0),
                        _safe_int(merged_context.get("turn_count"), 0),
                    ),
                }
            )

    try:
        snapshot = _build_rupy_chat_snapshot(user_id)
        reply = _build_rupy_chat_reply(question, snapshot, context=merged_context)
    except PyMongoError:
        return jsonify({"ok": False, "error": "Could not process Rupy chat request."}), 500

    context_update = _derive_rupy_chat_context(reply, snapshot=snapshot, previous_context=merged_context)
    session[RUPY_CHAT_SESSION_CONTEXT_KEY] = context_update
    session.modified = True

    return jsonify(
        {
            "ok": True,
            "question": question,
            "answer": str(reply.get("answer", "")).strip(),
            "intent": str(reply.get("intent", "default")).strip(),
            "state": str(reply.get("state", "thinking")).strip(),
            "event_type": str(reply.get("event_type", "tip")).strip(),
            "quick_replies": reply.get("quick_replies", RUPY_CHAT_DEFAULT_QUICK_REPLIES),
            "context_update": context_update,
        }
    )


# VIVA: DASHBOARD PAGE CALC - combines totals, budget, forecast, anomalies, goals, and gamification.
# Dashboard
@app.route('/')
def dashboard():
    user_id = _current_user_id()
    scope = _get_scope("this_month")
    current_month = date.today().strftime("%Y-%m")
    recent_month = _get_month_filter("recent_month", current_month)
    expenses = list(collection.find({"user_id": user_id}).sort("date", -1))
    _normalize_history(expenses)
    _normalize_display_dates(expenses)
    incomes = list(
        incomes_collection.find({"user_id": user_id}, {"amount": 1, "date": 1})
    )
    categories = _get_categories()

    current_month_label = _month_label(current_month)
    expense_totals_by_month = _build_monthly_expense_map(expenses)
    income_totals_by_month = _build_monthly_expense_map(incomes)
    this_month_expense = _safe_amount(expense_totals_by_month.get(current_month))
    this_month_income = _safe_amount(income_totals_by_month.get(current_month))

    all_time_expense = _sum_amount(expenses)
    all_time_income = _sum_amount(incomes)
    all_time_remaining = all_time_income - all_time_expense
    this_month_remaining = this_month_income - this_month_expense

    if scope == "all_time":
        total_expense = all_time_expense
        total_income = all_time_income
    else:
        total_expense = this_month_expense
        total_income = this_month_income

    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    anomaly_preferences = _get_anomaly_preferences(user_id)
    # VIVA: DASHBOARD CALC - these helpers generate the main budget and risk numbers used by the cards.
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )

    remaining_balance = total_income - total_expense
    monthly_base_budget = _safe_amount(budget_snapshot.get("base_budget"))
    monthly_carry_in = _safe_amount(budget_snapshot.get("carry_in"))
    monthly_budget = _safe_amount(budget_snapshot.get("effective_budget"))
    monthly_expense = _safe_amount(budget_snapshot.get("spent"))
    monthly_remaining = _safe_amount(budget_snapshot.get("remaining"))
    next_month_carry = _safe_amount(budget_snapshot.get("carry_out"))
    monthly_records = sum(
        1
        for item in expenses
        if _month_key_from_record_date(item.get("date")) == current_month
    )
    month_budget_doc = _get_month_budget_doc(user_id, current_month, allowed_categories=categories)
    category_budget_limits = month_budget_doc.get("category_limits", {})
    monthly_category_totals = _month_category_totals(expenses, current_month)
    category_budget_status = _build_category_budget_status(
        monthly_category_totals,
        category_budget_limits,
    )
    monthly_forecast = _build_monthly_forecast(
        current_month,
        monthly_expense,
        monthly_budget,
    )
    cut_suggestions = _build_cut_suggestions(
        monthly_category_totals,
        category_budget_limits,
        monthly_budget=monthly_budget,
        monthly_spent=monthly_expense,
        forecast_over_by=_safe_amount(monthly_forecast.get("forecast_over_by")),
    )
    goals_overview = _build_goals_state(
        user_id,
        expenses=expenses,
        incomes=incomes,
        current_month=current_month,
    )
    if goals_overview.get("recurring_resets", 0) > 0 and not session.get("goal_ui_event"):
        _set_goal_ui_event(
            "goal_recurring_reset",
            f"Recurring goals reset for {current_month_label}.",
            "info",
        )

    if monthly_budget > 0:
        monthly_spent_percent = (monthly_expense / monthly_budget) * 100
    else:
        monthly_spent_percent = 100.0 if monthly_expense > 0 else 0.0
    monthly_spent_percent_display = min(monthly_spent_percent, 100.0)

    if monthly_budget <= 0 and monthly_expense > 0:
        budget_status_text = "No budget set"
        budget_status_type = "negative"
    elif monthly_remaining < 0:
        budget_status_text = f"Overspent by \u20b9 {abs(monthly_remaining):,.2f}"
        budget_status_type = "negative"
    elif monthly_expense == 0:
        budget_status_text = "No spending yet"
        budget_status_type = "positive"
    else:
        budget_status_text = "Within budget"
        budget_status_type = "positive"

    # Daily expense chart datasets (7D / 30D / 3M).
    today = date.today()
    daily_rollup = {}
    for expense in expenses:
        day_key = str(expense.get("date", "")).strip()
        if not day_key:
            continue

        day_bucket = daily_rollup.setdefault(
            day_key,
            {
                "total": 0.0,
                "count": 0,
                "categories": {},
            },
        )

        amount_value = _safe_amount(expense.get("amount"))
        day_bucket["total"] += amount_value
        day_bucket["count"] += 1

        category_name = str(expense.get("category", "")).strip() or "Other"
        day_bucket["categories"][category_name] = (
            _safe_amount(day_bucket["categories"].get(category_name)) + amount_value
        )

    def _build_daily_chart_series(days_window):
        date_keys = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days_window - 1, -1, -1)
        ]
        totals = []
        txn_counts = []
        top_categories = []
        category_breakdown = []
        category_totals = {}

        for day_key in date_keys:
            day_data = daily_rollup.get(day_key, {})
            totals.append(_safe_amount(day_data.get("total")))
            txn_counts.append(int(day_data.get("count", 0) or 0))

            day_categories = day_data.get("categories", {})
            normalized_day_categories = {}
            for cat_name, cat_amount in day_categories.items():
                safe_name = str(cat_name or "").strip() or "Other"
                safe_amount = _safe_amount(cat_amount)
                if safe_amount <= 0:
                    continue
                normalized_day_categories[safe_name] = safe_amount
                category_totals[safe_name] = _safe_amount(category_totals.get(safe_name)) + safe_amount

            category_breakdown.append(normalized_day_categories)

            if not normalized_day_categories:
                top_categories.append("No spend")
                continue
            top_categories.append(
                max(normalized_day_categories.items(), key=lambda item: _safe_amount(item[1]))[0]
            )

        return {
            "dates": date_keys,
            "totals": totals,
            "txn_counts": txn_counts,
            "top_categories": top_categories,
            "category_breakdown": category_breakdown,
            "category_totals": category_totals,
        }

    expense_chart_series = {
        "7d": _build_daily_chart_series(7),
        "30d": _build_daily_chart_series(30),
        "3m": _build_daily_chart_series(90),
    }

    # Legacy values retained for compatibility.
    last7days = [_format_display_date(day_value) for day_value in expense_chart_series["7d"]["dates"]]
    daily_totals = expense_chart_series["7d"]["totals"]

    recent_expense_records = _filter_records_by_month(expenses, recent_month)
    recent_expense_groups = _group_records_by_month(recent_expense_records)
    recent_month_options = _build_month_options(expenses)

    # Build contextual dashboard notifications.
    previous_month_key = _shift_month_key(current_month, -1)
    previous_month_label = _month_label(previous_month_key)
    previous_month_expense = _safe_amount(expense_totals_by_month.get(previous_month_key))
    if previous_month_expense > 0:
        spending_change_percent = ((this_month_expense - previous_month_expense) / previous_month_expense) * 100
    else:
        spending_change_percent = 100.0 if this_month_expense > 0 else 0.0

    anomaly_summary = _analyze_spending_anomalies(
        expenses,
        current_month,
        threshold_percent=anomaly_preferences.get("threshold_percent", 40.0),
        min_amount_delta=anomaly_preferences.get("min_delta", 100.0),
        baseline_months_count=anomaly_preferences.get("baseline_months", 3),
    )
    dashboard_notifications = []
    notification_counts = {"alerts": 0, "insights": 0, "transactions": 0}

    def _add_dashboard_notification(notification_id, group, title, message, time_label, target_url):
        dashboard_notifications.append(
            {
                "id": notification_id,
                "group": group,
                "title": title,
                "message": message,
                "time": time_label,
                "url": target_url,
            }
        )
        if group in notification_counts:
            notification_counts[group] += 1

    if monthly_budget > 0:
        budget_usage_percent = (monthly_expense / monthly_budget) * 100
        if budget_usage_percent >= 90:
            _add_dashboard_notification(
                f"budget-90-{current_month}",
                "alerts",
                f"You've used {budget_usage_percent:.0f}% of your budget.",
                f"Budget left for {current_month_label}: \u20b9{max(monthly_remaining, 0):,.2f}",
                "Today",
                url_for("expenses_page", history_month=current_month),
            )
        elif budget_usage_percent >= 75:
            _add_dashboard_notification(
                f"budget-75-{current_month}",
                "alerts",
                f"Budget usage reached {budget_usage_percent:.0f}%.",
                f"Track spending to stay within \u20b9{monthly_budget:,.2f} this month.",
                "Today",
                url_for("expenses_page", history_month=current_month),
            )
    elif monthly_expense > 0:
        _add_dashboard_notification(
            f"budget-missing-{current_month}",
            "alerts",
            "No monthly budget set yet.",
            "Set your budget to enable proactive limit alerts.",
            "Today",
            url_for("settings_page"),
        )

    for item in category_budget_status[:6]:
        category_limit = _safe_amount(item.get("limit"))
        if category_limit <= 0:
            continue

        category_name = str(item.get("category", "")).strip() or "Category"
        tone = str(item.get("tone", "")).strip()
        usage_percent = _safe_amount(item.get("usage_percent"))
        remaining_amount = _safe_amount(item.get("remaining"))

        if tone == "over":
            _add_dashboard_notification(
                f"cat-limit-over-{current_month}-{_slug_key(category_name)}",
                "alerts",
                f"{category_name} crossed its category budget.",
                f"Overspent by \u20b9{abs(remaining_amount):,.2f} (usage {usage_percent:.0f}%).",
                "Today",
                url_for("expenses_page", history_month=current_month),
            )
        elif tone == "warning":
            _add_dashboard_notification(
                f"cat-limit-warn-{current_month}-{_slug_key(category_name)}",
                "alerts",
                f"{category_name} is near category budget.",
                f"Usage reached {usage_percent:.0f}% for this month.",
                "Today",
                url_for("expenses_page", history_month=current_month),
            )

    forecast_over_by = _safe_amount(monthly_forecast.get("forecast_over_by"))
    forecast_projected_total = _safe_amount(monthly_forecast.get("projected_total"))
    if monthly_budget > 0 and forecast_over_by > 0:
        _add_dashboard_notification(
            f"forecast-over-{current_month}",
            "alerts",
            "Forecast indicates month-end overspend.",
            (
                f"Projected spend: \u20b9{forecast_projected_total:,.2f} "
                f"vs budget \u20b9{monthly_budget:,.2f}."
            ),
            "Forecast",
            url_for("reports_page"),
        )
    elif monthly_budget > 0 and _safe_amount(monthly_forecast.get("forecast_buffer")) > 0:
        _add_dashboard_notification(
            f"forecast-safe-{current_month}",
            "insights",
            "Forecast says you are on track.",
            (
                f"Projected month-end spend: \u20b9{forecast_projected_total:,.2f} "
                f"within the budget."
            ),
            "Forecast",
            url_for("reports_page"),
        )

    if anomaly_summary.get("overall"):
        overall_anomaly = anomaly_summary["overall"]
        _add_dashboard_notification(
            f"anomaly-overall-{current_month}",
            "alerts",
            f"Spending is {overall_anomaly.get('percent', 0.0):.0f}% above usual.",
            (
                f"{current_month_label}: \u20b9{overall_anomaly.get('current_total', 0.0):,.2f} "
                f"vs avg \u20b9{overall_anomaly.get('baseline_average', 0.0):,.2f}"
            ),
            "This month",
            url_for("reports_page"),
        )

    for item in anomaly_summary.get("categories", [])[:2]:
        category_name = str(item.get("category", "")).strip() or "General"
        _add_dashboard_notification(
            f"anomaly-cat-{current_month}-{_slug_key(category_name)}",
            "alerts",
            f"{category_name}: spending is {item.get('percent', 0.0):.0f}% above usual.",
            (
                f"Current \u20b9{item.get('current_total', 0.0):,.2f} | "
                f"Avg \u20b9{item.get('baseline_average', 0.0):,.2f}"
            ),
            "This month",
            url_for("expenses_page", history_month=current_month),
        )

    if previous_month_expense > 0 and abs(spending_change_percent) >= 10:
        trend_word = "increased" if spending_change_percent > 0 else "decreased"
        _add_dashboard_notification(
            f"spend-trend-{current_month}",
            "insights",
            f"Spending {trend_word} {abs(spending_change_percent):.0f}% vs last month.",
            f"{current_month_label} vs {previous_month_label}",
            "This month",
            url_for("reports_page"),
        )

    if monthly_budget > 0 and 0 < monthly_remaining <= (monthly_budget * 0.1):
        _add_dashboard_notification(
            f"goal-almost-{current_month}",
            "insights",
            "Goal almost reached: monthly budget target.",
            f"Only \u20b9{monthly_remaining:,.2f} left before hitting your limit.",
            "Today",
            url_for("dashboard", scope="this_month", recent_month=current_month),
        )

    if cut_suggestions:
        top_cut = cut_suggestions[0]
        _add_dashboard_notification(
            f"cut-tip-{current_month}-{_slug_key(top_cut.get('category'))}",
            "insights",
            f"Cut suggestion: {top_cut.get('category')} this week.",
            (
                f"Try reducing around \u20b9{_safe_amount(top_cut.get('suggested_cut_week')):,.2f} "
                f"({top_cut.get('reason', 'spending optimization')})."
            ),
            "Weekly action",
            url_for("expenses_page", history_month=current_month),
        )

    for expense in expenses[:6]:
        category = str(expense.get("category", "")).strip() or "General"
        description = str(expense.get("description", "")).strip()
        title = f"New transaction: {description or category}"
        amount_value = _safe_amount(expense.get("amount"))
        month_key = _month_key_from_record_date(expense.get("date")) or "all"
        _add_dashboard_notification(
            f"txn-{expense.get('_id')}",
            "transactions",
            title,
            f"\u20b9{amount_value:,.2f} | {category}",
            str(expense.get("history", "")).strip() or str(expense.get("date_display", "")).strip() or "Recent",
            url_for("expenses_page", history_month=month_key),
        )

    if goals_overview.get("overdue_count", 0) > 0:
        _add_dashboard_notification(
            f"goals-overdue-{current_month}-{goals_overview['overdue_count']}",
            "alerts",
            f"{goals_overview['overdue_count']} goal deadline missed.",
            "Open Goals to recover overdue targets and reset plan.",
            "Today",
            url_for("goals_page"),
        )
    if goals_overview.get("due_soon_count", 0) > 0:
        _add_dashboard_notification(
            f"goals-due-soon-{current_month}-{goals_overview['due_soon_count']}",
            "alerts",
            f"{goals_overview['due_soon_count']} goals are near deadline.",
            "Rupy suggests a quick review before they become overdue.",
            "This week",
            url_for("goals_page"),
        )
    if goals_overview.get("completed_today_count", 0) > 0:
        first_goal = (goals_overview.get("completed_today_titles") or ["Goal"])[0]
        _add_dashboard_notification(
            f"goals-complete-{current_month}-{goals_overview['completed_today_count']}",
            "insights",
            f"Goal completed: {first_goal}",
            "Great momentum. Keep stacking wins in your goals hub.",
            "Today",
            url_for("goals_page"),
        )
    if goals_overview.get("recurring_resets", 0) > 0:
        _add_dashboard_notification(
            f"goals-recurring-reset-{current_month}-{goals_overview['recurring_resets']}",
            "insights",
            "Recurring goals reset for the new month.",
            f"{goals_overview['recurring_resets']} recurring goals are now active.",
            "Monthly reset",
            url_for("goals_page"),
        )

    dashboard_notifications = _sync_dashboard_notifications(user_id, dashboard_notifications)
    notification_unread_count = sum(
        1
        for item in dashboard_notifications
        if not bool(item.get("is_read"))
    )
    dashboard_user_doc = users_collection.find_one({"_id": user_id}, {"gamification": 1}) or {}
    gamification = _build_gamification_dashboard_state(
        user_id,
        dashboard_user_doc,
        expenses=expenses,
        categories=categories,
        current_month=current_month,
        monthly_budget=monthly_budget,
        monthly_expense=monthly_expense,
        monthly_records=monthly_records,
    )
    weekly_spending_summary = _build_weekly_spending_summary(expenses)
    rupy_coach = _build_rupy_coach_payload(
        expenses=expenses,
        current_month=current_month,
        current_month_label=current_month_label,
        monthly_budget=monthly_budget,
        monthly_expense=monthly_expense,
        monthly_remaining=monthly_remaining,
        monthly_spent_percent=monthly_spent_percent,
        monthly_forecast=monthly_forecast,
        goals_overview=goals_overview,
        gamification=gamification,
        weekly_summary=weekly_spending_summary,
    )
    rupy_meme_expressions = _build_rupy_meme_expressions()

    return render_template(
        'dashboard.html',
        expenses=expenses,
        total_expense=total_expense,
        total_income=total_income,
        remaining_balance=remaining_balance,
        all_time_expense=all_time_expense,
        all_time_income=all_time_income,
        all_time_remaining=all_time_remaining,
        this_month_expense=this_month_expense,
        this_month_income=this_month_income,
        this_month_remaining=this_month_remaining,
        monthly_records=monthly_records,
        monthly_budget=monthly_budget,
        monthly_expense=monthly_expense,
        monthly_remaining=monthly_remaining,
        monthly_spent_percent=monthly_spent_percent,
        monthly_spent_percent_display=monthly_spent_percent_display,
        budget_status_text=budget_status_text,
        budget_status_type=budget_status_type,
        monthly_base_budget=monthly_base_budget,
        monthly_carry_in=monthly_carry_in,
        next_month_carry=next_month_carry,
        budget_rollover_enabled=bool(budget_snapshot.get("rollover_enabled")),
        carry_forward_deficit=bool(budget_snapshot.get("carry_forward_deficit")),
        scope=scope,
        current_month=current_month,
        current_month_label=current_month_label,
        last7days=last7days,
        daily_totals=daily_totals,
        expense_chart_series=expense_chart_series,
        chart_category_ui_map=CATEGORY_UI_MAP,
        default_category_ui=DEFAULT_CATEGORY_UI,
        recent_month=recent_month,
        recent_month_options=recent_month_options,
        recent_expense_groups=recent_expense_groups,
        search_categories=categories,
        spending_anomaly=anomaly_summary,
        anomaly_preferences=anomaly_preferences,
        category_budget_limits=category_budget_limits,
        category_budget_status=category_budget_status,
        monthly_category_totals=monthly_category_totals,
        monthly_forecast=monthly_forecast,
        cut_suggestions=cut_suggestions,
        gamification=gamification,
        goals_overview=goals_overview,
        dashboard_notifications=dashboard_notifications,
        notification_counts=notification_counts,
        notification_unread_count=notification_unread_count,
        weekly_spending_summary=weekly_spending_summary,
        rupy_coach=rupy_coach,
        rupy_meme_expressions=rupy_meme_expressions,
    )


# VIVA: GAMIFICATION PAGE CALC - renders level, streak, XP rules, and achievements.
@app.route('/gamification')
def gamification_page():
    user_id = _current_user_id()
    current_month = date.today().strftime("%Y-%m")
    current_month_label = _month_label(current_month)

    expenses = list(collection.find({"user_id": user_id}).sort("date", -1))
    categories = _get_categories()
    expense_totals_by_month = _build_monthly_expense_map(expenses)
    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )

    monthly_budget = _safe_amount(budget_snapshot.get("effective_budget"))
    monthly_expense = _safe_amount(budget_snapshot.get("spent"))
    monthly_remaining = _safe_amount(budget_snapshot.get("remaining"))
    monthly_records = sum(
        1
        for item in expenses
        if _month_key_from_record_date(item.get("date")) == current_month
    )

    user_doc = users_collection.find_one({"_id": user_id}, {"gamification": 1}) or {}
    gamification = _build_gamification_dashboard_state(
        user_id,
        user_doc,
        expenses=expenses,
        categories=categories,
        current_month=current_month,
        monthly_budget=monthly_budget,
        monthly_expense=monthly_expense,
        monthly_records=monthly_records,
    )

    unlocked_achievements = [item for item in gamification.get("achievements", []) if item.get("unlocked")]
    locked_achievements = [item for item in gamification.get("achievements", []) if not item.get("unlocked")]

    xp_action_labels = {
        "add_expense": "Add expense",
        "set_budget": "Set budget",
        "stay_under_budget": "Stay under budget",
        "savings_goal_reached": "Savings goal reached",
        "streak_milestone": "7-day streak milestone",
        "daily_challenge": "Daily challenge completion",
    }
    xp_rules = [
        {
            "action": xp_action_labels.get(action_key, action_key.replace("_", " ").title()),
            "xp": _safe_int(xp_value),
        }
        for action_key, xp_value in GAMIFICATION_XP_ACTIONS.items()
    ]

    return render_template(
        "gamification.html",
        gamification=gamification,
        unlocked_achievements=unlocked_achievements,
        locked_achievements=locked_achievements,
        xp_rules=xp_rules,
        current_month=current_month,
        current_month_label=current_month_label,
        monthly_budget=monthly_budget,
        monthly_expense=monthly_expense,
        monthly_remaining=monthly_remaining,
        monthly_records=monthly_records,
    )


# VIVA: GOALS PAGE CALC - renders goal progress, due-soon warnings, and the next focus goal.
@app.route('/goals')
def goals_page():
    user_id = _current_user_id()
    current_month = date.today().strftime("%Y-%m")
    current_month_label = _month_label(current_month)
    today_key = date.today().strftime("%Y-%m-%d")

    expenses = list(collection.find({"user_id": user_id}, {"amount": 1, "category": 1, "date": 1}))
    incomes = list(incomes_collection.find({"user_id": user_id}, {"amount": 1, "date": 1}))
    categories = _get_categories()
    goals_overview = _build_goals_state(
        user_id,
        expenses=expenses,
        incomes=incomes,
        current_month=current_month,
    )
    if goals_overview.get("recurring_resets", 0) > 0 and not session.get("goal_ui_event"):
        _set_goal_ui_event(
            "goal_recurring_reset",
            f"Recurring goals reset for {current_month_label}.",
            "info",
        )
    goal_templates = _goal_templates_for_form(categories, current_month)
    next_focus_goal = goals_overview.get("next_focus_goal") or {}
    goal_signal = {
        "goal_warning_count": _safe_int(goals_overview.get("due_soon_count"), 0) + _safe_int(goals_overview.get("overdue_count"), 0),
        "goal_overdue_count": _safe_int(goals_overview.get("overdue_count"), 0),
        "goal_completed_today": _safe_int(goals_overview.get("completed_today_count"), 0),
        "goal_focus_title": str(next_focus_goal.get("title", "")).strip(),
        "goal_eta": str(next_focus_goal.get("eta_copy", "")).strip(),
        "goal_recurring_resets": _safe_int(goals_overview.get("recurring_resets"), 0),
    }

    return render_template(
        "goals.html",
        goals_overview=goals_overview,
        goal_templates=goal_templates,
        goal_signal=goal_signal,
        categories=categories,
        current_month=current_month,
        current_month_label=current_month_label,
        today=today_key,
    )


@app.route('/goals/add', methods=['POST'])
def add_goal():
    user_id = _current_user_id()
    template_key = str(request.form.get("template_key", "")).strip()
    template_map = {
        str(item.get("key", "")).strip(): item
        for item in GOAL_TEMPLATES
        if str(item.get("key", "")).strip()
    }
    selected_template = template_map.get(template_key)

    title = str(request.form.get("title", "")).strip()
    if not title and selected_template:
        title = str(selected_template.get("title", "")).strip()
    if not title:
        abort(400, description="Goal title is required")
    if len(title) > 90:
        abort(400, description="Goal title is too long")

    goal_type_raw = str(request.form.get("goal_type", "")).strip().lower()
    if not goal_type_raw and selected_template:
        goal_type_raw = str(selected_template.get("goal_type", "")).strip().lower()
    if goal_type_raw not in GOAL_TYPE_META:
        abort(400, description="Invalid goal type")
    goal_type = goal_type_raw

    target_raw = str(request.form.get("target_amount", "")).strip()
    if not target_raw and selected_template:
        target_raw = str(selected_template.get("target_amount", "")).strip()
    try:
        target_amount = float(target_raw)
    except (TypeError, ValueError):
        abort(400, description="Invalid target amount")
    if target_amount <= 0:
        abort(400, description="Target amount must be greater than zero")

    due_date_raw = str(request.form.get("due_date", "")).strip()
    if not due_date_raw and selected_template:
        due_days = max(0, _safe_int(selected_template.get("due_days"), 0))
        if due_days > 0:
            due_date_raw = (date.today() + timedelta(days=due_days)).strftime("%Y-%m-%d")
    due_date = ""
    if due_date_raw:
        try:
            due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            abort(400, description="Invalid due date")

    tracking_month = ""
    category_name = ""
    recurring_requested = str(request.form.get("is_recurring", "")).strip().lower() in {"1", "true", "on", "yes"}
    if not recurring_requested and selected_template:
        recurring_requested = _normalize_goal_recurrence(selected_template.get("recurrence")) == GOAL_RECURRENCE_MONTHLY

    if goal_type == GOAL_TYPE_SPENDING_CAP:
        tracking_month_raw = str(request.form.get("tracking_month", "")).strip() or date.today().strftime("%Y-%m")
        try:
            tracking_month = datetime.strptime(tracking_month_raw, "%Y-%m").strftime("%Y-%m")
        except ValueError:
            abort(400, description="Invalid tracking month")

        category_name = str(request.form.get("category", "")).strip()
        if not category_name and selected_template:
            category_name = str(selected_template.get("category", "")).strip()
        if category_name:
            allowed_categories = set(_get_categories())
            if category_name not in allowed_categories:
                abort(400, description="Invalid category selected")
    else:
        recurring_requested = False

    now_utc = datetime.utcnow()
    recurrence = GOAL_RECURRENCE_MONTHLY if recurring_requested else ""
    last_reset_month = tracking_month if recurrence == GOAL_RECURRENCE_MONTHLY else ""
    goals_collection.insert_one(
        {
            "user_id": user_id,
            "title": title,
            "goal_type": goal_type,
            "status": GOAL_STATUS_ACTIVE,
            "target_amount": target_amount,
            "category": category_name,
            "tracking_month": tracking_month,
            "is_recurring": bool(recurring_requested),
            "recurrence": recurrence,
            "last_reset_month": last_reset_month,
            "template_key": template_key,
            "due_date": due_date,
            "created_at": now_utc,
            "updated_at": now_utc,
            "completed_at": None,
        }
    )
    xp_result = _award_action_xp(user_id, "set_budget")

    flash(f"Goal created: {title}", "success")
    if xp_result.get("xp_awarded", 0) > 0:
        flash(f"Gamification: +{xp_result['xp_awarded']} XP earned.", "info")
    _set_goal_ui_event(
        "goal_created",
        f"Goal created: {title}. Keep tracking daily to stay on target.",
        "success",
    )
    return redirect(url_for("goals_page"))


@app.route('/goals/<goal_id>/status', methods=['POST'])
def update_goal_status(goal_id):
    user_id = _current_user_id()
    parsed_goal_id = _parse_object_id(goal_id)
    goal_doc = goals_collection.find_one({"_id": parsed_goal_id, "user_id": user_id})
    if not goal_doc:
        abort(404)
    previous_status = _normalize_goal_status(goal_doc.get("status"))
    goal_title = str(goal_doc.get("title", "")).strip() or "Goal"

    action = str(request.form.get("action", "")).strip().lower()
    action_map = {
        "complete": GOAL_STATUS_COMPLETED,
        "archive": GOAL_STATUS_ARCHIVED,
        "activate": GOAL_STATUS_ACTIVE,
    }
    next_status = action_map.get(action)
    if not next_status:
        abort(400, description="Invalid goal action")

    updates = {
        "status": next_status,
        "updated_at": datetime.utcnow(),
    }
    xp_result = {"xp_awarded": 0}
    if next_status == GOAL_STATUS_COMPLETED:
        updates["completed_at"] = datetime.utcnow()
        if previous_status != GOAL_STATUS_COMPLETED:
            xp_result = _award_action_xp(user_id, "savings_goal_reached")
    elif next_status == GOAL_STATUS_ACTIVE:
        updates["completed_at"] = None

    goals_collection.update_one(
        {"_id": parsed_goal_id, "user_id": user_id},
        {"$set": updates},
    )

    status_message = {
        GOAL_STATUS_COMPLETED: "Goal marked as completed.",
        GOAL_STATUS_ARCHIVED: "Goal archived.",
        GOAL_STATUS_ACTIVE: "Goal moved back to active.",
    }
    flash(status_message.get(next_status, "Goal updated."), "success")
    if next_status == GOAL_STATUS_COMPLETED and previous_status != GOAL_STATUS_COMPLETED:
        _set_goal_ui_event(
            "goal_completed",
            f"Goal completed: {goal_title}. Celebration mode on.",
            "success",
        )
    elif next_status == GOAL_STATUS_ARCHIVED:
        _set_goal_ui_event(
            "goal_archived",
            f"Goal archived: {goal_title}. You can restore it anytime.",
            "info",
        )
    elif next_status == GOAL_STATUS_ACTIVE:
        _set_goal_ui_event(
            "goal_reactivated",
            f"Goal reactivated: {goal_title}. Rupy is tracking it again.",
            "info",
        )
    if xp_result.get("xp_awarded", 0) > 0:
        if xp_result.get("level_up"):
            flash(
                f"Gamification: +{xp_result['xp_awarded']} XP. Level {xp_result['new_level']} unlocked.",
                "success",
            )
        else:
            flash(f"Gamification: +{xp_result['xp_awarded']} XP earned.", "info")
    return _redirect_back(default_endpoint="goals_page")


@app.route('/goals/<goal_id>/delete', methods=['POST'])
def delete_goal(goal_id):
    user_id = _current_user_id()
    parsed_goal_id = _parse_object_id(goal_id)
    goal_doc = goals_collection.find_one({"_id": parsed_goal_id, "user_id": user_id})
    if not goal_doc:
        abort(404)
    goal_title = str(goal_doc.get("title", "")).strip() or "Goal"

    goals_collection.delete_one({"_id": parsed_goal_id, "user_id": user_id})
    flash(f"Goal deleted: {goal_title}", "warning")
    _set_goal_ui_event(
        "goal_deleted",
        f"Goal removed: {goal_title}. Create a new one when you are ready.",
        "warning",
    )
    return _redirect_back(default_endpoint="goals_page")


# VIVA: EXPENSES PAGE CALC - combines totals, budget status, forecast, and cut suggestions for the month.
# Expenses Page
@app.route('/expenses')
def expenses_page():
    user_id = _current_user_id()
    scope = _get_scope("this_month")
    current_month = date.today().strftime("%Y-%m")
    history_month = _get_month_filter("history_month", current_month)
    expenses = list(collection.find({"user_id": user_id}).sort("date", -1))
    _normalize_history(expenses)
    _normalize_display_dates(expenses)
    incomes = list(incomes_collection.find({"user_id": user_id}).sort("date", -1))
    _normalize_history(incomes)
    _normalize_display_dates(incomes)
    current_month_label = _month_label(current_month)
    all_time_expense = _sum_amount(expenses)
    all_time_income = _sum_amount(incomes)
    all_time_remaining = all_time_income - all_time_expense

    this_month_expense = _sum_amount_for_month(expenses, current_month)
    this_month_income = _sum_amount_for_month(incomes, current_month)
    this_month_remaining = this_month_income - this_month_expense

    if scope == "all_time":
        total_expense = all_time_expense
        total_income = all_time_income
    else:
        total_expense = this_month_expense
        total_income = this_month_income

    remaining_balance = total_income - total_expense
    categories = _get_categories()
    expense_totals_by_month = _build_monthly_expense_map(expenses)
    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    # VIVA: EXPENSES CALC - page totals reuse the same budget snapshot and forecast helpers.
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )
    month_budget_doc = _get_month_budget_doc(user_id, current_month, allowed_categories=categories)
    category_budget_limits = month_budget_doc.get("category_limits", {})
    monthly_category_totals = _month_category_totals(expenses, current_month)
    category_budget_status = _build_category_budget_status(
        monthly_category_totals,
        category_budget_limits,
    )
    monthly_forecast = _build_monthly_forecast(
        current_month,
        this_month_expense,
        _safe_amount(budget_snapshot.get("effective_budget")),
    )
    cut_suggestions = _build_cut_suggestions(
        monthly_category_totals,
        category_budget_limits,
        monthly_budget=_safe_amount(budget_snapshot.get("effective_budget")),
        monthly_spent=this_month_expense,
        forecast_over_by=_safe_amount(monthly_forecast.get("forecast_over_by")),
    )
    category_delete_map = {}
    for category_doc in categories_collection.find({"user_id": user_id}, {"name": 1}).sort("name", 1):
        category_name = str(category_doc.get("name", "")).strip()
        if not category_name or category_name in category_delete_map:
            continue
        category_delete_map[category_name] = str(category_doc.get("_id"))
    today_str = date.today().strftime("%Y-%m-%d")
    history_month_options = _build_month_options(expenses, incomes)
    filtered_expenses = _filter_records_by_month(expenses, history_month)
    filtered_incomes = _filter_records_by_month(incomes, history_month)
    expense_history_groups = _group_records_by_month(filtered_expenses)
    income_history_groups = _group_records_by_month(filtered_incomes)
    return render_template(
        'expenses.html',
        expenses=expenses,
        incomes=incomes,
        total_expense=total_expense,
        total_income=total_income,
        remaining_balance=remaining_balance,
        all_time_expense=all_time_expense,
        all_time_income=all_time_income,
        all_time_remaining=all_time_remaining,
        this_month_expense=this_month_expense,
        this_month_income=this_month_income,
        this_month_remaining=this_month_remaining,
        scope=scope,
        current_month=current_month,
        current_month_label=current_month_label,
        categories=categories,
        category_delete_map=category_delete_map,
        today=today_str,
        history_month=history_month,
        history_month_options=history_month_options,
        expense_history_groups=expense_history_groups,
        income_history_groups=income_history_groups,
        month_budget=_safe_amount(budget_snapshot.get("effective_budget")),
        month_budget_remaining=_safe_amount(budget_snapshot.get("remaining")),
        category_budget_limits=category_budget_limits,
        category_budget_status=category_budget_status,
        monthly_category_totals=monthly_category_totals,
        monthly_forecast=monthly_forecast,
        cut_suggestions=cut_suggestions,
    )

# Add Expense
@app.route('/add', methods=['POST'])
def add():
    user_id = _current_user_id()
    selected_category = request.form.get("category", "").strip()
    if not selected_category:
        abort(400, description="Category is required")
    _ensure_expense_category(selected_category)
    amount = _parse_amount_from_form()
    description = request.form.get('description', '').strip()

    expense = {
        "user_id": user_id,
        "amount": amount,
        "category": selected_category,
        "description": description,
        "date": _parse_date_from_form('date'),
        "history": _current_history_time(),
    }
    expense.update(_expense_search_fields(amount, selected_category, description))
    collection.insert_one(expense)
    xp_result = _award_action_xp(user_id, "add_expense")
    flash(
        f"Expense added: {_format_inr_message(expense.get('amount'))} | {selected_category}",
        "success",
    )
    if xp_result.get("xp_awarded", 0) > 0:
        if xp_result.get("level_up"):
            flash(
                f"Gamification: +{xp_result['xp_awarded']} XP. Level {xp_result['new_level']} unlocked.",
                "success",
            )
        else:
            flash(f"Gamification: +{xp_result['xp_awarded']} XP earned.", "info")
    expense_month = _month_key_from_record_date(expense.get("date"))
    for alert_message in _real_time_budget_alerts(user_id, expense_month, selected_category):
        flash(alert_message, "warning")
    return _redirect_back()

# Edit Expense
@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    user_id = _current_user_id()
    expense_id = _parse_object_id(id)
    expense = collection.find_one({"_id": expense_id, "user_id": user_id})
    if not expense:
        abort(404)

    if request.method == "POST":
        selected_category = request.form.get("category", "").strip()
        if not selected_category:
            abort(400, description="Category is required")
        _ensure_expense_category(selected_category)
        amount = _parse_amount_from_form()
        description = request.form.get('description', '').strip()

        updated_expense = {
            "amount": amount,
            "category": selected_category,
            "description": description,
            "date": _parse_date_from_form('date'),
            "history": _current_history_time(),
        }
        updated_expense.update(_expense_search_fields(amount, selected_category, description))
        collection.update_one(
            {"_id": expense_id, "user_id": user_id},
            {"$set": updated_expense},
        )
        flash(
            f"Expense updated: {_format_inr_message(updated_expense.get('amount'))} | {selected_category}",
            "success",
        )
        expense_month = _month_key_from_record_date(updated_expense.get("date"))
        for alert_message in _real_time_budget_alerts(user_id, expense_month, selected_category):
            flash(alert_message, "warning")
        return _redirect_back()

    categories = _get_categories()
    expense_category = str(expense.get("category", "")).strip()
    if expense_category and expense_category not in categories:
        categories.append(expense_category)

    return render_template('edit_expense.html', expense=expense, categories=sorted(categories))

# Delete Expense
@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    user_id = _current_user_id()
    expense_id = _parse_object_id(id)
    expense = collection.find_one({"_id": expense_id, "user_id": user_id})
    if not expense:
        abort(404)

    collection.delete_one({"_id": expense_id, "user_id": user_id})
    category_name = str(expense.get("category", "")).strip() or "Expense"
    flash(f"Deleted: {category_name} expense.", "warning")
    return _redirect_back()


# Add Income
@app.route('/add-income', methods=['POST'])
def add_income():
    user_id = _current_user_id()
    amount = _parse_amount_from_form()
    source = request.form.get("source", "").strip()
    income_date = _parse_date_from_form("date")

    incomes_collection.insert_one(
        {
            "user_id": user_id,
            "amount": amount,
            "source": source if source else "General",
            "date": income_date,
            "history": _current_history_time(),
        }
    )
    source_label = source if source else "General"
    flash(f"Income added: {_format_inr_message(amount)} | {source_label}", "success")
    return _redirect_back(default_endpoint="expenses_page")


# Edit Income
@app.route('/edit-income/<id>', methods=['GET', 'POST'])
def edit_income(id):
    user_id = _current_user_id()
    income_id = _parse_object_id(id)
    income = incomes_collection.find_one({"_id": income_id, "user_id": user_id})
    if not income:
        abort(404)

    if request.method == "POST":
        updated_income = {
            "amount": _parse_amount_from_form(),
            "source": request.form.get("source", "").strip() or "General",
            "date": _parse_date_from_form("date"),
            "history": _current_history_time(),
        }
        incomes_collection.update_one(
            {"_id": income_id, "user_id": user_id},
            {"$set": updated_income},
        )
        flash(
            f"Income updated: {_format_inr_message(updated_income.get('amount'))} | {updated_income.get('source')}",
            "success",
        )
        return _redirect_back(default_endpoint="expenses_page")

    return render_template('edit_income.html', income=income)


# Delete Income
@app.route('/delete-income/<id>', methods=['POST'])
def delete_income(id):
    user_id = _current_user_id()
    income_id = _parse_object_id(id)
    income = incomes_collection.find_one({"_id": income_id, "user_id": user_id})
    if not income:
        abort(404)

    incomes_collection.delete_one({"_id": income_id, "user_id": user_id})
    source_label = str(income.get("source", "")).strip() or "Income"
    flash(f"Deleted: {source_label} income entry.", "warning")
    return _redirect_back(default_endpoint="expenses_page")


# Add Expense Category
@app.route('/settings/categories/add', methods=['POST'])
def add_category():
    user_id = _current_user_id()
    name = request.form.get("name", "").strip()
    if not name:
        abort(400, description="Category name is required")

    existing_names = [
        str(doc.get("name", "")).strip().lower()
        for doc in categories_collection.find({"user_id": user_id}, {"name": 1})
    ]
    if name.lower() not in existing_names:
        categories_collection.insert_one({"user_id": user_id, "name": name})
        flash(f"Category added: {name}", "success")
    else:
        flash(f"Category already exists: {name}", "info")

    return _redirect_back(default_endpoint="settings_page")


# Delete Expense Category
@app.route('/settings/categories/delete/<id>', methods=['POST'])
def delete_category(id):
    user_id = _current_user_id()
    category_id = _parse_object_id(id)
    category_doc = categories_collection.find_one({"_id": category_id, "user_id": user_id})
    if not category_doc:
        abort(404)

    category_name = str(category_doc.get("name", "")).strip()
    if not category_name:
        abort(400, description="Invalid category")

    replacement_category = "Other"
    if category_name.lower() == "other":
        replacement_category = "General"

    _ensure_expense_category(replacement_category)
    collection.update_many(
        {"user_id": user_id, "category": category_name},
        {
            "$set": {
                "category": replacement_category,
                "category_search": _normalize_search_text(replacement_category),
            }
        },
    )

    categories_collection.delete_one({"_id": category_id, "user_id": user_id})

    if categories_collection.count_documents({"user_id": user_id}) == 0:
        _seed_default_categories(user_id)

    flash(
        f"Category deleted: {category_name}. Existing records moved to {replacement_category}.",
        "warning",
    )
    return _redirect_back(default_endpoint="settings_page")


# VIVA: SETTINGS ACTION - save monthly budget, rollover rules, category limits, and anomaly settings.
# Save Monthly Budget
@app.route('/settings/budget', methods=['POST'])
def save_monthly_budget():
    user_id = _current_user_id()
    month_key = _parse_month_from_form("month")
    amount = _parse_amount_from_form()
    rollover_enabled = request.form.get("rollover_enabled") == "on"
    carry_forward_deficit = request.form.get("carry_forward_deficit") == "on"
    anomaly_threshold_percent = _parse_float_from_form(
        "anomaly_threshold_percent",
        minimum=10.0,
        maximum=300.0,
    )
    anomaly_min_delta = _parse_float_from_form(
        "anomaly_min_delta",
        minimum=0.0,
        maximum=1000000.0,
    )
    anomaly_baseline_months = _parse_int_from_form(
        "anomaly_baseline_months",
        minimum=2,
        maximum=12,
    )
    category_docs = list(
        categories_collection.find({"user_id": user_id}, {"_id": 1, "name": 1})
    )
    category_name_by_id = {}
    for doc in category_docs:
        key = str(doc.get("_id", "")).strip()
        value = str(doc.get("name", "")).strip()
        if not key or not value:
            continue
        category_name_by_id[key] = value

    category_limits = {}
    for form_key, form_value in request.form.items():
        if not str(form_key).startswith("category_limit__"):
            continue
        category_id = str(form_key).split("category_limit__", 1)[1].strip()
        if not category_id:
            continue
        category_name = category_name_by_id.get(category_id)
        if not category_name:
            continue

        raw_limit = str(form_value or "").strip()
        if not raw_limit:
            continue
        try:
            limit_value = float(raw_limit)
        except (TypeError, ValueError):
            abort(400, description=f"Invalid category budget for {category_name}")
        if limit_value < 0:
            abort(400, description=f"Category budget cannot be negative ({category_name})")
        if limit_value > 0:
            category_limits[category_name] = limit_value

    budgets_collection.update_one(
        {"user_id": user_id, "month": month_key},
        {
            "$set": {
                "user_id": user_id,
                "month": month_key,
                "limit": amount,
                "category_limits": category_limits,
            }
        },
        upsert=True,
    )
    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "ui_preferences.budget_rollover_enabled": rollover_enabled,
                "ui_preferences.carry_forward_deficit": carry_forward_deficit,
                "ui_preferences.anomaly_threshold_percent": anomaly_threshold_percent,
                "ui_preferences.anomaly_min_delta": anomaly_min_delta,
                "ui_preferences.anomaly_baseline_months": anomaly_baseline_months,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    rollover_status = "ON" if rollover_enabled else "OFF"
    deficit_status = "ON" if carry_forward_deficit else "OFF"
    flash(
        (
            f"Budget saved for {_month_label(month_key)}: {_format_inr_message(amount)} "
            f"| Rollover: {rollover_status} | Deficit carry: {deficit_status} "
            f"| Anomaly: {anomaly_threshold_percent:.0f}% / \u20b9{anomaly_min_delta:,.0f} (last {anomaly_baseline_months} months) "
            f"| Category limits: {len(category_limits)}"
        ),
        "success",
    )
    xp_result = _award_action_xp(user_id, "set_budget")
    if xp_result.get("xp_awarded", 0) > 0:
        if xp_result.get("level_up"):
            flash(
                f"Gamification: +{xp_result['xp_awarded']} XP. Level {xp_result['new_level']} unlocked.",
                "success",
            )
        else:
            flash(f"Gamification: +{xp_result['xp_awarded']} XP earned.", "info")
    return _redirect_back(default_endpoint="settings_page")

# VIVA: REPORTS PAGE CALC - aggregates monthly category totals and compares them with budget and forecast.
# Reports Page with Chart
@app.route('/reports')
def reports_page():
    user_id = _current_user_id()
    current_month = date.today().strftime("%Y-%m")
    current_month_label = _month_label(current_month)
    available_categories = _get_categories()
    # VIVA: REPORTS CALC - Mongo aggregation groups current-month expenses by category for the chart.
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "date": {"$regex": f"^{current_month}"}
            }
        },
        {
            "$group": {
                "_id": "$category",
                "total": {
                    "$sum": {
                        "$convert": {
                            "input": "$amount",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            }
        },
        {
            "$sort": {"total": -1}
        }
    ]
    category_summary = list(collection.aggregate(pipeline))
    total_expense = sum(_safe_amount(e.get("total")) for e in category_summary)

    category_color_map = {
        "housing": "#2388e2",
        "rent": "#2388e2",
        "bills": "#1f6fc9",
        "food": "#ff9800",
        "transportation": "#7ac21f",
        "transport": "#7ac21f",
        "travel": "#7ac21f",
        "entertainment": "#9560db",
        "shopping": "#f35d6c",
        "other": "#7a93ad",
        "other categories": "#7a93ad",
        "general": "#7a93ad",
        "health": "#7a93ad",
        "education": "#1f6fc9",
    }
    fallback_colors = [
        "#2388e2",
        "#1f6fc9",
        "#ff9800",
        "#7ac21f",
        "#9560db",
        "#f35d6c",
        "#7a93ad",
        "#2388e2",
    ]

    category_rows = []
    for index, row in enumerate(category_summary):
        label = str(row.get("_id") or "Other").strip() or "Other"
        key = label.lower()
        color = category_color_map.get(key, fallback_colors[index % len(fallback_colors)])
        category_rows.append(
            {
                "label": label,
                "total": _safe_amount(row.get("total")),
                "color": color,
            }
        )

    categories = [row["label"] for row in category_rows]
    totals = [row["total"] for row in category_rows]
    chart_colors = [row["color"] for row in category_rows]

    expense_totals_by_month = _build_monthly_expense_map(
        collection.find({"user_id": user_id}, {"amount": 1, "date": 1})
    )
    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )
    month_budget = _safe_amount(budget_snapshot.get("effective_budget"))
    budget_remaining = _safe_amount(budget_snapshot.get("remaining"))
    month_budget_doc = _get_month_budget_doc(user_id, current_month, allowed_categories=available_categories)
    category_budget_limits = month_budget_doc.get("category_limits", {})
    monthly_category_totals = {
        str(item.get("label", "")).strip() or "Other": _safe_amount(item.get("total"))
        for item in category_rows
    }
    category_budget_status = _build_category_budget_status(
        monthly_category_totals,
        category_budget_limits,
    )
    monthly_forecast = _build_monthly_forecast(
        current_month,
        total_expense,
        month_budget,
    )
    cut_suggestions = _build_cut_suggestions(
        monthly_category_totals,
        category_budget_limits,
        monthly_budget=month_budget,
        monthly_spent=total_expense,
        forecast_over_by=_safe_amount(monthly_forecast.get("forecast_over_by")),
    )

    return render_template(
        'reports.html',
        category_summary=category_summary,
        category_rows=category_rows,
        total_expense=total_expense,
        categories=categories,
        totals=totals,
        chart_colors=chart_colors,
        current_month=current_month,
        current_month_label=current_month_label,
        month_budget=month_budget,
        budget_remaining=budget_remaining,
        monthly_base_budget=_safe_amount(budget_snapshot.get("base_budget")),
        monthly_carry_in=_safe_amount(budget_snapshot.get("carry_in")),
        budget_rollover_enabled=bool(budget_snapshot.get("rollover_enabled")),
        category_budget_limits=category_budget_limits,
        category_budget_status=category_budget_status,
        monthly_category_totals=monthly_category_totals,
        monthly_forecast=monthly_forecast,
        cut_suggestions=cut_suggestions,
    )

# VIVA: SETTINGS PAGE CALC - previews carry-forward, effective budget, category limits, and forecast.
# Settings Page
@app.route('/settings')
def settings_page():
    user_id = _current_user_id()
    categories = list(categories_collection.find({"user_id": user_id}).sort("name", 1))
    current_month = date.today().strftime("%Y-%m")
    expenses_for_budget = list(
        collection.find({"user_id": user_id}, {"amount": 1, "date": 1})
    )
    expense_totals_by_month = _build_monthly_expense_map(expenses_for_budget)
    budget_limits_map = _get_budget_limits_map(user_id)
    budget_preferences = _get_budget_preferences(user_id)
    anomaly_preferences = _get_anomaly_preferences(user_id)
    budget_snapshot = _compute_budget_snapshot(
        current_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )
    next_month = _shift_month_key(current_month, 1)
    next_month_snapshot = _compute_budget_snapshot(
        next_month,
        budget_limits_map,
        expense_totals_by_month,
        budget_preferences,
    )

    month_budget = _safe_amount(budget_limits_map.get(current_month))
    monthly_expense = _safe_amount(budget_snapshot.get("spent"))
    budget_remaining = _safe_amount(budget_snapshot.get("remaining"))
    effective_budget = _safe_amount(budget_snapshot.get("effective_budget"))
    carry_in = _safe_amount(budget_snapshot.get("carry_in"))
    next_month_carry = _safe_amount(budget_snapshot.get("carry_out"))
    next_month_base_budget = _safe_amount(budget_limits_map.get(next_month))
    next_month_effective_budget = _safe_amount(next_month_snapshot.get("effective_budget"))
    category_names = [str(item.get("name", "")).strip() for item in categories if str(item.get("name", "")).strip()]
    month_budget_doc = _get_month_budget_doc(user_id, current_month, allowed_categories=category_names)
    category_budget_limits = month_budget_doc.get("category_limits", {})
    category_limit_values = {}
    for item in categories:
        category_id = str(item.get("_id", "")).strip()
        category_name = str(item.get("name", "")).strip()
        if not category_id or not category_name:
            continue
        category_limit_values[category_id] = _safe_amount(category_budget_limits.get(category_name))
    monthly_category_totals = _month_category_totals(expenses_for_budget, current_month)
    category_budget_status = _build_category_budget_status(
        monthly_category_totals,
        category_budget_limits,
    )
    monthly_forecast = _build_monthly_forecast(
        current_month,
        monthly_expense,
        effective_budget,
    )
    cut_suggestions = _build_cut_suggestions(
        monthly_category_totals,
        category_budget_limits,
        monthly_budget=effective_budget,
        monthly_spent=monthly_expense,
        forecast_over_by=_safe_amount(monthly_forecast.get("forecast_over_by")),
    )

    return render_template(
        'settings.html',
        categories=categories,
        current_month=current_month,
        month_budget=month_budget,
        monthly_expense=monthly_expense,
        budget_remaining=budget_remaining,
        effective_budget=effective_budget,
        carry_in=carry_in,
        next_month=next_month,
        next_month_carry=next_month_carry,
        next_month_base_budget=next_month_base_budget,
        next_month_effective_budget=next_month_effective_budget,
        budget_rollover_enabled=bool(budget_snapshot.get("rollover_enabled")),
        carry_forward_deficit=bool(budget_snapshot.get("carry_forward_deficit")),
        anomaly_threshold_percent=anomaly_preferences.get("threshold_percent", 40.0),
        anomaly_min_delta=anomaly_preferences.get("min_delta", 100.0),
        anomaly_baseline_months=anomaly_preferences.get("baseline_months", 3),
        category_budget_limits=category_budget_limits,
        category_limit_values=category_limit_values,
        category_budget_status=category_budget_status,
        monthly_category_totals=monthly_category_totals,
        monthly_forecast=monthly_forecast,
        cut_suggestions=cut_suggestions,
    )

if __name__ == '__main__':
    app.run(debug=True)
