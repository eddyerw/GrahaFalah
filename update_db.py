import sqlite3
import streamlit_authenticator as stauth

def main():
    conn = sqlite3.connect('warga_apps.db')
    cursor = conn.cursor()

    # 1. Tambahkan kolom password ke tabel warga jika belum ada
    try:
        cursor.execute("ALTER TABLE warga ADD COLUMN password TEXT;")
    except sqlite3.OperationalError:
        pass # Kolom sudah ada, abaikan jika error

    # 2. Buat password enkripsi untuk Admin/Pak RT menggunakan fungsi hash terbaru
    # Menggunakan stauth.Hasher.hash() untuk versi terbaru
    password_asli = 'rahasiaRT123'
    hashed_password = stauth.Hasher.hash(password_asli)

    # 3. Masukkan data Pak RT sebagai admin pertama
    try:
        cursor.execute("""
            INSERT INTO warga (nama, email, no_hp, blok_rumah, role, password) 
            VALUES ('Pak Eddy', 'eddyerw@gmail.com', '08125064087', 'Blok B-8', 'Admin', ?)
        """, (hashed_password,))
        conn.commit()
        print("✅ Sukses: User Admin baru berhasil dibuat!")
    except sqlite3.IntegrityError:
        # Jika email sudah ada, kita update password dan role-nya saja
        cursor.execute("UPDATE warga SET password=?, role='Admin' WHERE email='pak.rt@email.com'", (hashed_password,))
        conn.commit()
        print("🔄 Sukses: Data Admin lama berhasil diperbarui dengan password baru!")

    conn.close()

if __name__ == '__main__':
    main()