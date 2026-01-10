import os
from flask import Flask, render_template, abort, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import psycopg2  # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IS_VERCEL = "VERCEL" in os.environ or "VERCEL_ENV" in os.environ
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    import sys
    print("⚠️  ВНИМАНИЕ: DATABASE_URL не установлена в переменных окружения!", file=sys.stderr)
    print("Установите переменную окружения DATABASE_URL с URL подключения к Supabase", file=sys.stderr)
    if IS_VERCEL:
        raise ValueError("DATABASE_URL обязательна для работы на Vercel!")

if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.secret_key = '4hff3k2j1l0m9n8b7v6c5x4z3y2w1u0t' 
ADMIN_PASSWORD = '3311973'

def get_db_connection():
    """Получение подключения к PostgreSQL (Supabase)"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не установлена! Установите переменную окружения.")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    except psycopg2.OperationalError:
        conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Создание таблицы products в PostgreSQL/Supabase"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            cost REAL NOT NULL,
            image TEXT NOT NULL,
            available BOOLEAN NOT NULL DEFAULT TRUE,
            description TEXT DEFAULT '',
            category TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session.permanent = True  
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Неверный пароль!", 403
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        description = request.form.get('description', '')
        available = request.form.get('available') == 'on'
        category = request.form.get('category', '')

        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'uploads/{filename}'

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO products (name, cost, image, available, description, category)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (name, cost, image_path, available, description, category))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    selected_cat = request.args.get('category')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if selected_cat:
        cur.execute('SELECT * FROM products WHERE category = %s ORDER BY id DESC', (selected_cat,))
    else:
        cur.execute('SELECT * FROM products ORDER BY id DESC')
    products_rows = cur.fetchall()
    products_list = []
    for row in products_rows:
        product = dict(row)
        product['categories_list'] = product.get('category', '') 
        products_list.append(product)   
    cur.close()
    conn.close()
    return render_template('admin_dashboard.html', products=products_list)

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        description = request.form.get('description', '')
        available = request.form.get('available') == 'on'
        category = request.form.get('category', '')

        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'uploads/{filename}'
        else:
            cur.execute('SELECT image FROM products WHERE id = %s', (product_id,))
            result = cur.fetchone()
            image_path = result['image'] if result else ''

        cur.execute('''
            UPDATE products 
            SET name = %s, cost = %s, image = %s, available = %s, description = %s, category = %s
            WHERE id = %s
        ''', (name, cost, image_path, available, description, category, product_id))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('edit_product.html', product=product, current_cats=[product['category']] if product else [])

@app.route('/admin/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT image FROM products WHERE id = %s', (product_id,))
    product = cur.fetchone()
    if product:
        # На Vercel файлы могут быть в /tmp/uploads
        if IS_VERCEL and product['image'].startswith('uploads/'):
            image_path = os.path.join(UPLOAD_FOLDER, os.path.basename(product['image']))
        else:
            image_path = os.path.join(app.root_path, 'static', product['image'])
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except: pass
        cur.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE available = TRUE ORDER BY id DESC LIMIT 10')
    carousel_products = cur.fetchall()
    cur.execute('SELECT * FROM products ORDER BY available DESC, id DESC')
    all_products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', carousel_items=carousel_products, items=all_products)

@app.route('/shop')
def shop():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE available = TRUE ORDER BY id DESC LIMIT 10')
    carousel_products = cur.fetchall()
    cur.execute('SELECT * FROM products ORDER BY available DESC, id DESC')
    all_products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('shop.html', items=all_products, carousel_items=carousel_products)

@app.route('/category/<cat_name>')
def show_category(cat_name):
    translations = {
        'earrings': {'ru': 'Серьги', 'en': 'Earrings', 'he': 'עגילים'},
        'pendants': {'ru': 'Подвески', 'en': 'Pendants', 'he': 'תליון'},
        'brooches': {'ru': 'Броши', 'en': 'Brooches', 'he': 'סיכות'},
        'rings': {'ru': 'Кольца', 'en': 'Rings', 'he': 'טבעות'},
        'necklaces': {'ru': 'Ожерелья', 'en': 'Necklaces', 'he': 'שרשראות'},
        'bracelets': {'ru': 'Браслеты', 'en': 'Bracelets', 'he': 'צמידים'},
        'chockers': {'ru': 'Чокеры', 'en': 'Chokers', 'he': 'צמידי צוואר'},
        'chains': {'ru': 'Цепочки', 'en': 'Chains', 'he': 'שרשראות'},
        'glassorbs': {'ru': 'Дутыши', 'en': 'Glass Orbs', 'he': 'כדורי זכוכית'},
        'pb': {'ru': 'Пандора', 'en': 'Pandora', 'he': 'פנדורה'},
        'sets': {'ru': 'Наборы', 'en': 'Sets', 'he': 'סטים'},
        'dread-beads': {'ru': 'Дреды', 'en': 'Dread Beads', 'he': 'חרוזי דרד'},
        'historical-beads': {'ru': 'Исторические', 'en': 'Historical Beads', 'he': 'חרוזים היסטוריים'},
        'key-chains': {'ru': 'Брелоки', 'en': 'Key Chains', 'he': 'מחזיקי מפתחות'},
        'sale': {'ru': 'Скидки', 'en': 'Sale', 'he': 'מבצע'}
    }
    titles = translations.get(cat_name, {'ru': cat_name, 'en': cat_name, 'he': cat_name})
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE category = %s ORDER BY available DESC, id DESC', (cat_name,))
    category_items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('category_view.html', items=category_items, titles=titles, title=cat_name)

@app.route('/product/<int:product_id>')
def product(product_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product_data = cur.fetchone()
    cur.close()
    conn.close()
    if product_data is None:
        abort(404)
    return render_template('product.html', item=product_data)

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/gallery')
def gallery(): return render_template('gallery.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

# Эндпоинт для отдачи загруженных изображений на Vercel
if IS_VERCEL:
    @app.route('/static/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

# Инициализация базы данных при старте приложения
init_db()

if __name__ == '__main__':
    app.run(debug=True)