#!/usr/bin/env python3
"""
Health Care - a cross-platform (Windows / Linux / macOS) health reminder app.

* Misty-forest picture background (needs Pillow; falls back to a plain colour)
* Languages: English, Tamil (தமிழ்) and Japanese (日本語) - Settings > Language
* Tasks tab (one-off or daily) and a daily GK quiz; everything refreshes every 24 hours
* Reminds you to drink water, go for a walk, rest your eyes, stretch ...
* Sends real desktop notifications (with an in-app popup as fallback)
* Dynamic GUI: responsive card layout that reflows when you resize the window,
  live countdowns, live progress bars, light/dark theme, add/edit/delete
  reminders at runtime, quiet hours, daily goals.
* No third-party packages needed - only Python 3.8+ with Tkinter.

Run:  python3 health_care_app.py      (Windows: python health_care_app.py)
"""
import datetime as dt
import json
import os
import platform
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox

try:                                   # optional: background image needs Pillow
    from PIL import Image, ImageEnhance, ImageTk
except Exception:                      # app still works with a plain background
    Image = None


def resource(name):
    here = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    for d in (here, "/usr/share/healthcare"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def load_bg_image():
    path = resource("background.jpg")
    if Image is None or not path:
        return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def render_bg(src, W, H, dark):
    """Scale-to-cover + centre-crop the picture, then darken it so text stays readable."""
    sw, sh = src.size
    sc = max(W / sw, H / sh)
    nw, nh = int(sw * sc) + 1, int(sh * sc) + 1
    im = src.resize((nw, nh), getattr(Image, "Resampling", Image).LANCZOS)
    x, y = (nw - W) // 2, (nh - H) // 2
    im = im.crop((x, y, x + W, y + H))
    return ImageEnhance.Brightness(im).enhance(0.4 if dark else 0.55)

APP = "Health Care"
SYSTEM = platform.system()

LANGS = {"en": "English", "ta": "தமிழ்", "ja": "日本語"}
LANG_IDX = {"en": 0, "ta": 1, "ja": 2}


def detect_lang():
    """Pick the UI language from the OS (or HEALTHCARE_LANG=en|ta|ja)."""
    code = os.environ.get("HEALTHCARE_LANG", "").lower()
    if not code:
        if SYSTEM == "Windows":
            try:
                import ctypes
                pid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
                code = {0x11: "ja", 0x49: "ta"}.get(pid, "en")
            except Exception:
                code = "en"
        else:
            code = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
                    or os.environ.get("LANG") or "en").lower()
    for k in ("ja", "ta"):
        if code.startswith(k):
            return k
    return "en"


# key: (English, Tamil, Japanese)
TR = {
    "app": ("Health Care", "ஆரோக்கிய பராமரிப்பு", "ヘルスケア"),
    "settings": ("Settings", "அமைப்புகள்", "設定"),
    "dark": ("Dark", "இருண்ட", "ダーク"),
    "light": ("Light", "ஒளி", "ライト"),
    "add_rem": ("+ Reminder", "+ நினைவூட்டல்", "+ リマインダー"),
    "water": ("Water", "தண்ணீர்", "水分"),
    "walking": ("Walking", "நடைப்பயிற்சி", "ウォーキング"),
    "score": ("Today's score", "இன்றைய மதிப்பெண்", "今日のスコア"),
    "tasks": ("Tasks", "பணிகள்", "タスク"),
    "plus_glass": ("+1 glass", "+1 டம்ளர்", "+1杯"),
    "plus_min": ("+%d min", "+%d நிமிடம்", "+%d分"),
    "reminders": ("Reminders", "நினைவூட்டல்கள்", "リマインダー"),
    "tasks_tab": ("Tasks (%d)", "பணிகள் (%d)", "タスク (%d)"),
    "gk_tab": ("GK Quiz", "பொது அறிவு வினாடி வினா", "一般常識クイズ"),
    "on": ("On", "இயக்கு", "オン"),
    "done": ("Done", "முடிந்தது", "完了"),
    "snooze": ("Snooze 5m", "5 நிமி தள்ளு", "5分後に再通知"),
    "edit": ("Edit", "திருத்து", "編集"),
    "delete": ("Delete", "நீக்கு", "削除"),
    "del_q": ("Delete reminder '%s'?", "'%s' நினைவூட்டலை நீக்கவா?", "リマインダー「%s」を削除しますか？"),
    "edit_rem": ("Edit reminder", "நினைவூட்டலைத் திருத்து", "リマインダーを編集"),
    "new_rem": ("New reminder", "புதிய நினைவூட்டல்", "新しいリマインダー"),
    "name": ("Name", "பெயர்", "名前"),
    "message": ("Message", "செய்தி", "メッセージ"),
    "every": ("Every (minutes)", "ஒவ்வொரு (நிமிடங்கள்)", "間隔（分）"),
    "cancel": ("Cancel", "ரத்து", "キャンセル"),
    "save": ("Save", "சேமி", "保存"),
    "err_min": ("Minutes must be a number from 1 to 1440.",
                "நிமிடங்கள் 1 முதல் 1440 வரை உள்ள எண்ணாக இருக்க வேண்டும்.",
                "分は1〜1440の数字で入力してください。"),
    "err_name": ("Please enter a name.", "பெயரை உள்ளிடவும்.", "名前を入力してください。"),
    "water_goal": ("Water goal (glasses/day)", "தண்ணீர் இலக்கு (டம்ளர்/நாள்)", "水分の目標（杯/日）"),
    "walk_goal": ("Walk goal (minutes/day)", "நடை இலக்கு (நிமிடம்/நாள்)", "ウォーキング目標（分/日）"),
    "walk_log": ("Minutes logged per walk 'Done'",
                 "நடை 'முடிந்தது' க்கு பதிவாகும் நிமிடங்கள்",
                 "ウォーキング「完了」で記録する分数"),
    "q_start": ("Quiet hours start (HH:MM)", "அமைதி நேரம் தொடக்கம் (HH:MM)", "サイレント時間の開始 (HH:MM)"),
    "q_end": ("Quiet hours end (HH:MM)", "அமைதி நேரம் முடிவு (HH:MM)", "サイレント時間の終了 (HH:MM)"),
    "q_on": ("Enable quiet hours", "அமைதி நேரத்தை இயக்கு", "サイレント時間を有効にする"),
    "beep": ("Beep on reminder", "நினைவூட்டலில் ஒலி", "リマインダー時にビープ音"),
    "language": ("Language", "மொழி", "言語"),
    "err_vals": ("Please check the values (times as HH:MM).",
                 "மதிப்புகளைச் சரிபார்க்கவும் (நேரம் HH:MM வடிவில்).",
                 "値を確認してください（時刻は HH:MM 形式）。"),
    "sent": ("Reminder sent: %s", "நினைவூட்டல் அனுப்பப்பட்டது: %s", "リマインダーを送信しました：%s"),
    "glasses_fmt": ("%d / %d glasses", "%d / %d டம்ளர்", "%d / %d 杯"),
    "min_fmt": ("%d / %d min", "%d / %d நிமிடம்", "%d / %d 分"),
    "done_fmt": ("%d / %d done", "%d / %d முடிந்தன", "%d / %d 完了"),
    "paused": ("Paused", "இடைநிறுத்தம்", "一時停止"),
    "quiet_active": ("Quiet hours active", "அமைதி நேரம் செயலில் உள்ளது", "サイレント時間中"),
    "next_fmt": ("Next: %s in %s%s", "அடுத்தது: %s - %s%s", "次：%s（%s後）%s"),
    "no_active": ("No active reminders", "செயலில் உள்ள நினைவூட்டல்கள் இல்லை", "有効なリマインダーはありません"),
    "repeat": ("Repeat daily", "தினமும் மீண்டும்", "毎日繰り返す"),
    "add_task": ("Add task", "பணி சேர்", "タスクを追加"),
    "no_tasks": ("No tasks yet - add one above.", "இன்னும் பணிகள் இல்லை - மேலே சேர்க்கவும்.",
                 "タスクはまだありません。上から追加してください。"),
    "daily": ("daily", "தினசரி", "毎日"),
    "gk_title": ("Daily GK: %d / %d correct today - new questions every 24 hours",
                 "தினசரி பொது அறிவு: இன்று %d / %d சரி - ஒவ்வொரு 24 மணி நேரமும் புதிய கேள்விகள்",
                 "今日の一般常識：%d / %d 正解 - 24時間ごとに新しい問題"),
    "gk_done": ("All done - come back tomorrow for new questions!",
                "அனைத்தும் முடிந்தது - புதிய கேள்விகளுக்கு நாளை வாருங்கள்!",
                "完了です！新しい問題は明日また挑戦してください。"),
    "new_day": ("New day! Tasks and GK questions have been refreshed.",
                "புதிய நாள்! பணிகளும் பொது அறிவு கேள்விகளும் புதுப்பிக்கப்பட்டன.",
                "新しい一日です！タスクと一般常識クイズが更新されました。"),
    "r_water_name": ("Drink water", "தண்ணீர் குடிக்கவும்", "水を飲む"),
    "r_water_msg": ("Time to drink a glass of water.", "ஒரு டம்ளர் தண்ணீர் குடிக்க வேண்டிய நேரம்.", "コップ1杯の水を飲む時間です。"),
    "r_walk_name": ("Go for a walk", "நடைப்பயிற்சி செல்லுங்கள்", "散歩に行く"),
    "r_walk_msg": ("Stand up and take a short walk.", "எழுந்து சிறிது நடக்கவும்.", "立ち上がって少し歩きましょう。"),
    "r_eyes_name": ("Rest your eyes", "கண்களுக்கு ஓய்வு கொடுங்கள்", "目を休める"),
    "r_eyes_msg": ("Look at something 20 feet away for 20 seconds.",
                   "20 அடி தூரத்தில் உள்ள ஒன்றை 20 விநாடிகள் பாருங்கள்.",
                   "6メートル先を20秒間見つめましょう。"),
    "r_stretch_name": ("Stretch", "உடலை நீட்டுங்கள்", "ストレッチ"),
    "r_stretch_msg": ("Stretch your neck, shoulders and back.", "கழுத்து, தோள்கள், முதுகை நீட்டுங்கள்.", "首・肩・背中を伸ばしましょう。"),
}
BUILTIN = {"water", "walk", "eyes", "stretch"}

THEMES = {
    "light": dict(bg="#f3f5f9", card="#ffffff", fg="#1f2937", sub="#6b7280",
                  accent="#2563eb", trough="#e5e7eb", good="#16a34a",
                  btn="#e5e7eb", btnfg="#1f2937"),
    "dark": dict(bg="#111827", card="#1f2937", fg="#f3f4f6", sub="#9ca3af",
                 accent="#60a5fa", trough="#374151", good="#34d399",
                 btn="#374151", btnfg="#f3f4f6"),
}

DEFAULT_REMINDERS = [
    dict(id="water", name="Drink water", interval=45, enabled=True, kind="water",
         message="Time to drink a glass of water.", color="#0ea5e9"),
    dict(id="walk", name="Go for a walk", interval=90, enabled=True, kind="walk",
         message="Stand up and take a short walk.", color="#22c55e"),
    dict(id="eyes", name="Rest your eyes", interval=20, enabled=True, kind="",
         message="Look at something 20 feet away for 20 seconds.", color="#a855f7"),
    dict(id="stretch", name="Stretch", interval=60, enabled=False, kind="",
         message="Stretch your neck, shoulders and back.", color="#f97316"),
]
DEFAULT_SETTINGS = dict(theme="light", quiet_on=False, quiet_start="22:00",
                        quiet_end="07:00", water_goal=8, walk_goal=30,
                        walk_log=10, sound=True, lang=detect_lang())
COLORS = ["#0ea5e9", "#22c55e", "#a855f7", "#f97316", "#ef4444", "#eab308", "#14b8a6"]

# (question, [options], index of correct option) - 5 new ones every day
GK_BANK = [
    ("What is the capital of Australia?", ["Sydney", "Canberra", "Melbourne", "Perth"], 1),
    ("Which is the largest planet in our solar system?", ["Earth", "Saturn", "Jupiter", "Neptune"], 2),
    ("Who wrote the Indian national anthem?", ["Bankim Chandra Chatterjee", "Rabindranath Tagore", "Sarojini Naidu", "Muhammad Iqbal"], 1),
    ("What is the chemical symbol for gold?", ["Au", "Ag", "Gd", "Go"], 0),
    ("Which is the largest ocean?", ["Atlantic", "Indian", "Pacific", "Arctic"], 2),
    ("Who was the first Prime Minister of India?", ["Jawaharlal Nehru", "Mahatma Gandhi", "Sardar Patel", "Rajendra Prasad"], 0),
    ("What is the hardest natural substance?", ["Gold", "Iron", "Diamond", "Quartz"], 2),
    ("Which vitamin does the body make from sunlight?", ["Vitamin A", "Vitamin C", "Vitamin D", "Vitamin K"], 2),
    ("Which is the longest river flowing within India?", ["Yamuna", "Ganga", "Godavari", "Krishna"], 1),
    ("How many continents are there?", ["5", "6", "7", "8"], 2),
    ("Which is the fastest land animal?", ["Lion", "Cheetah", "Horse", "Leopard"], 1),
    ("In which city is the Taj Mahal?", ["Delhi", "Agra", "Jaipur", "Lucknow"], 1),
    ("Which gas do plants absorb for photosynthesis?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], 2),
    ("What is the currency of Japan?", ["Yuan", "Won", "Yen", "Ringgit"], 2),
    ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Mercury", "Jupiter"], 1),
    ("What is the normal human body temperature in Celsius?", ["35", "37", "39", "41"], 1),
    ("How many bones are in an adult human body?", ["186", "206", "226", "256"], 1),
    ("Who formulated the law of universal gravitation?", ["Isaac Newton", "Albert Einstein", "Galileo", "Nikola Tesla"], 0),
    ("What is the national animal of India?", ["Lion", "Tiger", "Elephant", "Leopard"], 1),
    ("Which is the largest hot desert in the world?", ["Gobi", "Sahara", "Thar", "Kalahari"], 1),
    ("What is the smallest prime number?", ["0", "1", "2", "3"], 2),
    ("What is H2O commonly known as?", ["Salt", "Water", "Hydrogen peroxide", "Ammonia"], 1),
    ("In which year was Mahatma Gandhi born?", ["1869", "1879", "1889", "1857"], 0),
    ("Which organ pumps blood around the body?", ["Liver", "Lungs", "Heart", "Kidney"], 2),
    ("What is the capital of Tamil Nadu?", ["Chennai", "Madurai", "Coimbatore", "Tiruchirappalli"], 0),
    ("Which gas is most abundant in Earth's atmosphere?", ["Oxygen", "Nitrogen", "Argon", "Carbon dioxide"], 1),
    ("When did the Constitution of India come into effect?", ["15 Aug 1947", "26 Jan 1950", "2 Oct 1950", "26 Nov 1949"], 1),
    ("Which is the highest mountain above sea level?", ["K2", "Mount Everest", "Kangchenjunga", "Lhotse"], 1),
    ("Which mineral is most important for strong bones?", ["Iron", "Calcium", "Sodium", "Potassium"], 1),
    ("What is the SI unit of frequency?", ["Hertz", "Newton", "Watt", "Pascal"], 0),
]


# --------------------------------------------------------------------------- #
# storage
# --------------------------------------------------------------------------- #
def data_file():
    if SYSTEM == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif SYSTEM == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    folder = os.path.join(base, "healthcare")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "data.json")


def today():
    return dt.date.today().isoformat()


# --------------------------------------------------------------------------- #
# notifications
# --------------------------------------------------------------------------- #
def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def native_notify(title, message):
    """Fire a desktop notification. Returns True if it was handed to the OS."""
    try:
        if SYSTEM == "Windows":
            ps = (
                "$ErrorActionPreference='Stop';"
                "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,"
                "ContentType=WindowsRuntime]|Out-Null;"
                "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                "$n=$x.GetElementsByTagName('text');"
                "$n.Item(0).AppendChild($x.CreateTextNode($env:HC_T))|Out-Null;"
                "$n.Item(1).AppendChild($x.CreateTextNode($env:HC_M))|Out-Null;"
                "$t=[Windows.UI.Notifications.ToastNotification]::new($x);"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'"
                ").Show($t)"
            )
            env = dict(os.environ, HC_T=title, HC_M=message)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                env=env, creationflags=0x08000000,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if SYSTEM == "Darwin":
            script = 'display notification "%s" with title "%s"' % (
                message.replace('"', "'"), title.replace('"', "'"))
            subprocess.Popen(["osascript", "-e", script])
            return True
        subprocess.Popen(["notify-send", "-a", APP, "-t", "10000", title, message],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# small custom progress bar
# --------------------------------------------------------------------------- #
class Bar(tk.Canvas):
    def __init__(self, master, trough, fill, height=8, **kw):
        super().__init__(master, height=height, highlightthickness=0, bd=0,
                         bg=master["bg"], **kw)
        self.trough, self.fill, self.frac = trough, fill, 0.0
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, frac, fill=None):
        self.frac = max(0.0, min(1.0, frac))
        if fill:
            self.fill = fill
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), int(self["height"])
        self.create_rectangle(0, 0, w, h, fill=self.trough, width=0)
        if self.frac > 0:
            self.create_rectangle(0, 0, w * self.frac, h, fill=self.fill, width=0)


# --------------------------------------------------------------------------- #
# the app
# --------------------------------------------------------------------------- #
class HealthApp:
    def __init__(self, root):
        self.root = root
        root.title(APP)
        root.geometry("900x640")
        root.minsize(420, 420)
        self.path = data_file()
        self.load()
        self.cards = {}          # id -> dict(frame, time, bar, status)
        self.cols = 0
        self.last_day = today()
        self.bg_src = load_bg_image()
        self._last_bg = None
        self._cfg_job = None
        self.keep_y = None
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick()
        self.autosave()

    # ---------------- data ---------------- #
    def load(self):
        data = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
        self.settings = dict(DEFAULT_SETTINGS, **data.get("settings", {}))
        self.reminders = data.get("reminders") or [dict(r) for r in DEFAULT_REMINDERS]
        self.stats = data.get("stats", {})
        self.tasks = data.get("tasks", [])
        self.gk = data.get("gk", {})
        self.tab = "reminders"
        self.daily_refresh()
        now = time.time()
        for r in self.reminders:
            if r.get("next", 0) < now:
                r["next"] = now + r["interval"] * 60

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(dict(settings=self.settings, reminders=self.reminders,
                               stats=self.stats, tasks=self.tasks, gk=self.gk), f, indent=2)
        except Exception:
            pass

    def autosave(self):
        self.save()
        self.root.after(30000, self.autosave)

    def close(self):
        self.save()
        self.root.destroy()

    def day(self):
        return self.stats.setdefault(today(), dict(water=0, walk=0))

    @property
    def t(self):
        return THEMES[self.settings["theme"]]

    # ---------------- language ---------------- #
    def T(self, key):
        return TR[key][LANG_IDX.get(self.settings.get("lang", "en"), 0)]

    def rname(self, r):
        if r["id"] in BUILTIN and not r.get("custom"):
            return self.T("r_%s_name" % r["id"])
        return r["name"]

    def rmsg(self, r):
        if r["id"] in BUILTIN and not r.get("custom"):
            return self.T("r_%s_msg" % r["id"])
        return r["message"]

    def datestr(self):
        d = dt.date.today()
        lang, wd = self.settings.get("lang", "en"), d.weekday()
        if lang == "ja":
            return "%d年%d月%d日（%s）" % (d.year, d.month, d.day, "月火水木金土日"[wd])
        if lang == "ta":
            names = ("திங்கள்", "செவ்வாய்", "புதன்", "வியாழன்", "வெள்ளி", "சனி", "ஞாயிறு")
            return "%s, %02d-%02d-%d" % (names[wd], d.day, d.month, d.year)
        return d.strftime("%A, %d %B %Y")

    # ---------------- UI ---------------- #
    def button(self, parent, text, cmd, primary=False, small=False):
        t = self.t
        return tk.Button(
            parent, text=text, command=cmd, relief="flat", bd=0, cursor="hand2",
            bg=t["accent"] if primary else t["btn"],
            fg="#ffffff" if primary else t["btnfg"],
            activebackground=t["accent"], activeforeground="#ffffff",
            padx=8 if small else 12, pady=3 if small else 6,
            font=("TkDefaultFont", 9 if small else 10))

    def build(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.cards, self.stat_boxes, self.sections, self.wid = {}, [], [], {}
        t = self.t
        self.root.configure(bg=t["bg"])
        self.root.title(self.T("app"))

        self.status = tk.Label(self.root, bg=t["card"], fg=t["sub"], anchor="w",
                               padx=16, pady=6)
        self.status.pack(side="bottom", fill="x")
        sb = tk.Scrollbar(self.root)
        sb.pack(side="right", fill="y")
        c = self.canvas = tk.Canvas(self.root, bg=t["bg"], highlightthickness=0,
                                    yscrollcommand=lambda a, b: (sb.set(a, b), self.fix_bg()))
        sb.configure(command=c.yview)
        c.pack(side="left", fill="both", expand=True)

        # everything lives on one scrollable canvas whose lowest item is the picture
        self.bg_item = c.create_image(0, 0, anchor="nw")
        if self._last_bg and self._last_bg[0][2] == self.settings["theme"]:
            c.itemconfigure(self.bg_item, image=self._last_bg[1])
        self.title_id = c.create_text(0, 0, anchor="nw", text=self.T("app"),
                                      fill="#ffffff", font=("TkDefaultFont", 20, "bold"))
        self.date_id = c.create_text(0, 0, anchor="nw", text=self.datestr(), fill="#e5e7eb")
        self.hbtns = [
            self.button(c, self.T("add_rem"), lambda: self.reminder_dialog(None),
                        primary=True, small=True),
            self.button(c, self.T("dark") if self.settings["theme"] == "light" else self.T("light"),
                        self.toggle_theme, small=True),
            self.button(c, self.T("settings"), self.settings_dialog, small=True)]
        for b in self.hbtns:
            self.wid[b] = c.create_window(0, 0, window=b, anchor="nw")

        # daily summary
        self.water_box = self.stat_box(self.T("water"), self.add_water, self.T("plus_glass"))
        self.walk_box = self.stat_box(self.T("walking"), self.add_walk,
                                      self.T("plus_min") % self.settings["walk_log"])
        self.score_box = self.stat_box(self.T("score"), None, None)
        self.task_box = self.stat_box(self.T("tasks"), None, None)
        self.add_section("cells", [b["frame"] for b in self.stat_boxes], 200, 4)

        # tabs
        open_t = sum(1 for x in self.tasks if not x["done"])
        tabs = []
        for key, label in (("reminders", self.T("reminders")),
                           ("tasks", self.T("tasks_tab") % open_t),
                           ("gk", self.T("gk_tab"))):
            on = self.tab == key
            tabs.append(tk.Button(
                c, text=label, relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
                bg=t["accent"] if on else t["btn"], fg="#ffffff" if on else t["btnfg"],
                activebackground=t["accent"], activeforeground="#ffffff",
                command=lambda k=key: self.set_tab(k)))
        self.add_section("flow", tabs)

        if self.tab == "tasks":
            self.build_tasks()
        elif self.tab == "gk":
            self.build_gk()
        else:
            self.add_section("cells", [self.make_card(r) for r in self.reminders], 300, 4)
        self.refresh()
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(ev, self.on_wheel)
        c.bind("<Configure>", self.on_cfg)
        self.fix_bg()
        self.relayout()

    def stat_box(self, title, cmd, btn_text):
        t = self.t
        f = tk.Frame(self.canvas, bg=t["card"], padx=12, pady=10)
        tk.Label(f, text=title, bg=t["card"], fg=t["sub"]).pack(anchor="w")
        val = tk.Label(f, text="", bg=t["card"], fg=t["fg"],
                       font=("TkDefaultFont", 16, "bold"))
        val.pack(anchor="w")
        bar = Bar(f, t["trough"], t["accent"])
        bar.pack(fill="x", pady=6)
        if cmd:
            self.button(f, btn_text, cmd, small=True).pack(anchor="w")
        box = dict(frame=f, val=val, bar=bar)
        self.stat_boxes.append(box)
        return box

    # ---------------- background picture + layout ---------------- #
    def add_section(self, kind, widgets, minw=0, maxc=1):
        """kind 'cells': equal-width responsive grid; 'flow': natural-size row that wraps."""
        self.sections.append((kind, widgets, minw, maxc))
        for w in widgets:
            self.wid[w] = self.canvas.create_window(0, 0, window=w, anchor="nw")

    def make_bg(self, W, H):
        if Image is None or self.bg_src is None or W < 50 or H < 50:
            return None
        key = (W, H, self.settings["theme"])
        if self._last_bg and self._last_bg[0] == key:
            return self._last_bg[1]
        ph = ImageTk.PhotoImage(render_bg(self.bg_src, W, H, self.settings["theme"] == "dark"))
        self._last_bg = (key, ph)
        return ph

    def update_bg(self):
        self._cfg_job = None
        c = self.canvas
        if not c.winfo_exists():
            return
        ph = self.make_bg(c.winfo_width(), c.winfo_height())
        if ph is not None:
            c.itemconfigure(self.bg_item, image=ph)
        self.fix_bg()

    def fix_bg(self):
        """Keep the picture glued to the visible area while the page scrolls."""
        try:
            self.canvas.coords(self.bg_item, 0, self.canvas.canvasy(0))
            self.canvas.tag_lower(self.bg_item)
        except (tk.TclError, AttributeError):
            pass

    def on_cfg(self, event=None):
        self.relayout()
        if self._cfg_job:
            self.root.after_cancel(self._cfg_job)
        self._cfg_job = self.root.after(100, self.update_bg)

    def relayout(self):
        c = self.canvas
        if not c.winfo_exists():
            return
        W, H = c.winfo_width(), c.winfo_height()
        if W < 60:
            return
        c.update_idletasks()
        cw_max = min(W - 24, 1100)
        left = (W - cw_max) // 2
        gap, y = 10, 16

        # header: title + date on the left, buttons on the right (or below when narrow)
        c.coords(self.title_id, left, y)
        tb = c.bbox(self.title_id)
        th = tb[3] - tb[1]
        c.coords(self.date_id, left, y + th + 2)
        db = c.bbox(self.date_id)
        text_w, text_h = max(tb[2] - tb[0], db[2] - db[0]), th + (db[3] - db[1]) + 2
        bw = sum(b.winfo_reqwidth() for b in self.hbtns) + 6 * (len(self.hbtns) - 1)
        if text_w + bw + 20 <= cw_max:
            x = left + cw_max
            for b in reversed(self.hbtns):
                x -= b.winfo_reqwidth()
                c.coords(self.wid[b], x, y + 4)
                x -= 6
            y += text_h
        else:
            y += text_h + 6
            x = left
            for b in self.hbtns:
                c.coords(self.wid[b], x, y)
                x += b.winfo_reqwidth() + 6
            y += self.hbtns[0].winfo_reqheight()
        y += gap + 6

        for kind, widgets, minw, maxc in self.sections:
            if kind == "flow":
                x, rowh = left, 0
                for w in widgets:
                    ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
                    if x > left and x + ww > left + cw_max:
                        x, y, rowh = left, y + rowh + 6, 0
                    c.coords(self.wid[w], x, y)
                    x += ww + 6
                    rowh = max(rowh, wh)
                y += rowh + gap
            else:
                cols = max(1, min(maxc, (cw_max + gap) // (minw + gap)))
                cw = (cw_max - gap * (cols - 1)) // cols
                for i in range(0, len(widgets), cols):
                    row = widgets[i:i + cols]
                    for j, w in enumerate(row):
                        c.itemconfigure(self.wid[w], width=cw)
                        c.coords(self.wid[w], left + j * (cw + gap), y)
                    c.update_idletasks()
                    rowh = max(w.winfo_reqheight() for w in row)
                    for w in row:
                        c.itemconfigure(self.wid[w], height=rowh)
                    y += rowh + gap
        c.configure(scrollregion=(0, 0, W, max(y + 16, H)))
        if self.keep_y is not None:
            c.yview_moveto(self.keep_y)
            self.keep_y = None

    def make_card(self, r):
        t = self.t
        f = tk.Frame(self.canvas, bg=t["card"], padx=12, pady=10)
        top = tk.Frame(f, bg=t["card"])
        top.pack(fill="x")
        tk.Label(top, text="\u25cf", fg=r.get("color", t["accent"]), bg=t["card"]
                 ).pack(side="left")
        tk.Label(top, text=" " + self.rname(r), bg=t["card"], fg=t["fg"],
                 font=("TkDefaultFont", 11, "bold")).pack(side="left")
        var = tk.BooleanVar(value=r["enabled"])
        tk.Checkbutton(top, text=self.T("on"), variable=var, bg=t["card"], fg=t["sub"],
                       selectcolor=t["card"], activebackground=t["card"],
                       command=lambda: self.toggle(r, var.get())).pack(side="right")
        tk.Label(f, text=self.rmsg(r), bg=t["card"], fg=t["sub"], wraplength=260,
                 justify="left").pack(anchor="w", pady=(4, 2))
        time_lbl = tk.Label(f, text="", bg=t["card"], fg=t["fg"],
                            font=("TkFixedFont", 20, "bold"))
        time_lbl.pack(anchor="w")
        bar = Bar(f, t["trough"], r.get("color", t["accent"]))
        bar.pack(fill="x", pady=6)
        row = tk.Frame(f, bg=t["card"])
        row.pack(fill="x")
        self.button(row, self.T("done"), lambda: self.done(r), primary=True, small=True
                    ).pack(side="left")
        self.button(row, self.T("snooze"), lambda: self.snooze(r), small=True
                    ).pack(side="left", padx=4)
        self.button(row, self.T("edit"), lambda: self.reminder_dialog(r), small=True
                    ).pack(side="left")
        self.button(row, self.T("delete"), lambda: self.delete(r), small=True
                    ).pack(side="right")
        self.cards[r["id"]] = dict(frame=f, time=time_lbl, bar=bar)
        return f

    def on_wheel(self, e):
        if self.canvas.winfo_exists():
            d = -1 if (e.num == 4 or getattr(e, "delta", 0) > 0) else 1
            self.canvas.yview_scroll(d, "units")

    # ---------------- actions ---------------- #
    def toggle_theme(self):
        self.settings["theme"] = "dark" if self.settings["theme"] == "light" else "light"
        self.save()
        self.build()

    def toggle(self, r, on):
        r["enabled"] = on
        if on:
            r["next"] = time.time() + r["interval"] * 60
        self.save()

    def add_water(self):
        self.day()["water"] += 1
        self.refresh()
        self.save()

    def add_walk(self):
        self.day()["walk"] += self.settings["walk_log"]
        self.refresh()
        self.save()

    def done(self, r):
        r["next"] = time.time() + r["interval"] * 60
        if r.get("kind") == "water":
            self.day()["water"] += 1
        elif r.get("kind") == "walk":
            self.day()["walk"] += self.settings["walk_log"]
        self.refresh()
        self.save()

    def snooze(self, r):
        r["next"] = time.time() + 300
        self.refresh()

    def delete(self, r):
        if messagebox.askyesno(self.T("app"), self.T("del_q") % self.rname(r)):
            self.reminders.remove(r)
            self.save()
            self.build()

    # ---------------- dialogs ---------------- #
    def dialog(self, title):
        t = self.t
        d = tk.Toplevel(self.root)
        d.title(title)
        d.configure(bg=t["bg"], padx=16, pady=14)
        d.transient(self.root)
        d.resizable(False, False)
        d.grab_set()
        return d

    def field(self, d, label, value, row, width=30):
        t = self.t
        tk.Label(d, text=label, bg=t["bg"], fg=t["fg"]).grid(row=row, column=0,
                                                              sticky="w", pady=4)
        var = tk.StringVar(value=str(value))
        tk.Entry(d, textvariable=var, width=width).grid(row=row, column=1,
                                                        sticky="we", padx=8)
        return var

    def reminder_dialog(self, r):
        d = self.dialog(self.T("edit_rem") if r else self.T("new_rem"))
        name = self.field(d, self.T("name"), self.rname(r) if r else "", 0)
        msg = self.field(d, self.T("message"), self.rmsg(r) if r else "", 1)
        mins = self.field(d, self.T("every"), r["interval"] if r else 60, 2, 8)

        def ok():
            try:
                m = int(mins.get())
                assert 1 <= m <= 1440
            except Exception:
                messagebox.showerror(self.T("app"), self.T("err_min"))
                return
            if not name.get().strip():
                messagebox.showerror(self.T("app"), self.T("err_name"))
                return
            if r:
                changed = (name.get().strip() != self.rname(r)
                           or msg.get().strip() != self.rmsg(r))
                r.update(name=name.get().strip(), message=msg.get().strip(), interval=m)
                if changed:
                    r["custom"] = True
                r["next"] = time.time() + m * 60
            else:
                self.reminders.append(dict(
                    id="r%d" % int(time.time() * 1000), name=name.get().strip(),
                    message=msg.get().strip() or name.get().strip(), interval=m,
                    enabled=True, kind="", next=time.time() + m * 60,
                    color=COLORS[len(self.reminders) % len(COLORS)]))
            self.save()
            d.destroy()
            self.build()

        row = tk.Frame(d, bg=self.t["bg"])
        row.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="e")
        self.button(row, self.T("cancel"), d.destroy).pack(side="left", padx=4)
        self.button(row, self.T("save"), ok, primary=True).pack(side="left")

    def settings_dialog(self):
        s = self.settings
        d = self.dialog(self.T("settings"))
        wg = self.field(d, self.T("water_goal"), s["water_goal"], 0, 8)
        kg = self.field(d, self.T("walk_goal"), s["walk_goal"], 1, 8)
        kl = self.field(d, self.T("walk_log"), s["walk_log"], 2, 8)
        qs = self.field(d, self.T("q_start"), s["quiet_start"], 4, 8)
        qe = self.field(d, self.T("q_end"), s["quiet_end"], 5, 8)
        qon = tk.BooleanVar(value=s["quiet_on"])
        snd = tk.BooleanVar(value=s["sound"])
        t = self.t
        for i, (txt, var) in enumerate([(self.T("q_on"), qon), (self.T("beep"), snd)]):
            tk.Checkbutton(d, text=txt, variable=var, bg=t["bg"], fg=t["fg"],
                           selectcolor=t["card"], activebackground=t["bg"]
                           ).grid(row=3 if i == 0 else 6, column=0, columnspan=2, sticky="w")

        tk.Label(d, text=self.T("language"), bg=t["bg"], fg=t["fg"]
                 ).grid(row=7, column=0, sticky="w", pady=4)
        lang = tk.StringVar(value=LANGS.get(s.get("lang", "en"), "English"))
        tk.OptionMenu(d, lang, *LANGS.values()).grid(row=7, column=1, sticky="w", padx=8)

        def ok():
            try:
                for v in (qs.get(), qe.get()):
                    dt.datetime.strptime(v, "%H:%M")
                s.update(water_goal=max(1, int(wg.get())), walk_goal=max(1, int(kg.get())),
                         walk_log=max(1, int(kl.get())), quiet_start=qs.get(),
                         quiet_end=qe.get(), quiet_on=qon.get(), sound=snd.get(),
                         lang=[k for k, v in LANGS.items() if v == lang.get()][0])
            except Exception:
                messagebox.showerror(APP, self.T("err_vals"))
                return
            self.save()
            d.destroy()
            self.build()

        row = tk.Frame(d, bg=t["bg"])
        row.grid(row=8, column=0, columnspan=2, pady=(10, 0), sticky="e")
        self.button(row, self.T("cancel"), d.destroy).pack(side="left", padx=4)
        self.button(row, self.T("save"), ok, primary=True).pack(side="left")

    # ---------------- tabs: tasks + GK ---------------- #
    def set_tab(self, key):
        self.tab = key
        self.build()

    def rebuild_keep(self):
        self.keep_y = self.canvas.yview()[0]
        self.build()

    def daily_refresh(self):
        """Runs at launch and every new day (24-hour refresh)."""
        d = today()
        if self.gk.get("date") != d:
            self.gk = dict(date=d, answers={}, score=0)
        for x in self.tasks:
            if x.get("daily") and x.get("done_date") != d:
                x["done"] = False
        self.tasks = [x for x in self.tasks if not (
            x["done"] and not x.get("daily") and x.get("done_date") != d)]
        for k in sorted(self.stats)[:-60]:
            del self.stats[k]

    def gk_today(self):
        n = len(GK_BANK)
        start = (dt.date.today().toordinal() * 5) % n
        return [(start + k) % n for k in range(5)]

    def answer(self, i, oi):
        self.gk["answers"][str(i)] = oi
        if oi == GK_BANK[i][2]:
            self.gk["score"] += 1
        self.save()
        self.rebuild_keep()

    def toggle_task(self, x, on):
        x["done"] = on
        x["done_date"] = today()
        self.save()
        self.rebuild_keep()

    def del_task(self, x):
        self.tasks.remove(x)
        self.save()
        self.rebuild_keep()

    def build_tasks(self):
        t, c = self.t, self.canvas
        widgets = []
        row = tk.Frame(c, bg=t["card"], padx=10, pady=10)
        var, daily = tk.StringVar(), tk.BooleanVar()
        ent = tk.Entry(row, textvariable=var)
        ent.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Checkbutton(row, text=self.T("repeat"), variable=daily, bg=t["card"], fg=t["fg"],
                       selectcolor=t["card"], activebackground=t["card"]
                       ).pack(side="left", padx=6)

        def add(event=None):
            text = var.get().strip()
            if text:
                self.tasks.append(dict(id=str(time.time()), text=text, done=False,
                                       daily=daily.get()))
                self.save()
                self.build()
        ent.bind("<Return>", add)
        self.button(row, self.T("add_task"), add, primary=True, small=True).pack(side="left")
        ent.focus_set()
        widgets.append(row)
        if not self.tasks:
            box = tk.Frame(c, bg=t["card"], padx=12, pady=14)
            tk.Label(box, text=self.T("no_tasks"), bg=t["card"], fg=t["sub"]).pack()
            widgets.append(box)
        for x in self.tasks:
            card = tk.Frame(c, bg=t["card"], padx=10, pady=6)
            v = tk.BooleanVar(value=x["done"])
            tk.Checkbutton(card, text=x["text"], variable=v, bg=t["card"],
                           fg=t["sub"] if x["done"] else t["fg"], selectcolor=t["card"],
                           activebackground=t["card"],
                           command=lambda x=x, v=v: self.toggle_task(x, v.get())
                           ).pack(side="left")
            if x.get("daily"):
                tk.Label(card, text=self.T("daily"), bg=t["card"], fg=t["accent"]
                         ).pack(side="left", padx=6)
            self.button(card, self.T("delete"), lambda x=x: self.del_task(x), small=True
                        ).pack(side="right")
            widgets.append(card)
        self.add_section("cells", widgets, 400, 1)

    def build_gk(self):
        t, c = self.t, self.canvas
        qs = self.gk_today()
        ans = self.gk["answers"]
        head = tk.Frame(c, bg=t["card"], padx=12, pady=10)
        tk.Label(head, text=self.T("gk_title") % (self.gk["score"], len(qs)), bg=t["card"],
                 fg=t["fg"], font=("TkDefaultFont", 11, "bold"), wraplength=700,
                 justify="left").pack(anchor="w")
        self.add_section("cells", [head], 400, 1)
        cards = []
        for n, i in enumerate(qs, 1):
            q, opts, right = GK_BANK[i]
            card = tk.Frame(c, bg=t["card"], padx=12, pady=10)
            tk.Label(card, text="%d. %s" % (n, q), bg=t["card"], fg=t["fg"],
                     wraplength=460, justify="left",
                     font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 6))
            chosen = ans.get(str(i))
            for oi, o in enumerate(opts):
                bg, fg = t["btn"], t["btnfg"]
                if chosen is not None:
                    if oi == right:
                        bg, fg = t["good"], "#ffffff"
                    elif oi == chosen:
                        bg, fg = "#ef4444", "#ffffff"
                tk.Button(card, text=o, anchor="w", relief="flat", bd=0, bg=bg, fg=fg,
                          activebackground=t["accent"], activeforeground="#ffffff",
                          padx=10, pady=4, cursor="hand2", disabledforeground=fg,
                          state="disabled" if chosen is not None else "normal",
                          command=lambda i=i, oi=oi: self.answer(i, oi)
                          ).pack(fill="x", pady=2)
            cards.append(card)
        self.add_section("cells", cards, 480, 2)
        if len(ans) >= len(qs):
            done = tk.Frame(c, bg=t["card"], padx=12, pady=10)
            tk.Label(done, text=self.T("gk_done"), bg=t["card"], fg=t["good"]).pack()
            self.add_section("cells", [done], 400, 1)

    # ---------------- engine ---------------- #
    def in_quiet(self):
        s = self.settings
        if not s["quiet_on"]:
            return False
        try:
            now = dt.datetime.now().time()
            a = dt.datetime.strptime(s["quiet_start"], "%H:%M").time()
            b = dt.datetime.strptime(s["quiet_end"], "%H:%M").time()
        except ValueError:
            return False
        return (a <= now < b) if a <= b else (now >= a or now < b)

    def fire(self, r):
        r["next"] = time.time() + r["interval"] * 60
        title, msg = self.rname(r), self.rmsg(r)
        if self.settings["sound"]:
            self.root.bell()
        if not native_notify(title, msg):
            self.popup(title, msg)
        self.status.configure(text=self.T("sent") % title)

    def popup(self, title, msg):
        t = self.t
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.configure(bg=t["accent"], padx=2, pady=2)
        body = tk.Frame(p, bg=t["card"], padx=14, pady=12)
        body.pack()
        tk.Label(body, text=title, bg=t["card"], fg=t["fg"],
                 font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        tk.Label(body, text=msg, bg=t["card"], fg=t["sub"], wraplength=260,
                 justify="left").pack(anchor="w", pady=4)
        self.button(body, "OK", p.destroy, primary=True, small=True).pack(anchor="e")
        p.update_idletasks()
        x = p.winfo_screenwidth() - p.winfo_width() - 20
        y = p.winfo_screenheight() - p.winfo_height() - 70
        p.geometry("+%d+%d" % (x, y))
        p.after(12000, lambda: p.winfo_exists() and p.destroy())

    @staticmethod
    def fmt(sec):
        sec = max(0, int(sec))
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)

    def refresh(self):
        t, s, d = self.t, self.settings, self.day()
        wf = d["water"] / s["water_goal"]
        kf = d["walk"] / s["walk_goal"]
        self.water_box["val"].configure(text=self.T("glasses_fmt") % (d["water"], s["water_goal"]))
        self.water_box["bar"].set(wf, "#0ea5e9" if wf < 1 else t["good"])
        self.walk_box["val"].configure(text=self.T("min_fmt") % (d["walk"], s["walk_goal"]))
        self.walk_box["bar"].set(kf, "#22c55e" if kf < 1 else t["good"])
        score = int(100 * (min(wf, 1) + min(kf, 1)) / 2)
        self.score_box["val"].configure(text="%d%%" % score)
        self.score_box["bar"].set(score / 100, t["good"] if score >= 100 else t["accent"])
        done_t = sum(1 for x in self.tasks if x["done"])
        self.task_box["val"].configure(text=self.T("done_fmt") % (done_t, len(self.tasks)))
        self.task_box["bar"].set(done_t / len(self.tasks) if self.tasks else 0, t["good"])

        now = time.time()
        nxt = None
        for r in self.reminders:
            card = self.cards.get(r["id"])
            if not card:
                continue
            total = r["interval"] * 60
            if r["enabled"]:
                left = r["next"] - now
                card["time"].configure(text=self.fmt(left), fg=t["fg"])
                card["bar"].set(1 - left / total)
                if nxt is None or left < nxt[0]:
                    nxt = (left, self.rname(r))
            else:
                card["time"].configure(text=self.T("paused"), fg=t["sub"])
                card["bar"].set(0)
        quiet = "  |  " + self.T("quiet_active") if self.in_quiet() else ""
        if nxt:
            self.status.configure(text=self.T("next_fmt") % (nxt[1], self.fmt(nxt[0]), quiet))
        else:
            self.status.configure(text=self.T("no_active") + quiet)

    def tick(self):
        if today() != self.last_day:          # new day: 24-hour refresh
            self.last_day = today()
            self.daily_refresh()
            self.save()
            self.build()
            self.popup(self.T("app"), self.T("new_day"))
        now = time.time()
        for r in list(self.reminders):
            if r["enabled"] and now >= r["next"]:
                if self.in_quiet():
                    r["next"] = now + 60
                else:
                    self.fire(r)
        self.refresh()
        self.root.after(1000, self.tick)


def main():
    root = tk.Tk()
    HealthApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
