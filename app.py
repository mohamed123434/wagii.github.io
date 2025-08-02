import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# المسارات
BASE_DIR = os.path.dirname(__file__)
EXCEL_FOLDER = os.path.join(BASE_DIR, 'شركات')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')

# تأكد من وجود مجلد الشركات
if not os.path.exists(EXCEL_FOLDER):
    os.makedirs(EXCEL_FOLDER)

# تحميل المستخدمين
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# حفظ المستخدمين
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# إنشاء حساب admin إذا لم يكن موجود
users = load_users()
if not any(u['username'] == 'admin' for u in users):
    users.append({
        'username': 'admin',
        'password': 'admin123',   # بدون تشفير
        'role': 'admin'
    })
    save_users(users)
    print("تم إنشاء حساب المدير: admin / admin123")

# الصفحة الرئيسية - تسجيل الدخول
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        for user in users:
            print(f"Trying login for: {username} with password: {password}, comparing with: {user['username']} / {user['password']}")
            if user['username'] == username and user['password'] == password:
                session['username'] = username
                session['role'] = user.get('role', 'company')
                if session['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))

        error = 'اسم المستخدم أو كلمة المرور غير صحيحة'
        return render_template('login.html', error=error)

    return render_template('login.html')

# إنشاء حساب جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if any(user['username'] == username for user in users):
            flash('اسم المستخدم موجود بالفعل')
            return redirect(url_for('register'))
        users.append({'username': username, 'password': password, 'role': 'company'})  # بدون تشفير
        save_users(users)
        flash('تم إنشاء الحساب بنجاح')
        return redirect(url_for('login'))
    return render_template('register.html')

# لوحة تحكم الشركات
@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session['role'] != 'company':
        return redirect(url_for('login'))
    username = session['username']
    filepath = os.path.join(EXCEL_FOLDER, f"{username}.xlsx")
    sales_data = []
    try:
        if os.path.exists(filepath):
            df = pd.read_excel(filepath)
            required_columns = ['التاريخ', 'رقم الطلب', 'عنوان التوصيل', 'قيمة التوصيل', 'حالة التوصيل', 'السبب', 'العدد']
            if all(col in df.columns for col in required_columns):
                df = df[required_columns]
                sales_data = df.to_dict(orient='records')
            else:
                flash('بعض الأعمدة مفقودة في ملف Excel.')
        else:
            flash('لا يوجد ملف مبيعات لهذا المستخدم.')
    except Exception as e:
        flash(f"خطأ في قراءة الملف: {e}")
    return render_template('dashboard.html', username=username, sales_data=sales_data)

# لوحة تحكم المدير
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    users = load_users()
    companies = [u['username'] for u in users if u['role'] == 'company']
    return render_template('admin.html', companies=companies)

# رفع ملفات Excel من قبل المدير
import re

def clean_filename(name):
    # إزالة الأحرف غير المسموح بها وتحويل المسافات إلى "_"
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[\s]+', '_', name)
    return name

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    company = request.form['company_name']
    file = request.files['excel_file']

    try:
        if file and file.filename.endswith('.xlsx'):
            safe_company = clean_filename(company)
            if not safe_company:
                flash('❌ اسم الشركة غير صالح لحفظ الملف.')
                return redirect(url_for('admin_dashboard'))

            filename = f"{safe_company}.xlsx"
            filepath = os.path.join(EXCEL_FOLDER, filename)

            print(f"🟢 Trying to upload for company: {company}")
            print(f"📂 Will save to: {filepath}")

            file.save(filepath)
            flash('✅ تم رفع الملف بنجاح')
        else:
            flash('❌ صيغة الملف غير مدعومة. يجب أن يكون Excel (.xlsx فقط)')
    except Exception as e:
        flash(f'❌ فشل رفع الملف: {e}')

    return redirect(url_for('admin_dashboard'))

# تغيير كلمة المرور
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        users = load_users()
        for user in users:
            if user['username'] == session['username'] and user['password'] == old:
                user['password'] = new  # بدون تشفير
                save_users(users)
                flash('تم تحديث كلمة المرور')
                return redirect(url_for('dashboard'))
        flash('كلمة المرور الحالية غير صحيحة')
    return render_template('change_password.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# تشغيل التطبيق
if __name__ == '_main_':
    from os import environ
    app.run(host='0.0.0.0', port=int(environ.get('PORT',5000)))