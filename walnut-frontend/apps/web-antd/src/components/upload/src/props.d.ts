import type { UploadFile } from 'antdv-next';
import type { RcFile } from 'antdv-next/es/vc-upload/interface';

import type { UploadApi, UploadResult } from '#/api';

import { UploadChangeParam } from 'antdv-next';

export type UploadType = 'file' | 'image';

/**
 * 回显已有文件时的信息 后端无文件信息查询接口 仅能从url推导
 */
export interface UrlFileInfo {
  /** 原始文件名 可能为空(历史数据仅存url) */
  originalName?: string;
  /** 文件访问地址 */
  url: string;
}

/**
 * 自定义返回文件名/缩略图使用 泛型控制返回是否必填
 * type 为不同的来源 需要自行if判断
 */
export type CustomGetter<T extends string | undefined> = (
  cb:
    | { response: UrlFileInfo; type: 'info' }
    | { response: UploadResult; type: 'upload' },
) => T extends undefined ? string | undefined : string;

export interface BaseUploadProps {
  /**
   * 上传接口
   */
  api?: UploadApi;
  /**
   * 文件上传失败 是否从展示列表中删除
   * @default true
   */
  removeOnError?: boolean;
  /**
   * 上传成功 是否展示提示信息
   * @default true
   */
  showSuccessMsg?: boolean;
  /**
   * 删除文件前是否需要确认
   * @default false
   */
  removeConfirm?: boolean;
  /**
   * 同antdv参数
   */
  accept?: string;
  /**
   * 你可能使用的是application/pdf这种mime类型, 但是这样用户可能看不懂, 在这里自定义逻辑
   * @default 原始accept
   */
  acceptFormat?: ((accept: string) => string) | string;
  /**
   * 附带的请求参数
   */
  data?: any;
  /**
   * 最大上传图片数量
   * maxCount为1时 会被绑定为string而非string[]
   * @default 1
   */
  maxCount?: number;
  /**
   * 文件最大 单位M
   * @default 5
   */
  maxSize?: number;
  /**
   * 是否禁用
   * @default false
   */
  disabled?: boolean;
  /**
   * 是否显示文案 请上传不超过...
   * @default true
   */
  helpMessage?: boolean;
  /**
   * 是否支持多选文件，ie10+ 支持。开启后按住 ctrl 可选择多个文件。
   * @default false
   */
  multiple?: boolean;
  /**
   * 是否支持上传文件夹
   * @default false
   */
  directory?: boolean;
  /**
   * 是否支持拖拽上传
   * @default false
   */
  enableDragUpload?: boolean;
  /**
   * 自定义文件/图片预览逻辑 比如: 你可以改为下载
   * 图片上传默认为预览
   * 文件上传默认为window.open
   * @param file file
   */
  preview?: (file: UploadFile) => Promise<void> | void;
  /**
   * 是否在组件Unmounted时取消上传
   * @default true
   */
  abortOnUnmounted?: boolean;
  /**
   * 自定义文件名 需要区分两个接口的返回值
   */
  customFilename?: CustomGetter<string>;
  /**
   * 自定义缩略图 需要区分两个接口的返回值
   */
  customThumbUrl?: CustomGetter<undefined>;
}

export interface UploadEmits {
  (e: 'success', file: RcFile, response: UploadResult): void;
  (e: 'remove', file: UploadFile): void;
  (e: 'change', info: UploadChangeParam): void;
}
