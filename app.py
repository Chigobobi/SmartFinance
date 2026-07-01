from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os

# import dari file database 
from database import get_db, init_db
import sqlite3


# buat aplikasi flask
app = Flask(__name__)
CORS(app)

# initialisasi database saat aplikasi dimulai
init_db()
print("Aplikasi Flask siap dijalankan")

"""Buat route untuk kehalaman utama"""
@app.route('/')
def index():
    """Menampilkan halaman utama"""
    return render_template('index.html')

"""untuk memanggil asset folder"""
@app.route('/asset/<path:filename>')
def asset(filename):
    return send_from_directory('asset', filename)

"""Buat route untuk registrasi"""
@app.route('/api/register', methods=['POST'])
def register():
    """
    Mendaftarkan user baru
    URL: /api/register
    Method: POST
    Body (JSON): {username, email, password}
    """
    # ambil data dari request
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # validasi semua field harus diisi
    if not all([username, email, password]):
        return jsonify({'error':'semua wajib diisi'}),400
    
    # validasi password minimal 6 karakter
    if len(password) < 6 :
        return jsonify({'error':'password minimal 6 password'}),400
    
    # hash password (enkripsi)
    hashed_password = generate_password_hash(password)

    # simpan ke database
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, hashed_password)
        ) 
        conn.commit()
        return jsonify({'message': 'Registrasi berhasil'}),201

    except sqlite3.IntegrityError as e:
        # cek error
        if 'username' in str(e):
            return jsonify({'error': 'username sudah digunakan'}),400
        elif 'email' in str(e):
            return jsonify({'error':'email sudah digunakan'}),400
        return jsonify({'error':str(e)}),400
    
    finally:
        conn.close()

"""Buat route untuk login"""
@app.route('/api/login', methods=['POST'])
def login():
    """
    Login user
    URL: /api/login
    Method: POST
    Body (JSON): {username, password}
    """

    # ambil data
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # cari user di databae
    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute(
        'SELECT id, username, password FROM users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()

    # cek password (hash vs input)
    if user and check_password_hash(user['password'], password):
        return jsonify({
            'message': 'Login berhasil',
            'user': {'id':user['id'],
                    'username':user['username']}
        }),200
    else:
        return jsonify({'error':'username atau password salah'}),401
    
"""Buat route untuk transaksi"""
@app.route('/api/transactions/<int:user_id>', methods=['GET'])
def get_transactions(user_id):
    """
    Ambil semua transaksi milik user tertentu
    URL: /api/transactions/1
    Method: GET
    """
    conn = get_db()
    cursor = conn.cursor()
    transactions = cursor.execute(
        '''SELECT id, type, date, category, amount, description
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC''', (user_id,)
    ).fetchall()
    conn.close()

    # konversi ke list dictionary
    return jsonify([dict(row) for row in transactions])

# menambahkan transaksi baru
@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    """
    Tambah transaksi baru
    URL: /api/transactions
    Method: POST
    Body (JSON): {user_id, type, date, category, amount, description}
    """
    # ambil data
    data = request.json
    user_id = data.get('user_id')
    type = data.get('type')
    date = data.get('date')
    category = data.get('category')
    amount = data.get('amount')
    description = data.get('description', '')
    
    # 2. Validasi
    if not all([user_id, type, date, category, amount]):
        return jsonify({'error': 'Field wajib diisi!'}), 400
    
    if amount <= 0:
        return jsonify({'error': 'Jumlah harus lebih dari 0!'}), 400
    
    # 3. Simpan ke database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO transactions (user_id, type, date, category, amount, description)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, type, date, category, amount, description)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'message': 'Transaksi berhasil ditambahkan!', 'id': new_id}), 201

# menghapus transaksi baru
@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    """
    Hapus transaksi berdasarkan ID
    URL: /api/transactions/5
    Method: DELETE
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    
    if deleted:
        return jsonify({'message': 'Transaksi dihapus!'}), 200
    else:
        return jsonify({'error': 'Transaksi tidak ditemukan!'}), 404
    
""" Buat route untuk PDF"""
# app.py - lanjutan

@app.route('/api/pdf/<int:user_id>/<period>', methods=['GET'])
def generate_pdf(user_id, period):
    """
    Generate PDF laporan
    URL: /api/pdf/1/daily  atau /api/pdf/1/monthly
    Method: GET
    """
    # 1. Koneksi ke database
    conn = get_db()
    cursor = conn.cursor()
    
    # 2. Dapatkan nama user
    user = cursor.execute(
        'SELECT username FROM users WHERE id = ?', 
        (user_id,)
    ).fetchone()
    
    # 3. Filter transaksi berdasarkan periode
    today = datetime.now().strftime('%Y-%m-%d')
    
    if period == 'daily':
        # Laporan harian: hari ini
        transactions = cursor.execute(
            '''SELECT type, date, category, amount, description 
               FROM transactions 
               WHERE user_id = ? AND date = ? 
               ORDER BY date DESC''',
            (user_id, today)
        ).fetchall()
        title = f"Laporan Harian - {datetime.now().strftime('%d %B %Y')}"
    else:  # monthly
        # Laporan bulanan: bulan ini
        month_filter = datetime.now().strftime('%Y-%m')
        transactions = cursor.execute(
            '''SELECT type, date, category, amount, description 
               FROM transactions 
               WHERE user_id = ? AND date LIKE ? 
               ORDER BY date DESC''',
            (user_id, f'{month_filter}%')
        ).fetchall()
        title = f"Laporan Bulanan - {datetime.now().strftime('%B %Y')}"
    
    conn.close()
    
    # 4. Hitung total
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    balance = total_income - total_expense
    
    # 5. Buat PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    styles = getSampleStyleSheet()
    story = []
    
    # 5a. Judul
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a2740'),
        spaceAfter=30
    )
    story.append(Paragraph("💰 Aplikasi Keuangan", title_style))
    story.append(Spacer(1, 12))
    
    # 5b. Subtitle
    sub_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#555555'),
        spaceAfter=20
    )
    story.append(Paragraph(f"{title} - User: {user['username']}", sub_style))
    story.append(Spacer(1, 12))
    
    # 5c. Ringkasan (3 kotak)
    summary_data = [
        ['Total Pemasukan', f"Rp {total_income:,.0f}"],
        ['Total Pengeluaran', f"Rp {total_expense:,.0f}"],
        ['Saldo', f"Rp {balance:,.0f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#27ae60')),
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#e74c3c')),
        ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 5d. Tabel transaksi
    if transactions:
        table_data = [['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Deskripsi']]
        for t in transactions:
            type_label = '📈 Pemasukan' if t['type'] == 'income' else '📉 Pengeluaran'
            amount_str = f"+ Rp {t['amount']:,.0f}" if t['type'] == 'income' else f"- Rp {t['amount']:,.0f}"
            table_data.append([
                t['date'],
                type_label,
                t['category'],
                amount_str,
                t['description'] or '-'
            ])
        
        table = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 1.2*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2740')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("Tidak ada transaksi untuk periode ini.", styles['Normal']))
    
    # 5e. Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#aaaaaa'),
        alignment=1
    )
    story.append(Paragraph(
        f"Dicetak: {datetime.now().strftime('%d %B %Y %H:%M')} — Aplikasi Keuangan Multi-User",
        footer_style
    ))
    
    # 6. Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # 7. Kirim file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'laporan_{period}_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

""" jalankan aplikasi """
if __name__ == '__main__':
    app.run(debug=True, port=5000)