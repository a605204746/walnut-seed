import type { FormSchemaGetter } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';

import { DictEnum } from '@vben/constants';
import { getPopupContainer } from '@vben/utils';

import { Tag } from 'antdv-next';

import { tagSelectOptions, tagTypes } from '#/components/dict';
import { getDictOptions } from '#/utils/dict';
import { renderDict } from '#/utils/render';

export const querySchema: FormSchemaGetter = () => [
  {
    component: 'Input',
    fieldName: 'dictLabel',
    label: '字典标签',
  },
];

export const columns: VxeGridProps['columns'] = [
  { type: 'checkbox', width: 60 },
  {
    title: '字典标签',
    field: 'dictLabel',
  },
  {
    title: '字典键值',
    field: 'dictValue',
  },
  {
    title: '字典排序',
    field: 'dictSort',
    width: 90,
  },
  {
    title: '是否默认',
    field: 'isDefault',
    width: 100,
    slots: {
      default: ({ row }) => {
        return renderDict(row.isDefault, DictEnum.SYS_YES_NO);
      },
    },
  },
  {
    title: '回显样式',
    field: 'listClass',
    width: 150,
    slots: {
      default: ({ row }) => {
        const listClass = row.listClass || '';
        if (!listClass) {
          return <span>-</span>;
        }
        const tagType = tagTypes[listClass];
        // 预设样式显示预设label 自定义颜色直接作为tag颜色
        return (
          <Tag color={tagType?.color ?? listClass}>
            {tagType?.label ?? listClass}
          </Tag>
        );
      },
    },
  },
  {
    title: '备注',
    field: 'remark',
  },
  {
    title: '创建时间',
    field: 'createTime',
  },
  {
    field: 'action',
    fixed: 'right',
    slots: { default: 'action' },
    title: '操作',
    resizable: false,
    width: 'auto',
  },
];

export const modalSchema: FormSchemaGetter = () => [
  {
    component: 'Input',
    dependencies: {
      show: () => false,
      triggerFields: [''],
    },
    fieldName: 'id',
    label: 'id',
  },
  {
    component: 'Input',
    fieldName: 'dictLabel',
    label: '字典标签',
    rules: 'required',
  },
  {
    component: 'Input',
    fieldName: 'dictValue',
    label: '字典键值',
    rules: 'required',
  },
  {
    component: 'InputNumber',
    defaultValue: 0,
    fieldName: 'dictSort',
    label: '字典排序',
    rules: 'required',
  },
  {
    component: 'RadioGroup',
    componentProps: {
      buttonStyle: 'solid',
      options: getDictOptions(DictEnum.SYS_YES_NO),
      optionType: 'button',
    },
    defaultValue: 'N',
    fieldName: 'isDefault',
    label: '是否默认',
    rules: 'required',
  },
  {
    component: 'Select',
    componentProps: {
      allowClear: true,
      getPopupContainer,
      options: tagSelectOptions(),
    },
    fieldName: 'listClass',
    help: 'DictTag组件表格回显样式',
    label: '回显样式',
  },
  {
    component: 'Input',
    fieldName: 'cssClass',
    help: '自定义css类名',
    label: '样式属性',
  },
  {
    component: 'Textarea',
    fieldName: 'remark',
    label: '备注',
  },
];
