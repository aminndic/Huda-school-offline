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
    # أندرويد: استخدم متغير البيئة أولاً
    path = os.environ.get("FLET_APP_STORAGE_DATA")
    if path and os.path.exists(os.path.dirname(path)):
        os.makedirs(path, exist_ok=True)
        return path

    # فلت 1.x: جرب page.app_data_dir
    try:
        path = page.app_data_dir
        if path:
            os.makedirs(path, exist_ok=True)
            return path
    except Exception:
        pass

    # سطح المكتب فقط
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
            message = "تم
