# database.py
import sqlite3
from datetime import datetime

# nama file database
DB_NAME = 'keuangan.db'

def get_db():
    """
    Membuat koneksi
    """
    # Koneksi ke database SQLite
    conn = sqlite3.connect(DB_NAME)
    # row_factory membuat hasil query bisa diakses seperti dictionary
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    inisialisasi database - membuat tabel jika belum ada
    """
    print("menginisialisasi database")

    # dapatkan koneksi
    conn = get_db()
    cursor = conn.cursor()

    # buat tabel users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print('Tabel users sudah dibuat')

    # buat tabel transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('income', 'expense')) NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)
    ''')
    print('Tabel transaction sudah dibuat')

    # simpan perubahan
    conn.commit()
    conn.close()
    print('database siap diinisialisasikan')

    """ 
    id = INTEGER = ID unik/otomatis bertambah
    username = TEXT UNIQUE = nama pengguna tidak boleh sama
    crated_at = TIMESTAMP = waktu registrasi/waktu input
    amount = REAL = Jumlah uang
    FOREIGN KEY = menghubungkan transaksi ke user yang membuatnya
    ON DELETE CASCADE = jika user dihapus, transaksinya ikut terhapus
    """