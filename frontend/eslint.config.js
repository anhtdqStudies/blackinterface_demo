import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import prettier from 'eslint-config-prettier'

// ESLint checks correctness, Prettier owns formatting. `prettier` goes last and
// switches off every stylistic rule so the two never disagree - otherwise
// `npm run format` and `npm run lint` fight and neither can be a gate.
export default [
  { ignores: ['dist/**', 'node_modules/**', 'src/api/schema.d.ts', 'src/ui/*/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  ...vueTsEslintConfig(),
  prettier,
  {
    rules: {
      // The generated API types are the source of truth; anything the backend
      // does not describe should be an explicit decision, not an implicit any.
      '@typescript-eslint/no-explicit-any': 'error',
      'vue/multi-word-component-names': 'off',
    },
  },
]
