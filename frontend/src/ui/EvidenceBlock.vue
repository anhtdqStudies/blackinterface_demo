<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Evidence } from '@/api/client'
import Badge from '@/ui/Badge.vue'

/**
 * How far an answer can be trusted (ADR-0004, ADR-0013).
 *
 * The whole point is that this is *not* optional decoration. An answer with
 * caveats and an answer without them look identical on a screen unless
 * something insists on the difference, and by the time an operator notices, the
 * decision has been made. So: the caveats come first, before the provenance.
 *
 * The backend sends codes, not sentences — it is not the place to compose
 * Vietnamese. Translation happens here, where the operator's language is known.
 *
 * System palette throughout. A degraded answer is a fact about *our* software,
 * and must never borrow the red or green that mean something about the plant
 * (ADR-0014 section 2).
 */
const props = defineProps<{ evidence: Evidence; compact?: boolean }>()

const { t, d } = useI18n()

const limits = computed(() => props.evidence.limits ?? [])
const coverage = computed(() => props.evidence.coverage)

/**
 * Two grades, deliberately. "Incomplete" means we could not read part of what
 * was asked for; "caveat" means we read it and it is worth less than it looks.
 * Collapsing them would let a hole in the data hide behind a soft word.
 */
const tone = computed(() => (coverage.value && coverage.value.missing.length ? 'down' : 'warn'))

function when(iso: string): string {
  const at = new Date(iso)
  return isNaN(at.getTime()) ? iso : d(at, 'time')
}
</script>

<template>
  <section class="rounded-[var(--radius)] border border-line bg-panel-2 px-3 py-2 text-xs">
    <header class="mb-[6px] flex items-center gap-2">
      <span class="font-semibold tracking-[0.08em] text-dim uppercase">
        {{ t('evidence.title') }}
      </span>
      <Badge v-if="limits.length" :tone="tone">{{ limits.length }}</Badge>
      <Badge v-else tone="neutral">{{ t('evidence.clean') }}</Badge>
    </header>

    <ul v-if="limits.length" class="mb-2 list-none space-y-[3px] p-0">
      <li v-for="limit in limits" :key="limit.code" class="flex gap-2">
        <span class="text-sys-warn" aria-hidden="true">•</span>
        <span>
          {{ t(`limit.${limit.code}`) }}
          <span v-if="limit.count" class="text-dim">({{ limit.count }})</span>
          <span
            v-if="limit.subjects.length && !compact"
            class="block font-mono text-2xs break-all text-dim"
          >
            {{ limit.subjects.join(', ') }}
          </span>
        </span>
      </li>
    </ul>

    <dl class="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-[2px] text-dim">
      <dt>{{ t('evidence.coverage') }}</dt>
      <dd class="m-0 text-fg">
        {{ coverage?.resolved ?? 0 }} / {{ coverage?.requested ?? 0 }}
        {{ t('evidence.points') }}
      </dd>

      <dt>{{ t('evidence.source') }}</dt>
      <dd class="m-0 text-fg">
        {{ t(`sourceKind.${evidence.source.kind}`) }}
        <span v-if="evidence.model_version" class="text-dim">
          · ModelVersion {{ evidence.model_version }}
        </span>
      </dd>

      <dt>{{ t('evidence.at') }}</dt>
      <dd class="m-0 text-fg">{{ when(evidence.called_at) }}</dd>

      <template v-if="!compact">
        <dt>{{ t('evidence.tool') }}</dt>
        <dd class="m-0 font-mono text-fg">{{ evidence.tool }}({{ evidence.subject }})</dd>
      </template>
    </dl>
  </section>
</template>
