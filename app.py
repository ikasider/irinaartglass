import sqlite3
import os
from flask import Flask, render_template, abort, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = '4hff3k2j1l0m9n8b7v6c5x4z3y2w1u0t'
ADMIN_PASSWORD = '64dh5@83g94j382k5!'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'artglass.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cost REAL NOT NULL,
            image TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1,
            description TEXT DEFAULT ''
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_categories (
            product_id INTEGER,
            category_name TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Неверный пароль!", 403
    return '''
        <form method="post">
            <input type="password" name="password" placeholder="Пароль администратора">
            <button type="submit">Войти</button>
        </form>
    '''

@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        description = request.form.get('description', '')
        available = 1 if request.form.get('available') == 'on' else 0
        selected_categories = request.form.getlist('categories')

        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'uploads/{filename}'

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute('''
                INSERT INTO products (name, cost, image, available, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, cost, image_path, available, description))

            product_id = cur.lastrowid

            for cat in selected_categories:
                cur.execute('INSERT INTO product_categories (product_id, category_name) VALUES (?, ?)',
                            (product_id, cat))

            conn.commit()
            conn.close()
            return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

def delete_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')


@app.route('/')
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM products WHERE available = 1 ORDER BY id DESC LIMIT 10')
    carousel_products = cur.fetchall()
    cur.execute('SELECT * FROM products ORDER BY available DESC, id DESC')
    all_products = cur.fetchall()
    conn.close()
    return render_template('index.html', carousel_items=carousel_products, items=all_products)

@app.route('/shop')
def shop():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM products WHERE available = 1 ORDER BY id DESC LIMIT 10')
    carousel_products = cur.fetchall()
    cur.execute('SELECT * FROM products ORDER BY available DESC, id DESC')
    all_products = cur.fetchall()
    conn.close()
    return render_template('shop.html', items=all_products, carousel_items=carousel_products)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/category/<cat_name>')
def show_category(cat_name):
    translations = {
        'earrings': {'ru': 'Серьги', 'en': 'Earrings', 'he': 'עгילים'},
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT p.* FROM products p
        JOIN product_categories pc ON p.id = pc.product_id
        WHERE pc.category_name = ?
        ORDER BY p.available DESC, p.id DESC
    ''', (cat_name,))
    category_items = cur.fetchall()
    conn.close()

    return render_template('category_view.html', items=category_items, titles=titles, title=cat_name)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM products ORDER BY id DESC')
    products_rows = cur.fetchall()
    
    products_with_cats = []
    for row in products_rows:
        product = dict(row)
        
        cur.execute('SELECT category_name FROM product_categories WHERE product_id = ?', (product['id'],))
        cats = cur.fetchall()
        product['categories_list'] = ", ".join([c['category_name'] for c in cats])
        
        products_with_cats.append(product)
        
    conn.close()
    return render_template('admin_dashboard.html', products=products_with_cats)

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        description = request.form.get('description', '')
        available = 1 if request.form.get('available') == 'on' else 0
        selected_categories = request.form.getlist('categories')

        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'uploads/{filename}'
        else:
            cur.execute('SELECT image FROM products WHERE id = ?', (product_id,))
            image_path = cur.fetchone()['image']

        cur.execute('''
            UPDATE products 
            SET name = ?, cost = ?, image = ?, available = ?, description = ?
            WHERE id = ?
        ''', (name, cost, image_path, available, description, product_id))

        cur.execute('DELETE FROM product_categories WHERE product_id = ?', (product_id,))
        for cat in selected_categories:
            cur.execute('INSERT INTO product_categories (product_id, category_name) VALUES (?, ?)',
                        (product_id, cat))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    cur.execute('SELECT category_name FROM product_categories WHERE product_id = ?', (product_id,))
    current_cats = [row['category_name'] for row in cur.fetchall()]

    conn.close()
    return render_template('edit_product.html', product=product, current_cats=current_cats)

@app.route('/admin/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/product/<int:product_id>')
def product(product_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product_data = cur.fetchone()
    conn.close()

    if product_data is None:
        abort(404)
    return render_template('product.html', item=product_data)

    return render_template('product.html',
                           name=product_data['name'],
                           cost=product_data['cost'],
                           image=product_data['image'])


if __name__ == '__main__':
    init_db()
    app.run(debug=True)