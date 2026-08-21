<script setup lang="ts">
import type { SelectEmits } from 'antdv-next';
import type { MessageType } from 'antdv-next/dist/message/interface';

import type { TenantOption } from '#/api';

import { computed, onMounted, ref, shallowRef, unref } from 'vue';
import { useRoute } from 'vue-router';

import { useAccess } from '@vben/access';
import { useTabs } from '@vben/hooks';
import { $t } from '@vben/locales';

import { Select, Spin } from 'antdv-next';
import { storeToRefs } from 'pinia';

import { useDictStore } from '#/store/dict';
import { useGlobalLoadingStore } from '#/store/loading';
import { useTenantStore } from '#/store/tenant';
import { request } from '#/utils/http';

/**
 * 动态切换租户(原api/system/tenant模块已删除 此处内联保留)
 * @param tenantId 租户ID
 */
function tenantDynamicToggle(tenantId: string) {
  return request.get<void>(`/system/tenant/dynamic/${tenantId}`);
}

/**
 * 清除动态切换租户
 */
function tenantDynamicClear() {
  return request.get<void>('/system/tenant/dynamic/clear');
}

const { hasAccessByRoles } = useAccess();

// 上一次选择的租户
const lastSelected = ref<string>();
// 当前选择租户的id
const selected = ref<string>();

const tenantStore = useTenantStore();
const { initTenant, setChecked } = tenantStore;
const { tenantEnable, tenantList } = storeToRefs(tenantStore);

const showToggle = computed<boolean>(() => {
  // 超级管理员 && 启用租户
  return hasAccessByRoles(['superadmin']) && unref(tenantEnable);
});

onMounted(async () => {
  // 没有超级管理员权限 不会调用接口
  if (!hasAccessByRoles(['superadmin'])) {
    return;
  }
  await initTenant();
});

const route = useRoute();
const { closeOtherTabs, refreshTab, closeAllTabs } = useTabs();

async function close(checked: boolean) {
  // store设置状态
  setChecked(checked);

  /**
   * 切换租户需要回到首页的页面 一般为带id的页面
   * 其他则直接刷新页面
   */
  if (route.meta.requireHomeRedirect) {
    await closeAllTabs();
  } else {
    // 先关闭再刷新 这里不用Promise.all()
    await closeOtherTabs();
    await refreshTab();
  }
}

const dictStore = useDictStore();
// 用于清理上一条message
const messageInstance = shallowRef<MessageType | null>();
// loading加载中效果
const loading = ref(false);
const loadingStore = useGlobalLoadingStore();
function setLoading(l: boolean) {
  loading.value = l;
  loadingStore.globalLoading = l;
}
/**
 * 选中租户的处理
 * @param tenantId tenantId
 * @param option 当前option
 */
const handleSelect: SelectEmits['select'] = async (
  tenantId: string,
  option: any,
) => {
  if (unref(lastSelected) === tenantId) {
    // createMessage.info('选择一致');
    return;
  }
  try {
    setLoading(true);

    await tenantDynamicToggle(tenantId);
    lastSelected.value = tenantId;

    // 关闭之前的message 只保留一条
    messageInstance.value?.();
    messageInstance.value = window.message.success(
      `${$t('component.tenantToggle.switch')} ${option.companyName}`,
    );

    close(true);
    // 需要放在宏队列处理 直接清空页面由于没有字典会有样式问题(标签变成unknown)
    setTimeout(() => dictStore.resetCache());
  } catch (error) {
    console.error(error);
  } finally {
    setLoading(false);
  }
};

async function handleClear() {
  try {
    setLoading(true);

    await tenantDynamicClear();
    // 关闭之前的message 只保留一条
    messageInstance.value?.();
    messageInstance.value = window.message.success(
      $t('component.tenantToggle.reset'),
    );

    lastSelected.value = '';
    close(false);
    // 需要放在宏队列处理 直接清空页面由于没有字典会有样式问题(标签变成unknown)
    setTimeout(() => dictStore.resetCache());
  } catch (error) {
    console.error(error);
  } finally {
    setLoading(false);
  }
}

/**
 * select搜索使用
 * @param input 输入内容
 * @param option 选项
 */
function filterOption(input: string, option: TenantOption) {
  return option.companyName.toLowerCase().includes(input.toLowerCase());
}
</script>

<template>
  <div v-if="showToggle" class="mr-[8px] hidden md:block">
    <Select
      v-model:value="selected"
      :disabled="loading"
      :field-names="{ label: 'companyName', value: 'tenantId' }"
      :filter-option="filterOption"
      :options="tenantList"
      :placeholder="$t('component.tenantToggle.placeholder')"
      allow-clear
      class="w-60"
      :popup-style="{ position: 'fixed' }"
      show-search
      @clear="handleClear"
      @select="handleSelect"
    >
      <template v-if="loading" #suffixIcon>
        <Spin size="small" spinning />
      </template>
    </Select>
  </div>
</template>

<style lang="scss" scoped>
// 当选中时 添加border样式
:deep(.ant-select-selector) {
  &:has(.ant-select-selection-item) {
    box-shadow: 0 0 10px hsl(var(--primary));
  }
}
</style>
