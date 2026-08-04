<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useStationStore } from '@/stores/station'

const store = useStationStore()
onMounted(() => store.load())
</script>

<template>
  <div class="shell">
    <header>
      <RouterLink to="/station" class="brand">BLACK INTERFACE</RouterLink>

      <span v-if="store.station" class="meta">
        <b>{{ store.station.name }}</b>
        · ModelVersion <b>{{ store.station.model_version ?? '?' }}</b> ·
        {{ store.station.bay_count }} ngăn · {{ store.station.device_count }} thiết bị · nguồn
        <b>{{ store.station.source }}</b>
        <template v-if="store.station.load_seconds != null">
          · dựng trong <b>{{ store.station.load_seconds.toFixed(2) }}s</b>
        </template>
      </span>
      <span v-else-if="store.loading" class="meta">đang tải…</span>

      <nav>
        <RouterLink to="/station">Sơ đồ</RouterLink>
        <RouterLink to="/issues">
          Cảnh báo
          <span v-if="store.issues.length" class="badge" :class="{ bad: store.errorCount }">
            {{ store.issues.length }}
          </span>
        </RouterLink>
      </nav>

      <button :disabled="store.reloading" @click="store.reload()">
        {{ store.reloading ? 'Đang tải lại…' : 'Tải lại từ nguồn' }}
      </button>
    </header>

    <p v-if="store.error" class="error">
      <b>{{ store.error.code }}</b> — {{ store.error.message }}
    </p>

    <RouterView />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}

header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}

.brand {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--fg);
  text-decoration: none;
}

.meta {
  color: var(--dim);
  font-size: 12px;
}
.meta b {
  color: var(--fg);
  font-weight: 600;
}

nav {
  margin-left: auto;
  display: flex;
  gap: 14px;
}
nav a {
  color: var(--dim);
  text-decoration: none;
  font-size: 12px;
}
nav a.router-link-active {
  color: var(--fg);
}

.badge {
  display: inline-block;
  min-width: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--intermediate);
  color: #1a1200;
  font-size: 10px;
  font-weight: 700;
  text-align: center;
}
.badge.bad {
  background: var(--closed);
  color: #fff;
}

.error {
  margin: 0;
  padding: 8px 16px;
  background: color-mix(in srgb, var(--closed) 18%, var(--bg));
  border-bottom: 1px solid var(--closed);
  font-size: 12px;
}
</style>
