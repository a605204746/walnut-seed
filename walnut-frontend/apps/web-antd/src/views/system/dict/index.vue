<script setup lang="ts">
import { Page } from '@vben/common-ui';

import DictTypePanel from './type/index.vue';
</script>

<template>
  <Page :auto-content-height="true">
    <DictTypePanel class="h-full overflow-hidden" />
  </Page>
</template>
