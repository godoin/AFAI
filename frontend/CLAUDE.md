# CLAUDE.md — Frontend

Context for Claude when working on the AF Builder frontend.

---

## Stack

- **Framework:** Vue 3 + Vite
- **Styling:** Tailwind CSS
- **State:** Pinia (global store)
- **Server state / HTTP:** Axios + Vue Query (or plain Axios with Pinia)
- **File handling:** vue-filepond or native drag-and-drop
- **Tables:** TanStack Table for Vue (or vue3-easy-data-table for simpler cases)
- **Routing:** Vue Router 4
- **Component style:** Composition API with `<script setup>` — no Options API

---

## Folder structure

```
frontend/
├── CLAUDE.md               ← You are here
├── index.html
├── vite.config.js
├── tailwind.config.js
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   └── index.js
│   ├── api/               ← All API calls to backend
│   │   └── afBuilder.js
│   ├── components/
│   │   ├── upload/        ← TagListUploader.vue, FormulaUploader.vue
│   │   ├── review/        ← AFPreviewTable.vue, ValidationReport.vue
│   │   ├── status/        ← JobProgress.vue, StepIndicator.vue
│   │   └── common/        ← BaseButton.vue, BaseModal.vue, BaseBadge.vue, Toast.vue
│   ├── pages/
│   │   ├── UploadPage.vue     ← Step 1: input files
│   │   ├── PreviewPage.vue    ← Step 2: review mapped structure
│   │   ├── ExecutePage.vue    ← Step 3: run & monitor
│   │   └── ReviewPage.vue     ← Step 4: BA validation & approve
│   ├── stores/
│   │   └── jobStore.js        ← Pinia store for job state
│   └── utils/
│       └── parseCSV.js
```

---

## Component conventions

```vue
<!-- All components use <script setup> + Composition API -->
<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  file: Object,
  onUpload: Function
})

const emit = defineEmits(['upload'])
</script>

<template>
  <!-- No inline styles — Tailwind only -->
  <!-- Conditional classes use :class binding -->
  <div :class="['base-class', isActive && 'active-class']">
    ...
  </div>
</template>
```

---

## UI/UX rules

- The BA is the primary user — keep it simple and clear
- Never auto-submit or auto-approve anything — every write action requires a button click
- Show a clear step indicator: Upload → Preview → Execute → Review → Approve
- All destructive or write actions must show a confirmation modal (BaseModal.vue) before proceeding
- Loading states must be visible — use spinners or progress bars for PI System operations (these can take time)
- Errors from the backend must be shown clearly with the specific step that failed
- The UI must work at 1280px+ width (used on office workstations)

---

## Pinia store pattern

```js
// src/stores/jobStore.js
import { defineStore } from 'pinia'

export const useJobStore = defineStore('job', {
  state: () => ({
    jobId: null,
    status: null,       // 'idle' | 'validating' | 'previewing' | 'executing' | 'reviewing' | 'approved' | 'rejected'
    tagList: null,
    formulaList: null,
    preview: null,
    report: null,
    error: null,
  }),
  actions: {
    async uploadTagList(file) { ... },
    async executeJob() { ... },
    async approveJob() { ... },
    async rejectJob(reason) { ... },
  }
})
```

---

## API layer

All backend calls go through src/api/afBuilder.js. Never call axios directly in components.

```js
// src/api/afBuilder.js
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL })

export const uploadTagList    = (file)          => api.post('/upload/tags', file)
export const uploadFormulas   = (file)          => api.post('/upload/formulas', file)
export const previewStructure = (jobId)         => api.get(`/jobs/${jobId}/preview`)
export const executeJob       = (jobId)         => api.post(`/jobs/${jobId}/execute`)
export const getJobStatus     = (jobId)         => api.get(`/jobs/${jobId}/status`)
export const approveJob       = (jobId)         => api.post(`/jobs/${jobId}/approve`)
export const rejectJob        = (jobId, reason) => api.post(`/jobs/${jobId}/reject`, { reason })
```

---

## Vue Router page map

```js
// src/router/index.js
const routes = [
  { path: '/',        component: () => import('@/pages/UploadPage.vue') },
  { path: '/preview', component: () => import('@/pages/PreviewPage.vue') },
  { path: '/execute', component: () => import('@/pages/ExecutePage.vue') },
  { path: '/review',  component: () => import('@/pages/ReviewPage.vue') },
]
```

Navigation between steps is gated — you cannot skip to /execute without a completed preview.

---

## What Claude should do here

- Use script setup and Composition API exclusively — no Options API
- Keep components small and single-purpose
- Always add loading and error states using ref or Pinia state
- Put all business logic in stores or utils — components are presentational only
- Do not add authentication complexity during POC — a simple login page is enough
- Do not add any action that bypasses the BA review step

---

## What Claude should NOT do here

- Do not use Options API (export default { data() {} }) — use script setup only
- Do not connect directly to PI System or the MCP server from the frontend
- Do not store the Anthropic API key anywhere in the frontend code
- Do not add features outside the 6-step flow (upload, validate, preview, execute, review, approve)
- Do not use localStorage for anything sensitive (job data, user credentials)
- Do not use Vuex — this project uses Pinia