name: Build Huda School APK

on:
  workflow_dispatch:
  push:
    branches: [ "main", "master" ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Get project files
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Flet
        run: |
          python -m pip install --upgrade pip
          pip install flet

      - name: Prepare build directory
        run: yes | flet build apk --arch arm64-v8a --verbose 2>&1 || true

      - name: Fix minSdkVersion in build.gradle
        run: |
          GRADLE_FILE="build/flutter/android/app/build.gradle"
          if [ -f "$GRADLE_FILE" ]; then
            sed -i 's/minSdkVersion 23/minSdkVersion 24/g' "$GRADLE_FILE"
            echo "✅ Fixed minSdkVersion in $GRADLE_FILE"
          else
            echo "❌ build.gradle not found"
            find . -name "build.gradle" 2>/dev/null
          fi

      - name: Build Android APK
        run: yes | flet build apk --arch arm64-v8a --verbose

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: huda-school-apk
          path: build/apk/*.apk
          if-no-files-found: error

الأفضل هو إنشاء pyproject.toml لأنه الطريقة الرسمية. جرب الاثنين وأخبرني بالنتيجة.

[project]
name = "huda-school-offline"
version = "1.0.0"
description = "Offline student and grades management app for مدرسة الهدى الثانوية بنين"
requires-python = ">=3.12,<3.13"
dependencies = [
    "flet",
    "openpyxl",
    "reportlab",
    "arabic-reshaper",
    "python-bidi",
]

[tool.flet]
org = "org.aminndic"
product = "مدرسة الهدى الثانوية بنين"
company = "مدرسة الهدى الثانوية بنين"
copyright = "Copyright 2026"

[tool.flet.app]
path = "."

[tool.flet.android]
min_sdk_version = 23      الملف موجود اعدله

عدّل السطر الأخير فقط من 23 إلى 24:

toml
[project]
name = "huda-school-offline"
version = "1.0.0"
description = "Offline student and grades management app for مدرسة الهدى الثانوية بنين"
requires-python = ">=3.12,<3.13"
dependencies = [
    "flet",
    "openpyxl",
    "reportlab",
    "arabic-reshaper",
    "python-bidi",
]

[tool.flet]
org = "org.aminndic"
product = "مدرسة الهدى الثانوية بنين"
company = "مدرسة الهدى الثانوية بنين"
copyright = "Copyright 2026"

[tool.flet.app]
path = "."

[tool.flet.android]
min_sdk_version = 24

التغيير الوحيد هو:

min_sdk_version = 23  →  min_sdk_version = 24

افتح الملف على GitHub واضغط ✏️ وغيّر الرقم ثم اضغط Commit changes.

المشكلة في كودك في main.py — السطر 36 يحاول إنشاء مجلد في /data/.huda_school وهذا المسار ممنوع على أندرويد.

أرسل لي الكود الموجود في main.py خصوصاً دالة get_data_dir في السطر 36.

على الأرجح الكود هكذا:

python
def get_data_dir():
    return "/data/.huda_school"  # ❌ خطأ على أندرويد

الحل هو استخدام المسار الصحيح على أندرويد:

python
import os
import flet as ft

def get_data_dir(page: ft.Page):
    # يعطي المسار الصحيح على كل نظام تشغيل
    data_dir = page.app_data_dir
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

أو إذا كنت لا تستخدم page:

python
import os
import platform

def get_data_dir():
    if platform.system() == "Android":
        # على أندرويد استخدم المتغير البيئي
        base = os.environ.get("FLET_APP_STORAGE_DATA", "/data/data/org.aminndic")
    else:
        base = os.path.expanduser("~")
    
    data_dir = os.path.join(base, ".huda_school")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

أرسل لي الكود الحالي وسأصلحه بدقة.

import os import sqlite3 import tempfile from datetime import datetime import flet as ft from openpyxl import Workbook, load_workbook from reportlab.lib.pagesizes import A4 from reportlab.pdfgen import canvas from reportlab.pdfbase import pdfmetrics from reportlab.pdfbase.ttfonts import TTFont try

PASTED

المشكلة في دالة get_data_dir() — الدالة ft.app_storage_path() لا تعمل خارج سياق page، فتفشل وتذهب للـ fallback الذي يحاول إنشاء /data/.huda_school وهو ممنوع على أندرويد.

الحل: مرر page للدالة واستخدم page.app_data_dir:

python
import os
import sqlite3
import tempfile
from datetime import datetime

import flet as ft
from openpyxl import Workbook, load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:
    arabic_reshaper = None
    get_display = None


APP_TITLE = "مدرسة الهدى الثانوية بنين"
SUBJECTS = ["اللغة العربية", "الرياضيات", "اللغة الإنجليزية", "الفيزياء"]
DB_NAME = "students.db"


def get_data_dir(page: ft.Page):
    # استخدم page.app_data_dir — يعطي المسار الصحيح على أندرويد وسطح المكتب
    try:
        path = page.app_data_dir
        if path:
            os.makedirs(path, exist_ok=True)
            return path
    except Exception:
        pass
    # fallback للتطوير فقط
    path = os.path.join(os.path.expanduser("~"), ".huda_school")
    os.makedirs(path, exist_ok=True)
    return path


DB_PATH = None


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT DEFAULT '',
            arabic REAL DEFAULT 0,
            math REAL DEFAULT 0,
            english REAL DEFAULT 0,
            physics REAL DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def shape_arabic(text):
    text = str(text or "")
    if arabic_reshaper and get_display:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


def main(page: ft.Page):
    global DB_PATH
    # ✅ الآن نمرر page للدالة
    DB_PATH = os.path.join(get_data_dir(page), DB_NAME)
    page.title = APP_TITLE
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 14
    page.scroll = ft.ScrollMode.AUTO
    page.window_width = 1000
    page.window_height = 800

    conn = connect_db()
    selected_student_id = None
    status = ft.Text("", color="#146C43")
    search_box = ft.TextField(label="بحث باسم الطالب أو الفصل", prefix_icon=ft.Icons.SEARCH, expand=True)
    name_box = ft.TextField(label="اسم الطالب", expand=True)
    class_box = ft.TextField(label="الفصل", width=150)
    arabic_box = ft.TextField(label="العربية", value="0", width=110, keyboard_type=ft.KeyboardType.NUMBER)
    math_box = ft.TextField(label="الرياضيات", value="0", width=110, keyboard_type=ft.KeyboardType.NUMBER)
    english_box = ft.TextField(label="الإنجليزية", value="0", width=110, keyboard_type=ft.KeyboardType.NUMBER)
    physics_box = ft.TextField(label="الفيزياء", value="0", width=110, keyboard_type=ft.KeyboardType.NUMBER)
    students_column = ft.Column(spacing=8)

    def show_message(message, error=False):
        status.value = message
        status.color = "#B42318" if error else "#146C43"
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def number(value):
        try:
            return float(value or 0)
        except (ValueError, TypeError):
            return 0.0

    def clear_form():
        nonlocal selected_student_id
        selected_student_id = None
        name_box.value = ""
        class_box.value = ""
        arabic_box.value = "0"
        math_box.value = "0"
        english_box.value = "0"
        physics_box.value = "0"
        save_button.text = "إضافة الطالب"
        page.update()

    def refresh_students(*_):
        students_column.controls.clear()
        term = (search_box.value or "").strip()
        if term:
            rows = conn.execute(
                "SELECT * FROM students WHERE name LIKE ? OR class_name LIKE ? ORDER BY id DESC",
                (f"%{term}%", f"%{term}%")
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()

        if not rows:
            students_column.controls.append(
                ft.Container(content=ft.Text("لا توجد بيانات بعد. أضف طالباً جديداً.", color="#667085"),
                             padding=20, alignment=ft.alignment.center)
            )
        for row in rows:
            total = sum(float(row[k] or 0) for k in ("arabic", "math", "english", "physics"))
            student_line = ft.Row(
                controls=[
                    ft.Text(str(row["id"]), width=40),
                    ft.Column([
                        ft.Text(row["name"], weight=ft.FontWeight.BOLD),
                        ft.Text(f"الفصل: {row['class_name'] or '—'}  |  المجموع: {total:g} / 400",
                                size=12, color="#475467"),
                    ], expand=True, spacing=3),
                    ft.IconButton(ft.Icons.EDIT, tooltip="تعديل", on_click=lambda e, r=dict(row): load_student(r)),
                    ft.IconButton(ft.Icons.PICTURE_AS_PDF, tooltip="شهادة PDF", on_click=lambda e, r=dict(row): make_pdf(r)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="حذف", icon_color="#B42318",
                                  on_click=lambda e, sid=row["id"], sn=row["name"]: confirm_delete(sid, sn)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            students_column.controls.append(
                ft.Container(content=student_line, padding=10, border=ft.border.all(1, "#EAECF0"),
                             border_radius=10, bgcolor="#FFFFFF")
            )
        page.update()

    def load_student(row):
        nonlocal selected_student_id
        selected_student_id = int(row["id"])
        name_box.value = row["name"] or ""
        class_box.value = row["class_name"] or ""
        arabic_box.value = str(row["arabic"] or 0)
        math_box.value = str(row["math"] or 0)
        english_box.value = str(row["english"] or 0)
        physics_box.value = str(row["physics"] or 0)
        save_button.text = "حفظ التعديلات"
        page.update()

    def confirm_delete(student_id, student_name):
        def close_dialog(_):
            page.close(dialog)

        def delete_now(_):
            conn.execute("DELETE FROM students WHERE id=?", (student_id,))
            conn.commit()
            page.close(dialog)
            if selected_student_id == student_id:
                clear_form()
            refresh_students()
            show_message(f"تم حذف الطالب: {student_name}")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("تأكيد الحذف"),
            content=ft.Text(f"هل تريد حذف الطالب «{student_name}»؟"),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.FilledButton("حذف", on_click=delete_now, style=ft.ButtonStyle(bgcolor="#B42318")),
            ],
        )
        page.open(dialog)

    def save_student(_):
        nonlocal selected_student_id
        name = (name_box.value or "").strip()
        if not name:
            show_message("اكتب اسم الطالب أولاً.", True)
            return
        values = (
            name, (class_box.value or "").strip(),
            number(arabic_box.value), number(math_box.value),
            number(english_box.value), number(physics_box.value)
        )
        if selected_student_id is None:
            conn.execute(
                "INSERT INTO students(name,class_name,arabic,math,english,physics) VALUES(?,?,?,?,?,?)",
                values
            )
            message = "تمت إضافة الطالب وحفظ بياناته على الجهاز."
        else:
            conn.execute(
                "UPDATE students SET name=?,class_name=?,arabic=?,math=?,english=?,physics=? WHERE id=?",
                values + (selected_student_id,)
            )
            message = "تم حفظ التعديلات."
        conn.commit()
        clear_form()
        refresh_students()
        show_message(message)

    def make_pdf(row):
        temp_dir = tempfile.gettempdir()
        safe_id = row["id"]
        path = os.path.join(temp_dir, f"huda_student_{safe_id}.pdf")
        pdf = canvas.Canvas(path, pagesize=A4)
        width, height = A4

        font_path = os.path.join(os.path.dirname(__file__), "assets", "Amiri-Regular.ttf")
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont("Amiri", font_path))
                font_name = "Amiri"
            else:
                font_name = "Helvetica"
        except Exception:
            font_name = "Helvetica"

        pdf.setFont(font_name, 18)
        pdf.drawCentredString(width / 2, height - 70, shape_arabic(APP_TITLE))
        pdf.setFont(font_name, 15)
        pdf.drawCentredString(width / 2, height - 110, shape_arabic("شهادة درجات طالب"))
        pdf.setFont(font_name, 12)
        y = height - 165
        lines = [
            f"اسم الطالب: {row['name']}",
            f"الفصل: {row['class_name'] or '—'}",
            f"اللغة العربية: {row['arabic'] or 0}",
            f"الرياضيات: {row['math'] or 0}",
            f"اللغة الإنجليزية: {row['english'] or 0}",
            f"الفيزياء: {row['physics'] or 0}",
            f"المجموع: {sum(float(row[k] or 0) for k in ('arabic','math','english','physics')):g} من 400",
            f"تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d')}",
        ]
        for line in lines:
            pdf.drawRightString(width - 55, y, shape_arabic(line))
            y -= 32
        pdf.line(55, y - 15, width - 55, y - 15)
        pdf.setFont(font_name, 10)
        pdf.drawCentredString(width / 2, 65, shape_arabic("إدارة المدرسة"))
        pdf.save()
        show_message(f"تم إنشاء ملف PDF في: {path}")
        try:
            page.launch_url("file://" + path)
        except Exception:
            pass

    def export_excel(_):
        rows = conn.execute("SELECT id,name,class_name,arabic,math,english,physics FROM students ORDER BY id").fetchall()
        wb = Workbook()
        ws = wb.active
        ws.title = "الطلاب"
        ws.append(["رقم", "اسم الطالب", "الفصل", "اللغة العربية", "الرياضيات", "اللغة الإنجليزية", "الفيزياء"])
        for r in rows:
            ws.append([r["id"], r["name"], r["class_name"], r["arabic"], r["math"], r["english"], r["physics"]])
        path = os.path.join(tempfile.gettempdir(), "طلاب_مدرسة_الهدى.xlsx")
        wb.save(path)
        show_message(f"تم تصدير Excel إلى: {path}")

    def import_excel_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        path = e.files[0].path
        if not path or not path.lower().endswith(".xlsx"):
            show_message("اختر ملف Excel بامتداد .xlsx فقط.", True)
            return
        try:
            wb = load_workbook(path, data_only=True)
            ws = wb.active
            imported = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[1]:
                    continue
                name = str(row[1]).strip()
                class_name = str(row[2] or "") if len(row) > 2 else ""
                vals = [number(row[i]) if len(row) > i else 0 for i in range(3, 7)]
                conn.execute(
                    "INSERT INTO students(name,class_name,arabic,math,english,physics) VALUES(?,?,?,?,?,?)",
                    (name, class_name, *vals)
                )
                imported += 1
            conn.commit()
            refresh_students()
            show_message(f"تم استيراد {imported} طالباً.")
        except Exception as ex:
            show_message(f"تعذر استيراد الملف: {ex}", True)

    file_picker = ft.FilePicker(on_result=import_excel_result)
    page.overlay.append(file_picker)

    save_button = ft.FilledButton("إضافة الطالب", icon=ft.Icons.SAVE, on_click=save_student)

    header = ft.Container(
        content=ft.Column([
            ft.Text("بسم الله الرحمن الرحيم", size=16, text_align=ft.TextAlign.CENTER),
            ft.Text(APP_TITLE, size=25, weight=ft.FontWeight.BOLD, color="#FFFFFF",
                    text_align=ft.TextAlign.CENTER),
            ft.Text("نظام إدارة الطلاب والدرجات — يعمل دون إنترنت", size=13,
                    color="#F3E8FF", text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        bgcolor="#6D28D9", padding=20, border_radius=14,
    )

    form = ft.Container(
        content=ft.Column([
            ft.Text("بيانات الطالب", size=18, weight=ft.FontWeight.BOLD, color="#5B21B6"),
            ft.Row([name_box, class_box], wrap=True),
            ft.Row([arabic_box, math_box, english_box, physics_box], wrap=True),
            ft.Row([
                save_button,
                ft.OutlinedButton("مسح الحقول", icon=ft.Icons.CLEAR, on_click=lambda e: clear_form()),
                ft.OutlinedButton("استيراد Excel", icon=ft.Icons.UPLOAD_FILE,
                                  on_click=lambda e: file_picker.pick_files(
                                      allowed_extensions=["xlsx"], allow_multiple=False)),
                ft.OutlinedButton("تصدير Excel", icon=ft.Icons.DOWNLOAD, on_click=export_excel),
            ], wrap=True),
        ], spacing=12),
        padding=16, bgcolor="#F9F5FF", border_radius=12,
    )

    page.add(
        header,
        ft.Container(height=8),
        form,
        ft.Row([
            ft.Text("سجل الطلاب", size=20, weight=ft.FontWeight.BOLD),
            search_box,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
        status,
        students_column,
        ft.Text("تنبيه: البيانات تحفظ في قاعدة SQLite داخل مساحة التطبيق على هذا الجهاز.",
                size=11, color="#667085"),
    )
    search_box.on_change = refresh_students
    refresh_students()


if __name__ == "__main__":
    ft.run(main)
