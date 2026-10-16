// ESLint flat config (ESLint 9). Airbnb style for React + TypeScript,
// with Prettier turning off every formatting rule so the two never fight.
import js from '@eslint/js';
import globals from 'globals';
import reactRefresh from 'eslint-plugin-react-refresh';
import prettier from 'eslint-config-prettier';
import { configs, plugins } from 'eslint-config-airbnb-extended';

export default [
  { ignores: ['dist', 'node_modules', 'coverage'] },
  js.configs.recommended,
  plugins.stylistic,
  plugins.importX,
  plugins.react,
  plugins.reactA11y,
  plugins.reactHooks,
  plugins.typescriptEslint,
  ...configs.react.recommended,
  ...configs.react.typescript,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: globals.browser },
    plugins: { 'react-refresh': reactRefresh },
    rules: {
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // React 17+ JSX transform: no need to import React in every file.
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
    },
  },
  {
    // Tests and config files may import dev dependencies.
    files: ['**/*.test.{ts,tsx}', '*.config.{js,ts}'],
    rules: { 'import-x/no-extraneous-dependencies': ['error', { devDependencies: true }] },
  },
  prettier,
];
