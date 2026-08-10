<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/lib/markdown'

const props = defineProps<{ source: string }>()

const html = computed(() => renderMarkdown(props.source))
</script>

<template>
  <!-- Sanitized in renderMarkdown() via DOMPurify before v-html. -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div v-if="html" class="chat-prose" v-html="html" />
</template>
