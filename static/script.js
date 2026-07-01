// ============================================
// STATE - Data aplikasi
// ============================================
const state = {
    currentUser: null,        // User yang sedang login
    transactions: [],          // Semua transaksi user
    API_URL: window.location.origin + '/api'  // URL API
};

// ============================================
// NAVIGATION - Pindah halaman
// ============================================
function showPage(name) {
    // Sembunyikan semua halaman
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    // Tampilkan halaman yang dipilih
    document.getElementById('page-' + name).classList.add('active');
    window.scrollTo(0, 0);
}

// ============================================
// AUTH - Registrasi dan Login
// ============================================

// Tampilkan pesan flash
function flash(id, msg) {
    const el = document.getElementById(id);
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 4000);
}

// Registrasi
async function doRegister() {
    // 1. Ambil data dari form
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;

    // 2. Validasi
    if (!username || !email || !password) {
        return flash('reg-flash', '⚠️ Semua field wajib diisi!');
    }
    if (password.length < 6) {
        return flash('reg-flash', '⚠️ Password minimal 6 karakter!');
    }

    try {
        // 3. Kirim ke server
        const response = await fetch(state.API_URL + '/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        const data = await response.json();

        // 4. Proses respon
        if (response.ok) {
            toast('✅ Registrasi berhasil! Silakan login.');
            showPage('login');
        } else {
            flash('reg-flash', '❌ ' + data.error);
        }
    } catch (error) {
        flash('reg-flash', '❌ Terjadi kesalahan: ' + error.message);
    }
}

// Login
async function doLogin() {
    // 1. Ambil data dari form
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
        // 2. Kirim ke server
        const response = await fetch(state.API_URL + '/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();

        // 3. Proses respon
        if (response.ok) {
            // Simpan data user
            state.currentUser = data.user;
            document.getElementById('dash-username').textContent = data.user.username;
            
            // Set tanggal hari ini di form
            document.getElementById('tx-date').valueAsDate = new Date();
            
            // Pindah ke dashboard
            showPage('dashboard');
            
            // Muat transaksi
            await loadTransactions();
            renderAll();
        } else {
            flash('login-flash', '❌ ' + data.error);
        }
    } catch (error) {
        flash('login-flash', '❌ Terjadi kesalahan: ' + error.message);
    }
}

// Logout
function doLogout() {
    state.currentUser = null;
    state.transactions = [];
    showPage('home');
}

// ============================================
// TRANSACTIONS - Operasi Transaksi
// ============================================

// Muat transaksi dari server
async function loadTransactions() {
    if (!state.currentUser) return;
    try {
        const response = await fetch(state.API_URL + '/transactions/' + state.currentUser.id);
        state.transactions = await response.json();
    } catch (error) {
        toast('❌ Gagal memuat transaksi: ' + error.message);
    }
}

// Format Rupiah
function formatRupiah(n) {
    return 'Rp ' + n.toLocaleString('id-ID');
}

// Ambil tanggal hari ini
function getDateToday() {
    return new Date().toISOString().slice(0, 10);
}

// Tambah transaksi
async function addTransaction() {
    if (!state.currentUser) {
        toast('❌ Silakan login terlebih dahulu!');
        return;
    }

    // 1. Ambil data dari form
    const type = document.getElementById('tx-type').value;
    const date = document.getElementById('tx-date').value || getDateToday();
    const category = document.getElementById('tx-category').value.trim();
    const amount = parseFloat(document.getElementById('tx-amount').value);
    const description = document.getElementById('tx-desc').value.trim();

    // 2. Validasi
    if (!category) return toast('⚠️ Isi kategori dulu!');
    if (!amount || amount <= 0) return toast('⚠️ Jumlah harus lebih dari 0!');

    try {
        // 3. Kirim ke server
        const response = await fetch(state.API_URL + '/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: state.currentUser.id,
                type,
                date,
                category,
                amount,
                description
            })
        });
        const data = await response.json();

        // 4. Proses respon
        if (response.ok) {
            // Reset form
            document.getElementById('tx-category').value = '';
            document.getElementById('tx-amount').value = '';
            document.getElementById('tx-desc').value = '';
            
            toast('✅ Transaksi berhasil ditambahkan!');
            await loadTransactions();
            renderAll();
        } else {
            toast('❌ ' + data.error);
        }
    } catch (error) {
        toast('❌ Gagal menambah transaksi: ' + error.message);
    }
}

// Hapus transaksi
async function deleteTransaction(id) {
    if (!confirm('Yakin ingin menghapus transaksi ini?')) return;

    try {
        const response = await fetch(state.API_URL + '/transactions/' + id, {
            method: 'DELETE'
        });
        if (response.ok) {
            toast('🗑️ Transaksi dihapus!');
            await loadTransactions();
            renderAll();
        } else {
            toast('❌ Gagal menghapus transaksi');
        }
    } catch (error) {
        toast('❌ ' + error.message);
    }
}

// ============================================
// RENDER - Tampilkan data ke layar
// ============================================

// Render semua data
function renderAll() {
    // Hitung total pemasukan
    const income = state.transactions
        .filter(t => t.type === 'income')
        .reduce((s, t) => s + t.amount, 0);
    
    // Hitung total pengeluaran
    const expense = state.transactions
        .filter(t => t.type === 'expense')
        .reduce((s, t) => s + t.amount, 0);

    // Tampilkan di summary cards
    document.getElementById('sum-income').textContent = formatRupiah(income);
    document.getElementById('sum-expense').textContent = formatRupiah(expense);
    document.getElementById('sum-balance').textContent = formatRupiah(income - expense);
    
    // Render tabel
    renderTable();
}

// Render tabel transaksi
function renderTable() {
    const tbody = document.getElementById('tx-tbody');
    const fType = document.getElementById('filter-type').value;
    const fSearch = document.getElementById('filter-search').value.toLowerCase();

    // Filter transaksi
    let txs = state.transactions;
    if (fType !== 'all') txs = txs.filter(t => t.type === fType);
    if (fSearch) {
        txs = txs.filter(t =>
            t.category.toLowerCase().includes(fSearch) ||
            (t.description || '').toLowerCase().includes(fSearch)
        );
    }

    // Update badge jumlah
    document.getElementById('tx-count').textContent = txs.length;

    // Jika tidak ada transaksi
    if (!txs.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Tidak ada transaksi yang cocok.</td></tr>';
        return;
    }

    // Tampilkan transaksi
    tbody.innerHTML = txs.map(t => `
        <tr>
            <td>${t.date}</td>
            <td><span class="badge-${t.type}">${t.type === 'income' ? '📈 Masuk' : '📉 Keluar'}</span></td>
            <td>${escapeHtml(t.category)}</td>
            <td class="amt-${t.type}">${t.type === 'income' ? '+' : '-'} ${formatRupiah(t.amount)}</td>
            <td style="color:#7f8c9a">${escapeHtml(t.description || '-')}</td>
            <td><button class="btn-del" onclick="deleteTransaction(${t.id})">Hapus</button></td>
        </tr>
    `).join('');
}

// Escape HTML untuk keamanan (mencegah XSS)
function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ============================================
// PDF - Download Laporan
// ============================================
function downloadPDF(period) {
    if (!state.currentUser) {
        toast('❌ Silakan login terlebih dahulu!');
        return;
    }

    // Buka URL PDF di tab baru
    const url = state.API_URL + '/pdf/' + state.currentUser.id + '/' + period;
    window.open(url, '_blank');
    toast('📄 Sedang memproses laporan...');
}

// ============================================
// TOAST - Notifikasi
// ============================================
function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 3000);
}