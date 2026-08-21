/* eslint-disable @typescript-eslint/no-non-null-assertion */
import type { UploadChangeParam, UploadFile, UploadProps } from 'antdv-next';

import type { ModelRef } from 'vue';

import type {
  BaseUploadProps,
  CustomGetter,
  UploadEmits,
  UploadType,
} from './props';

import type { UploadResult } from '#/api';

import { computed, onUnmounted, ref, watch } from 'vue';

import { $t } from '@vben/locales';

import { Upload } from 'antdv-next';
import { isFunction, isString } from 'lodash-es';

/**
 * 图片预览hook
 * @returns 预览
 */
export function useImagePreview() {
  /**
   * 获取base64字符串
   * @param file 文件
   * @returns base64字符串
   */
  function getBase64(file: File) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.addEventListener('load', () => resolve(reader.result));
      reader.addEventListener('error', (error) => reject(error));
    });
  }

  // Modal可见
  const previewVisible = ref(false);
  // 预览的图片 url/base64
  const previewImage = ref('');

  function handleOpenChange(isOpen: boolean) {
    previewVisible.value = isOpen;
  }

  async function handlePreview(file: UploadFile) {
    if (!file) {
      return;
    }
    // 文件预览 取base64
    if (!file.url && !file.preview && file.originFileObj) {
      file.preview = (await getBase64(file.originFileObj)) as string;
    }
    // 这里不可能为空
    const url = file.url ?? '';
    previewImage.value = url || file.preview || '';
    previewVisible.value = true;
  }

  function handleAfterOpenChange(open: boolean) {
    if (!open) {
      previewVisible.value = false;
      previewImage.value = '';
    }
  }

  return {
    previewVisible,
    previewImage,
    handleOpenChange,
    handlePreview,
    handleAfterOpenChange,
  };
}

/**
 * 从文件访问地址推导展示文件名
 * @param url 文件访问地址
 * @returns 文件名
 */
function filenameFromUrl(url: string) {
  const lastSegment = url.split('/').filter(Boolean).pop() ?? '';
  return decodeURIComponent(lastSegment) || url;
}

/**
 * 图片上传和文件上传的通用hook
 * 后端上传接口仅返回 { url, original_filename } 无文件id
 * 因此组件双向绑定的值为逗号分隔的文件url
 * @param props 组件props
 * @param emit 事件
 * @param bindValue 双向绑定的url列表(逗号分隔)
 * @param uploadType 区分是文件还是图片上传
 * @returns hook
 */
export function useUpload(
  props: Readonly<BaseUploadProps>,
  emit: UploadEmits,
  bindValue: ModelRef<string>,
  uploadType: UploadType,
) {
  // 组件内部维护fileList
  const innerFileList = ref<UploadFile[]>([]);

  const acceptStr = computed(() => {
    // string类型
    if (isString(props.acceptFormat)) {
      return props.acceptFormat;
    }
    // 函数类型
    if (isFunction(props.acceptFormat)) {
      return props.acceptFormat(props.accept!);
    }
    // 默认 会对拓展名做处理
    return props.accept
      ?.split(',')
      .map((item) => {
        if (item.startsWith('.')) {
          return item.slice(1);
        }
        return item;
      })
      .join(', ');
  });

  /**
   * 自定义文件显示名称
   * @param cb callback
   * @returns 文件名
   */
  function transformFilename(cb: Parameters<CustomGetter<string>>[0]) {
    if (isFunction(props.customFilename)) {
      return props.customFilename(cb);
    }
    // 回显已有文件 从url推导
    if (cb.type === 'info') {
      return cb.response.originalName ?? filenameFromUrl(cb.response.url);
    }
    // 上传接口返回的原始文件名
    return cb.response.original_filename ?? filenameFromUrl(cb.response.url);
  }

  /**
   * 自定义缩略图
   * @param cb callback
   * @returns 缩略图地址
   */
  function transformThumbUrl(cb: Parameters<CustomGetter<undefined>>[0]) {
    if (isFunction(props.customThumbUrl)) {
      return props.customThumbUrl(cb);
    }
    // image 默认返回图片链接
    if (uploadType === 'image') {
      return cb.response.url;
    }
    // 文件默认返回空 走antd默认的预览图逻辑
    return undefined;
  }

  function handleChange(info: UploadChangeParam) {
    /**
     * 移除当前文件
     * @param currentFile 当前文件
     * @param currentFileList 当前所有文件list
     */
    function removeCurrentFile(
      currentFile: UploadChangeParam['file'],
      currentFileList: UploadChangeParam['fileList'],
    ) {
      if (props.removeOnError) {
        currentFileList.splice(currentFileList.indexOf(currentFile), 1);
      } else {
        currentFile.status = 'error';
      }
    }

    const { file: currentFile, fileList } = info;

    switch (currentFile.status) {
      // 上传成功 只是判断httpStatus 200 需要手动判断业务code
      case 'done': {
        if (!currentFile.response) {
          return;
        }
        // 获取返回结果 为customRequest的reslove参数
        // 只有success才会走到这里
        const { url } = currentFile.response as UploadResult;
        currentFile.url = url;
        // 无文件id 使用url作为唯一标识
        currentFile.uid = url;

        const cb = {
          type: 'upload',
          response: currentFile.response as UploadResult,
        } as const;

        currentFile.fileName = transformFilename(cb);
        currentFile.name = transformFilename(cb);
        currentFile.thumbUrl = transformThumbUrl(cb);
        // url添加 单个文件会被当做string
        if (props.maxCount === 1) {
          bindValue.value = url;
        } else {
          // 给默认值
          const validUrls = bindValue.value ? bindValue.value.split(',') : [];
          validUrls.push(url);
          bindValue.value = validUrls.join(',');
        }
        break;
      }
      // 上传失败 网络原因导致httpStatus 不等于200
      case 'error': {
        removeCurrentFile(currentFile, fileList);
      }
    }
    emit('change', info);
  }

  function handleRemove(currentFile: UploadFile) {
    function remove() {
      // fileList会自行处理删除 这里只需要处理绑定的url
      if (props.maxCount === 1) {
        bindValue.value = '';
      } else {
        const validUrls = bindValue.value ? bindValue.value.split(',') : [];
        const index = validUrls.indexOf(currentFile.uid);
        if (index !== -1) {
          validUrls.splice(index, 1);
          bindValue.value = validUrls.join(',');
        }
      }
      // 触发remove事件
      emit('remove', currentFile);
    }

    if (!props.removeConfirm) {
      remove();
      return true;
    }

    return new Promise<boolean>((resolve) => {
      window.modal.confirm({
        title: $t('pages.common.tip'),
        content: $t('component.upload.confirmDelete', [currentFile.name]),
        okButtonProps: { danger: true },
        centered: true,
        onOk() {
          resolve(true);
          remove();
        },
        onCancel() {
          resolve(false);
        },
      });
    });
  }

  /**
   * 上传前检测文件大小
   * 拖拽时候前置会有浏览器自身的accept校验 校验失败不会执行此方法
   * @param file file
   * @returns file | false
   */
  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    const isLtMax = file.size / 1024 / 1024 < props.maxSize!;
    if (!isLtMax) {
      window.message.error($t('component.upload.maxSize', [props.maxSize]));
      // 防止被加入文件列表 可以通过返回 Upload.LIST_IGNORE 实现。
      return Upload.LIST_IGNORE;
    }
    // 大坑 Safari不支持file-type库 去除文件类型的校验
    return file;
  };

  const abortList: (() => void)[] = [];
  /**
   * 自定义上传实现
   * @param info
   */
  const customRequest: UploadProps['customRequest'] = async (info) => {
    const { api } = props;
    if (!isFunction(api)) {
      console.warn('upload api must exist and be a function');
      return;
    }
    try {
      const apiInstance = api(info.file as File, {
        otherData: props?.data,
      });
      // 进度条事件
      apiInstance.onUpload((e) => {
        const percent = Math.trunc((e.loaded / e.total!) * 100);
        info.onProgress!({ percent });
      });
      abortList.push(apiInstance.abort);
      const res = await apiInstance;
      info.onSuccess!(res);
      if (props.showSuccessMsg) {
        window.message.success($t('component.upload.uploadSuccess'));
      }
      emit('success', info.file, res);
    } catch (error: any) {
      console.error(error);
      info.onError!(error);
    }
  };

  onUnmounted(() => {
    props.abortOnUnmounted && abortList.forEach((abort) => abort());
    abortList.length = 0;
  });

  /**
   * 这里默认只监听list地址变化 即重新赋值才会触发watch
   * immediate用于初始化触发
   */
  watch(
    () => bindValue.value,
    (value) => {
      if (!value) {
        // 清空绑定值时，同时清空innerFileList，避免外部使用时还能读取到
        innerFileList.value = [];
        return;
      }

      // 后端无文件信息查询接口 直接根据url回显
      const urls = value.split(',');
      innerFileList.value = urls.map((url) => {
        const cb = { type: 'info', response: { url } } as const;

        const fileitem: UploadFile = {
          uid: url,
          name: transformFilename(cb),
          fileName: transformFilename(cb),
          url,
          thumbUrl: transformThumbUrl(cb),
          status: 'done',
        };
        return fileitem;
      });
    },
    { immediate: true },
  );

  return {
    handleChange,
    handleRemove,
    beforeUpload,
    customRequest,
    innerFileList,
    acceptStr,
  };
}
