<script setup lang="ts">
import type { VbenFormProps } from '@vben/common-ui';

import type { VxeGridProps } from '#/adapter/vxe-table';
import type { DictData } from '#/api/system/dict/dict-data-model';
import type { DictType } from '#/api/system/dict/dict-type-model';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Popconfirm, Space } from 'antdv-next';

import { useVbenVxeGrid, vxeCheckboxChecked } from '#/adapter/vxe-table';
import {
  dictDataExport,
  dictDataList,
  dictDataRemove,
} from '#/api/system/dict/dict-data';
import { useBlobExport } from '#/utils/file/export';

import { columns, querySchema } from './data';
import dictDataItemModal from './dict-data-item-modal.vue';

const dictType = ref('');
const dictName = ref('');
const title = computed(() => `字典数据【${dictName.value}】`);
// 首次打开时表格随proxyConfig自动加载 第二次及以后打开手动reload
const isFirstOpen = ref(true);

const formOptions: VbenFormProps = {
  commonConfig: {
    labelWidth: 70,
    componentProps: {
      allowClear: true,
    },
  },
  schema: querySchema(),
  wrapperClass: 'grid-cols-1 md:grid-cols-2',
  handleReset: () => {
    tableApi.formApi.resetForm();
    tableApi.reload();
  },
};

const gridOptions: VxeGridProps = {
  checkboxConfig: {
    // 高亮
    highlight: true,
    // 翻页时保留选中状态
    reserve: true,
  },
  columns,
  height: 'auto',
  keepSource: true,
  minHeight: 300,
  pagerConfig: {},
  proxyConfig: {
    ajax: {
      query: async ({ page }, formValues = {}) => {
        return await dictDataList({
          pageNum: page.currentPage,
          pageSize: page.pageSize,
          dictType: dictType.value,
          ...formValues,
        });
      },
    },
  },
  rowConfig: {
    keyField: 'id',
  },
  id: 'system-dict-data-modal',
};

const [BasicTable, tableApi] = useVbenVxeGrid({
  formOptions,
  gridOptions,
});

const [BasicModal, modalApi] = useVbenModal({
  fullscreenButton: true,
  onOpened: async () => {
    if (isFirstOpen.value) {
      isFirstOpen.value = false;
      return;
    }
    // 切换了字典类型 重新加载数据
    await tableApi.reload();
  },
});

const [DictDataItemModal, itemModalApi] = useVbenModal({
  connectedComponent: dictDataItemModal,
});

/**
 * 打开指定字典类型的字典数据弹窗
 * @param row 字典类型行数据
 */
function open(row: DictType) {
  dictType.value = row.dictType;
  dictName.value = row.dictName;
  modalApi.open();
}
defineExpose({ open });

function handleAdd() {
  itemModalApi.setData({ dictType: dictType.value });
  itemModalApi.open();
}

async function handleEdit(record: DictData) {
  itemModalApi.setData({ dictType: dictType.value, id: record.id });
  itemModalApi.open();
}

async function handleDelete(row: DictData) {
  await dictDataRemove([row.id]);
  await tableApi.query();
}

function handleMultiDelete() {
  const rows = tableApi.grid.getCheckboxRecords();
  const ids = rows.map((row: DictData) => row.id);
  window.modal.confirm({
    title: '提示',
    okType: 'danger',
    content: `确认删除选中的${ids.length}条记录吗？`,
    onOk: async () => {
      await dictDataRemove(ids);
      await tableApi.query();
    },
  });
}

const { exportBlob, exportLoading, buildExportFileName } =
  useBlobExport(dictDataExport);
async function handleExport() {
  // 构建表单请求参数
  const formValues = await tableApi.formApi.getValues();
  // 文件名
  const fileName = buildExportFileName('字典数据');
  exportBlob({
    data: { ...formValues, dictType: dictType.value },
    fileName,
  });
}
</script>

<template>
  <BasicModal :title="title" class="w-[900px]">
    <BasicTable table-title="字典数据列表">
      <template #toolbar-tools>
        <Space>
          <a-button
            :disabled="!vxeCheckboxChecked(tableApi)"
            danger
            type="primary"
            v-access:code="['system:dict:remove']"
            @click="handleMultiDelete"
          >
            {{ $t('pages.common.delete') }}
          </a-button>
          <a-button
            v-access:code="['system:dict:export']"
            :loading="exportLoading"
            :disabled="exportLoading"
            @click="handleExport"
          >
            {{ $t('pages.common.export') }}
          </a-button>
          <a-button
            type="primary"
            v-access:code="['system:dict:add']"
            @click="handleAdd"
          >
            {{ $t('pages.common.add') }}
          </a-button>
        </Space>
      </template>
      <template #action="{ row }">
        <Space>
          <action-button
            v-access:code="['system:dict:edit']"
            @click.stop="handleEdit(row)"
          >
            {{ $t('pages.common.edit') }}
          </action-button>
          <Popconfirm
            placement="left"
            title="确认删除？"
            @confirm="handleDelete(row)"
          >
            <action-button
              danger
              v-access:code="['system:dict:remove']"
              @click.stop=""
            >
              {{ $t('pages.common.delete') }}
            </action-button>
          </Popconfirm>
        </Space>
      </template>
    </BasicTable>
    <DictDataItemModal @reload="tableApi.query()" />
  </BasicModal>
</template>
