<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { apiRequest, setAuthToken } from './api'

const token = ref(localStorage.getItem('book_token') || '')
const currentUser = ref(null)
const books = ref([])
const borrows = ref([])
const loading = ref(false)
const message = ref('欢迎来到星辉图书馆管理系统')
const searchText = ref('')
const activeBookId = ref(null)

const loginForm = reactive({
  username: 'admin',
  password: 'admin123',
})

const bookForm = reactive({
  isbn: '',
  title: '',
  author: '',
  publisher: '',
  category: '',
  total_copies: 1,
  location: '',
})

const canWriteBooks = computed(() => currentUser.value?.permissions?.includes('books:write'))
const canReadBorrows = computed(() => currentUser.value?.permissions?.includes('borrows:read'))
const totalBooks = computed(() => books.value.length)
const totalCopies = computed(() => books.value.reduce((sum, book) => sum + book.total_copies, 0))
const availableCopies = computed(() => books.value.reduce((sum, book) => sum + book.available_copies, 0))
const borrowedCount = computed(() => borrows.value.filter((record) => record.status === 'borrowed').length)

onMounted(async () => {
  if (token.value) {
    setAuthToken(token.value)
    await bootstrap()
  }
})

async function bootstrap() {
  try {
    loading.value = true
    currentUser.value = await apiRequest('/auth/me')
    await Promise.all([loadBooks(), loadBorrows()])
    message.value = `欢迎回来，${currentUser.value.display_name || currentUser.value.username}`
  } catch (error) {
    logout()
    message.value = error.message
  } finally {
    loading.value = false
  }
}

async function login() {
  try {
    loading.value = true
    const result = await apiRequest('/auth/login', {
      method: 'POST',
      body: loginForm,
    })
    token.value = result.access_token
    localStorage.setItem('book_token', token.value)
    setAuthToken(token.value)
    await bootstrap()
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

function logout() {
  token.value = ''
  currentUser.value = null
  books.value = []
  borrows.value = []
  localStorage.removeItem('book_token')
  setAuthToken('')
}

async function loadBooks() {
  const query = searchText.value.trim()
  books.value = await apiRequest(`/books${query ? `?q=${encodeURIComponent(query)}` : ''}`)
}

async function loadBorrows() {
  if (!token.value) return
  borrows.value = await apiRequest('/borrows')
}

async function saveBook() {
  if (!canWriteBooks.value) {
    message.value = '当前账号没有图书写入权限'
    return
  }

  const payload = {
    ...bookForm,
    total_copies: Number(bookForm.total_copies || 0),
  }

  try {
    loading.value = true
    if (activeBookId.value) {
      await apiRequest(`/books/${activeBookId.value}`, {
        method: 'PATCH',
        body: payload,
      })
      message.value = '图书信息已更新'
    } else {
      await apiRequest('/books', {
        method: 'POST',
        body: payload,
      })
      message.value = '新图书已入库'
    }
    clearBookForm()
    await loadBooks()
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

function editBook(book) {
  activeBookId.value = book.id
  Object.assign(bookForm, {
    isbn: book.isbn,
    title: book.title,
    author: book.author,
    publisher: book.publisher,
    category: book.category,
    total_copies: book.total_copies,
    location: book.location,
  })
  message.value = `正在编辑《${book.title}》`
}

function clearBookForm() {
  activeBookId.value = null
  Object.assign(bookForm, {
    isbn: '',
    title: '',
    author: '',
    publisher: '',
    category: '',
    total_copies: 1,
    location: '',
  })
}

async function deleteBook(book) {
  if (!window.confirm(`确定要删除《${book.title}》吗？`)) return
  try {
    await apiRequest(`/books/${book.id}`, { method: 'DELETE' })
    message.value = '图书已移出馆藏'
    await loadBooks()
  } catch (error) {
    message.value = error.message
  }
}

async function borrowBook(book) {
  try {
    await apiRequest('/borrows', {
      method: 'POST',
      body: { book_id: book.id },
    })
    message.value = `已借阅《${book.title}》`
    await Promise.all([loadBooks(), loadBorrows()])
  } catch (error) {
    message.value = error.message
  }
}

async function returnBook(record) {
  try {
    await apiRequest(`/borrows/${record.id}/return`, { method: 'POST' })
    message.value = '还书成功'
    await Promise.all([loadBooks(), loadBorrows()])
  } catch (error) {
    message.value = error.message
  }
}

function bookTitle(bookId) {
  return books.value.find((book) => book.id === bookId)?.title || `图书 #${bookId}`
}
</script>

<template>
  <main class="app-shell">
    <section v-if="!currentUser" class="login-stage">
      <div class="orb orb-a"></div>
      <div class="orb orb-b"></div>
      <div class="login-card">
        <div class="brand-mark">LB</div>
        <p class="eyebrow">Luminous Library</p>
        <h1>星辉图书馆</h1>
        <p class="login-copy">一站式管理馆藏、借阅与权限，让图书管理像星图一样清晰。</p>

        <form class="login-form" @submit.prevent="login">
          <label>
            用户名
            <input v-model="loginForm.username" autocomplete="username" />
          </label>
          <label>
            密码
            <input v-model="loginForm.password" type="password" autocomplete="current-password" />
          </label>
          <button class="primary-button" :disabled="loading">
            {{ loading ? '正在进入...' : '进入系统' }}
          </button>
        </form>
        <p class="hint">默认管理员：admin / admin123</p>
        <p class="message">{{ message }}</p>
      </div>
    </section>

    <section v-else class="dashboard">
      <aside class="sidebar">
        <div class="logo-block">
          <div class="brand-mark small">LB</div>
          <div>
            <strong>星辉图书馆</strong>
            <span>Library Console</span>
          </div>
        </div>

        <nav class="nav-list">
          <a class="active">总览</a>
          <a>馆藏图书</a>
          <a>借阅记录</a>
          <a>权限中心</a>
        </nav>

        <div class="profile-card">
          <span>当前用户</span>
          <strong>{{ currentUser.display_name || currentUser.username }}</strong>
          <p>{{ currentUser.roles.join(' / ') }}</p>
          <button class="ghost-button" @click="logout">退出登录</button>
        </div>
      </aside>

      <section class="content">
        <header class="hero-panel">
          <div>
            <p class="eyebrow">Book Management System</p>
            <h1>馆藏中枢控制台</h1>
            <p>{{ message }}</p>
          </div>
          <button class="shine-button" @click="loadBooks">刷新数据</button>
        </header>

        <section class="stats-grid">
          <article class="stat-card">
            <span>图书种类</span>
            <strong>{{ totalBooks }}</strong>
          </article>
          <article class="stat-card gold">
            <span>馆藏总册</span>
            <strong>{{ totalCopies }}</strong>
          </article>
          <article class="stat-card cyan">
            <span>可借册数</span>
            <strong>{{ availableCopies }}</strong>
          </article>
          <article class="stat-card rose">
            <span>我的借阅</span>
            <strong>{{ borrowedCount }}</strong>
          </article>
        </section>

        <section class="workspace">
          <div class="books-panel glass-panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Collection</p>
                <h2>馆藏图书</h2>
              </div>
              <form class="search-box" @submit.prevent="loadBooks">
                <input v-model="searchText" placeholder="搜索书名、作者、ISBN、分类" />
                <button>查询</button>
              </form>
            </div>

            <div class="book-list">
              <article v-for="book in books" :key="book.id" class="book-card">
                <div class="book-cover">
                  <span>{{ book.category || 'LIB' }}</span>
                </div>
                <div class="book-info">
                  <strong>{{ book.title }}</strong>
                  <p>{{ book.author }} · {{ book.publisher || '未知出版社' }}</p>
                  <div class="meta-row">
                    <span>ISBN {{ book.isbn }}</span>
                    <span>{{ book.location || '未设置位置' }}</span>
                  </div>
                  <div class="stock-bar">
                    <i :style="{ width: `${book.total_copies ? (book.available_copies / book.total_copies) * 100 : 0}%` }"></i>
                  </div>
                </div>
                <div class="book-actions">
                  <span class="stock">{{ book.available_copies }}/{{ book.total_copies }} 可借</span>
                  <button class="soft-button" :disabled="book.available_copies <= 0" @click="borrowBook(book)">借阅</button>
                  <button v-if="canWriteBooks" class="soft-button" @click="editBook(book)">编辑</button>
                  <button v-if="canWriteBooks" class="danger-button" @click="deleteBook(book)">删除</button>
                </div>
              </article>
            </div>
          </div>

          <aside class="side-stack">
            <form class="glass-panel book-form" @submit.prevent="saveBook">
              <p class="eyebrow">Curator</p>
              <h2>{{ activeBookId ? '编辑图书' : '新书入库' }}</h2>
              <input v-model="bookForm.isbn" placeholder="ISBN" :disabled="!canWriteBooks" />
              <input v-model="bookForm.title" placeholder="书名" :disabled="!canWriteBooks" />
              <input v-model="bookForm.author" placeholder="作者" :disabled="!canWriteBooks" />
              <input v-model="bookForm.publisher" placeholder="出版社" :disabled="!canWriteBooks" />
              <input v-model="bookForm.category" placeholder="分类" :disabled="!canWriteBooks" />
              <input v-model.number="bookForm.total_copies" type="number" min="0" placeholder="总册数" :disabled="!canWriteBooks" />
              <input v-model="bookForm.location" placeholder="馆藏位置" :disabled="!canWriteBooks" />
              <div class="form-actions">
                <button class="primary-button" :disabled="!canWriteBooks">{{ activeBookId ? '保存修改' : '新增图书' }}</button>
                <button type="button" class="ghost-button" @click="clearBookForm">清空</button>
              </div>
              <p v-if="!canWriteBooks" class="hint">当前角色只能查看和借阅，不能维护馆藏。</p>
            </form>

            <div class="glass-panel borrow-panel">
              <div class="panel-heading compact">
                <div>
                  <p class="eyebrow">{{ canReadBorrows ? 'Borrow Center' : 'My Borrows' }}</p>
                  <h2>借阅记录</h2>
                </div>
                <button class="ghost-button" @click="loadBorrows">刷新</button>
              </div>
              <div class="borrow-list">
                <article v-for="record in borrows" :key="record.id" class="borrow-item">
                  <div>
                    <strong>{{ bookTitle(record.book_id) }}</strong>
                    <span>{{ record.borrowed_at }}</span>
                  </div>
                  <button
                    v-if="record.status === 'borrowed'"
                    class="soft-button"
                    @click="returnBook(record)"
                  >
                    还书
                  </button>
                  <span v-else class="returned">已归还</span>
                </article>
              </div>
            </div>
          </aside>
        </section>
      </section>
    </section>
  </main>
</template>
