<script setup lang="ts">
/**
 * Nothing but the shell. Everything that used to be here — header markup, the
 * stream lifecycle, the error banner — moved into `app/layout/`, where each of
 * those three jobs has its own file and its own reason to change.
 */
import Shell from '@/app/layout/Shell.vue'
</script>

<template>
  <Shell />
</template>
