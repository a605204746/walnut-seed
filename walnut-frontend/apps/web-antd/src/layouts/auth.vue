<script lang="ts" setup>
import { computed } from 'vue';

import { AuthPageLayout } from '@vben/layouts';
import { preferences, usePreferences } from '@vben/preferences';

import { ConfigProvider, theme } from 'antdv-next';

import { WalnutSlogan } from '#/components/walnut-slogan';
import { $t } from '#/locales';

const appName = computed(() => preferences.app.name);
const logo = computed(() => preferences.logo.source);
const logoDark = computed(() => preferences.logo.sourceDark);

const { isDark } = usePreferences();

/**
 * 登录页单独使用核桃品牌色（琥珀），
 * 嵌套 ConfigProvider 只作用于认证页，后台管理端仍跟随全局主题色。
 */
const authTheme = computed(() => ({
  algorithm: isDark.value ? [theme.darkAlgorithm] : [theme.defaultAlgorithm],
  token: {
    colorPrimary: isDark.value ? '#e8a752' : '#b4692e',
    colorLink: isDark.value ? '#e8a752' : '#b4692e',
  },
}));
</script>

<template>
  <ConfigProvider :theme="authTheme">
    <AuthPageLayout
      :app-name="appName"
      :logo="logo"
      :logo-dark="logoDark"
      :page-description="$t('authentication.pageDesc')"
      :page-title="$t('authentication.pageTitle')"
    >
      <!-- 自定义工具栏 -->
      <!-- <template #toolbar></template> -->
      <template #slogan>
        <WalnutSlogan class="animate-float" />
      </template>
    </AuthPageLayout>
  </ConfigProvider>
</template>
