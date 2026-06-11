import streamlit as st
import sqlite3
import requests
import streamlit_authenticator as stauth
from datetime import datetime
import pandas as pd

# --- KONFIGURASI API WHATSAPP (Sinyal HTTP) ---
# Ganti URL dan Token sesuai dengan penyedia layanan gateway WA yang Anda gunakan
WA_API_URL = "https://api.wagateway.com/send-message" 
WA_TOKEN = "YOUR_API_TOKEN_HERE"

def kirim_notifikasi_wa(no_hp, pesan):
    """Fungsi untuk mengirim notifikasi WhatsApp menggunakan HTTP POST"""
    if not no_hp:
        return False
    
    # Format nomor HP agar berawalan 62 (standar Indonesia)
    if no_hp.startswith("0"):
        no_hp = "62" + no_hp[1:]
        
    payload = {
        "token": WA_TOKEN,
        "to": no_hp,
        "message": pesan
    }
    try:
        # Mengirimkan sinyal HTTP POST ke Gateway WhatsApp
        response = requests.post(WA_API_URL, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Gagal mengirim WA: {e}")
        return False

# --- UTILITAS DATABASE ---
def run_query(query, params=(), fetch=False):
    with sqlite3.connect('warga_apps.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        if fetch:
            return cursor.fetchall()

# --- AMBIL DATA USER UNTUK AUTENTIKASI ---
# Mengambil data kredensial dari database untuk dimasukkan ke sistem login
credentials = {"usernames": {}}
user_data_db = run_query("SELECT email, nama, password, role, no_hp FROM warga", fetch=True)

for email, nama, hashed_password, role, no_hp in user_data_db:
    credentials["usernames"][email] = {
        "name": nama,
        "password": hashed_password, # Password harus sudah di-hash di DB
        "logged_in": False
    }

# --- INISIALISASI STREAMLIT AUTHENTICATOR ---
authenticator = stauth.Authenticate(
    credentials,
    cookie_name="warga_app_cookie",
    key="signature_key_komplek",
    cookie_expiry_days=30
)

# --- HALAMAN LOGIN ---
st.set_page_config(page_title="Apps Warga Komplek", page_icon="🏡", layout="centered")

# Merender Form Login otomatis
name, authentication_status, username = authenticator.login('Login Aplikasi Warga', 'main')

if authentication_status == False:
    st.error('Username/Password salah. Silakan coba lagi.')
elif authentication_status == None:
    st.warning('Silakan masukkan username (email) dan password Anda.')
    
    # Tombol darurat/bantuan jika belum punya akun
    with st.expander("Belum punya akun atau lupa password?"):
        st.info("Silakan hubungi Pengurus Komplek (Pak RT) untuk didaftarkan email dan mendapatkan password default Anda.")

# --- JIKA BERHASIL LOGIN ---
elif authentication_status:
    # Cari tahu role dan nomor HP user yang sedang login
    user_info = run_query("SELECT role, no_hp FROM warga WHERE email=?", (username,), fetch=True)
    role = user_info[0][0] if user_info else "Warga"
    no_hp_user = user_info[0][1] if user_info else ""

    # Sidebar Utama
    st.sidebar.title(f"Halo, {name}! 👋")
    st.sidebar.write(f"Akses: **{role}**")
    authenticator.logout('Log Out', 'sidebar')
    st.sidebar.markdown("---")

    # Menu Navigasi
    menu = st.sidebar.radio("Pilih Menu:", ["📰 Berita Komplek", "💰 Iuran Komplek", "🕋 Tabungan Qurban", "👥 Data Anggota Warga"])

    # --- 1. FITUR BERITA & PENGUMUMAN (DENGAN WA BROADCAST DARURAT) ---
    if menu == "📰 Berita Komplek":
        st.header("📰 Berita & Pengumuman Komplek")
        
        if role == "Admin":
            with st.expander("➕ Tambah Pengumuman Baru"):
                judul = st.text_input("Judul Pengumuman")
                isi = st.text_area("Isi Pengumuman")
                is_darurat = st.checkbox("🚨 Tandai sebagai DARURAT (Kirim WhatsApp ke semua warga)")
                
                if st.button("Simpan & Terbitkan"):
                    if judul and isi:
                        run_query("INSERT INTO berita (tanggal, judul, isi) VALUES (?, ?, ?)", 
                                  (datetime.now().strftime("%Y-%m-%d"), judul, isi))
                        st.success("Berita berhasil diterbitkan!")
                        
                        # Jika dicentang darurat, kirim WA broadcast ke semua warga
                        if is_darurat:
                            daftar_wa_warga = run_query("SELECT no_hp, nama FROM warga WHERE no_hp IS NOT NULL", fetch=True)
                            pesan_wa = f"🚨 *PENGUMUMAN DARURAT KOMPLEK*\n\n*Judul:* {judul}\n*Isi:* {isi}\n\n_Mohon diperhatikan, Terima kasih._\n_- Pengurus Komplek_."
                            
                            sukses_kirim = 0
                            for no_hp, nama_warga in daftar_wa_warga:
                                if kirim_notifikasi_wa(no_hp, pesan_wa):
                                    sukses_kirim += 1
                            st.info(f"Broadcast Darurat dikirim ke {sukses_kirim} nomor warga.")
                        st.rerun()
        
        # Tampilkan Berita
        daftar_berita = run_query("SELECT tanggal, judul, isi FROM berita ORDER BY id_berita DESC", fetch=True)
        for tgl, jdl, idx in daftar_berita:
            st.subheader(jdl)
            st.caption(f"🗓️ Diposting pada: {tgl}")
            st.write(idx)
            st.markdown("---")

    # --- 2. FITUR IURAN KOMPLEK (DENGAN NOTIFIKASI WA SETELAH APPROVAL) ---
    elif menu == "💰 Iuran Komplek":
        st.header("💰 Manajemen Iuran Bulanan")
        
        if role == "Warga":
            st.subheader("Form Pembayaran Iuran")
            bulan = st.selectbox("Untuk Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            jumlah = st.number_input("Jumlah Transfer (Rp)", value=150000, step=50000)
            
            if st.button("Kirim Laporan Bayar"):
                run_query("INSERT INTO iuran (email_warga, jenis_iuran, periode_bulan, jumlah, status) VALUES (?, 'Komplek', ?, ?, 'Menunggu Konfirmasi')",
                          (username, bulan, jumlah))
                st.success("Laporan iuran berhasil dikirim! Menunggu pengecekan Admin.")
                
        elif role == "Admin":
            st.subheader("Persetujuan Iuran Warga")
            iuran_masuk = run_query("""
                SELECT i.id_iuran, i.email_warga, i.periode_bulan, i.jumlah, w.nama, w.no_hp 
                FROM iuran i 
                JOIN warga w ON i.email_warga = w.email 
                WHERE i.jenis_iuran='Komplek' AND i.status='Menunggu Konfirmasi'
            """, fetch=True)
            
            if not iuran_masuk:
                st.info("Belum ada laporan pembayaran baru dari warga.")
                
            for id_i, email, bln, jml, nama_w, no_hp_w in iuran_masuk:
                st.write(f"📩 **{nama_w}** ({bln}) - **Rp {jml:,.0f}**")
                if st.button(f"Setujui Pembayaran #{id_i}", key=id_i):
                    # Update Status di Database
                    run_query("UPDATE iuran SET status='Lunas' WHERE id_iuran=?", (id_i,))
                    
                    # Kirim WA otomatis ke warga bersangkutan
                    pesan_konfirmasi = f"Halo *{nama_w}*,\n\nPembayaran iuran Komplek Anda untuk bulan *{bln}* sebesar *Rp {jml:,.0f}* telah *DISETUJUI* dan dinyatakan *LUNAS*. \n\nTerima kasih atas partisipasinya! 🙏\n_- Pengurus Komplek_"
                    kirim_notifikasi_wa(no_hp_w, pesan_konfirmasi)
                    
                    st.success(f"Iuran {nama_w} Berhasil Disetujui & WA Terkirim!")
                    st.rerun()

    # --- 3. FITUR QURBAN ---
    elif menu == "🕋 Tabungan Qurban":
        st.header("🕋 Tabungan & Iuran Qurban")
        
        rows = run_query("SELECT jumlah FROM iuran WHERE email_warga=? AND jenis_iuran='Qurban' AND status='Lunas'", (username,), fetch=True)
        total_tabungan = sum([r[0] for r in rows])
        st.metric(label="Total Tabungan Qurban Anda saat ini", value=f"Rp {total_tabungan:,.0f}")
        
        with st.expander("➕ Setor Tabungan Qurban"):
            jml_qurban = st.number_input("Nominal Setoran (Rp)", value=500000, step=100000)
            if st.button("Konfirmasi Setoran"):
                run_query("INSERT INTO iuran (email_warga, jenis_iuran, periode_bulan, jumlah, status) VALUES (?, 'Qurban', ?, ?, 'Lunas')",
                          (username, datetime.now().strftime("%B %Y"), jml_qurban))
                
                # Kirim WA struk mandiri ke warga
                pesan_qurban = f"Halo *{name}*,\n\nSetoran tabungan Qurban Anda sebesar *Rp {jml_qurban:,.0f}* pada {datetime.now().strftime('%d/%m/%Y')} berhasil dicatat.\n*Total saldo qurban Anda saat ini:* Rp {total_tabungan + jml_qurban:,.0f}.\n\nSemoga berkah! 🙏"
                kirim_notifikasi_wa(no_hp_user, pesan_qurban)
                
                st.success("Setoran berhasil dicatat!")
                st.rerun()

    # --- 4. DATA WARGA & PEMBUATAN AKUN BARU ---
    elif menu == "👥 Data Anggota Warga":
        st.header("👥 Manajemen Anggota Warga")
        
        if role == "Admin":
            with st.expander("➕ Daftarkan Warga Baru & Buat Akun"):
                nama_w = st.text_input("Nama Lengkap")
                email_w = st.text_input("Email (untuk login)")
                no_hp_w = st.text_input("No. WhatsApp (contoh: 08123456789)")
                blok_w = st.text_input("Blok / No Rumah")
                password_w = st.text_input("Password Default Warga", type="password", value="warga123")
                
                if st.button("Simpan & Daftarkan"):
                    if nama_w and email_w and no_hp_w:
                        # Hashing password sebelum disimpan demi keamanan
                        hashed_password = stauth.Hasher([password_w]).generate()[0]
                        
                        try:
                            run_query("INSERT INTO warga (nama, email, no_hp, blok_rumah, password, role) VALUES (?, ?, ?, ?, ?, 'Warga')", 
                                      (nama_w, email_w, no_hp_w, blok_w, hashed_password))
                            st.success(f"Akun warga {nama_w} sukses dibuat!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Email sudah terdaftar sebelumnya!")
        
        # Tampilkan Tabel Warga
        data_warga = run_query("SELECT nama, email, no_hp, blok_rumah, role FROM warga", fetch=True)
        if data_warga:
            df = pd.DataFrame(data_warga, columns=["Nama Warga", "Email", "No. WA", "Blok/No Rumah", "Role"])
            st.dataframe(df, use_container_width=True)