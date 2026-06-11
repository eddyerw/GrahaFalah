import sqlite3

def init_db():
    conn = sqlite3.connect('warga_apps.db')
    cursor = conn.cursor()
    
    # 1. Tabel Warga
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warga (
            id_warga INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            no_hp TEXT,
            blok_rumah TEXT,
            role TEXT DEFAULT 'Warga'
        )
    ''')
    
    # 2. Tabel Berita
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS berita (
            id_berita INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            judul TEXT,
            isi TEXT
        )
    ''')
    
    # 3. Tabel Iuran Komplek & Qurban
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iuran (
            id_iuran INTEGER PRIMARY KEY AUTOINCREMENT,
            email_warga TEXT,
            jenis_iuran TEXT, -- 'Komplek' atau 'Qurban'
            periode_bulan TEXT,
            jumlah REAL,
            status TEXT DEFAULT 'Belum Bayar',
            bukti_transfer TEXT -- Berupa nama file/URL gambar
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database dan Tabel Berhasil Dibuat!")

if __name__ == '__main__':
    init_db()