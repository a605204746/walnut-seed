/**
 * 富文本内容中图片地址转换(兼容旧接口)
 *
 * 后端上传接口现直接返回可长期访问的文件url 图片src即为最终地址
 * 无需再做ossId -> url转换 此方法保留以兼容历史调用方 直接返回原内容
 * @param content 富文本内容
 * @returns string
 */
export async function contentWithOssIdTransform(content: string) {
  if (!content) {
    return null;
  }
  return content;
}
