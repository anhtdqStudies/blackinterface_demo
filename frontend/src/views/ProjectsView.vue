<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'

const store = useProjectsStore()
const router = useRouter()

const name = ref('')
const url = ref('opc.tcp://127.0.0.1:48050')

onMounted(() => store.fetchList())

async function create(): Promise<void> {
  if (await store.create(name.value, url.value)) {
    name.value = ''
    router.push('/station')
  }
}

async function open(id: number): Promise<void> {
  if (await store.open(id)) router.push('/station')
}

async function refresh(id: number): Promise<void> {
  if (await store.refresh(id)) router.push('/station')
}

function remove(id: number, projectName: string): void {
  if (window.confirm(`Xoá project "${projectName}" và snapshot của nó?`)) {
    store.remove(id)
  }
}

function short(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return isNaN(date.getTime()) ? iso : date.toLocaleString('vi-VN')
}
</script>

<template>
  <main class="page">
    <section class="card">
      <h2>Project mới</h2>
      <p class="dim">
        Trỏ vào một OneATS DataServer — sơ đồ được dựng tự động từ address space, không vẽ tay.
        Kết nối thành công sẽ lưu một snapshot: lần mở sau hiển thị ngay, không cần DataServer
        đang chạy.
      </p>
      <form @submit.prevent="create">
        <label>
          Tên project
          <input v-model="name" placeholder="ví dụ: Trạm 220kV Bình Hoà" required />
        </label>
        <label>
          Địa chỉ DataServer
          <input v-model="url" placeholder="opc.tcp://host:48050" required class="mono" />
        </label>
        <button type="submit" class="on" :disabled="store.busyId !== null">
          {{ store.busyId === -1 ? 'Đang kết nối…' : 'Kết nối và dựng sơ đồ' }}
        </button>
      </form>

      <p v-if="store.error" class="problem">
        <b>{{ store.error.code }}</b> — {{ store.error.message }}
      </p>
      <p v-else-if="store.lastLoadError" class="problem">
        Không đọc được nguồn: <code>{{ store.lastLoadError }}</code>
        <br />
        <span class="dim">
          Project đã được lưu — sửa mạng/địa chỉ rồi bấm «Tải lại từ nguồn» để thử lại.
        </span>
      </p>
    </section>

    <section class="card">
      <h2>Project đã có</h2>
      <p v-if="store.loading" class="dim">đang tải…</p>
      <p v-else-if="store.projects.length === 0" class="empty">
        Chưa có project nào. Tạo project đầu tiên ở trên.
      </p>
      <ul v-else class="list">
        <li v-for="p in store.projects" :key="p.id" :class="{ active: p.active }">
          <div class="who">
            <b>{{ p.name }}</b>
            <span v-if="p.active" class="tag">đang mở</span>
            <br />
            <code>{{ p.opcua_url }}</code>
          </div>
          <div class="what dim">
            <template v-if="p.has_snapshot">
              {{ p.model_name || '?' }} · ModelVersion {{ p.model_version ?? '?' }}
              <br />
              snapshot: {{ short(p.snapshot_saved_at) }}
            </template>
            <template v-else> chưa có snapshot — lần kết nối đầu chưa thành công </template>
          </div>
          <div class="actions">
            <button :disabled="store.busyId !== null || !p.has_snapshot" @click="open(p.id)">
              {{ store.busyId === p.id ? 'Đang mở…' : 'Mở' }}
            </button>
            <button :disabled="store.busyId !== null" @click="refresh(p.id)">
              Tải lại từ nguồn
            </button>
            <button :disabled="store.busyId !== null" @click="remove(p.id, p.name)">Xoá</button>
          </div>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.page {
  flex: 1;
  overflow: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px 20px;
}
.card h2 {
  margin: 0 0 4px;
  font-size: 14px;
}
.card > .dim {
  margin: 0 0 12px;
  font-size: 12px;
}

form {
  display: flex;
  gap: 12px;
  align-items: end;
  flex-wrap: wrap;
}
label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--dim);
}
input {
  background: var(--panel-2);
  color: var(--fg);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 6px 10px;
  font: inherit;
  min-width: 220px;
}
input:focus {
  outline: none;
  border-color: var(--accent);
}
input.mono {
  font-family: var(--mono);
  min-width: 280px;
}

.problem {
  margin: 12px 0 0;
  padding: 8px 12px;
  border: 1px solid var(--closed);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--closed) 14%, var(--panel));
  font-size: 12px;
}

.list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.list li {
  display: grid;
  grid-template-columns: 1.2fr 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-2);
}
.list li.active {
  border-color: var(--accent);
}
.who {
  font-size: 13px;
}
.what {
  font-size: 11px;
}
.tag {
  margin-left: 8px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--accent);
  color: #08111f;
  font-size: 10px;
  font-weight: 700;
}
.actions {
  display: flex;
  gap: 6px;
}
</style>
