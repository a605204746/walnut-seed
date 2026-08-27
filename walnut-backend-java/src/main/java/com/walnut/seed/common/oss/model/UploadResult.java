package com.walnut.seed.common.oss.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 文件上传结果
 *
 * @author deepin_sir
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UploadResult {

    /**
     * 文件可访问的 URL
     */
    private String url;

    /**
     * 原始文件名
     * <p>
     * 序列化为 snake_case，与 Python 后端及前端 UploadResult 类型定义
     * （apps/web-antd/src/api/core/upload.ts）保持一致
     */
    @JsonProperty("original_filename")
    private String originalFilename;

}
