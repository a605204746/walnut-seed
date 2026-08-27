package com.walnut.seed.module.web.controller;

import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.oss.FileStorageService;
import com.walnut.seed.common.oss.model.UploadResult;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

/**
 * 文件管理
 * <p>
 * 与 Python 后端 /common/file/* 对齐（见
 * walnut-backend-python/app/api/v1/module_common/file/controller.py）：
 * 上传返回 {url, original_filename}（snake_case，对应前端
 * apps/web-antd/src/api/core/upload.ts 的 UploadResult 类型）。
 * 登录鉴权由全局 Sa-Token 拦截器统一校验（路径不在 security.excludes 内）。
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@RestController
@RequestMapping("/common/file")
public class FileController {

    private final FileStorageService fileStorageService;

    /**
     * 文件上传（multipart 字段名 file，与前端 uploadApi 一致）
     */
    @PostMapping("/upload")
    public ApiResponse<UploadResult> upload(@RequestParam("file") MultipartFile file) {
        return ApiResponse.ok("上传成功", fileStorageService.upload(file));
    }

    /**
     * 文件下载（查询参数名 file_url，与 Python 端一致）
     */
    @GetMapping("/download")
    public void download(@RequestParam("file_url") String fileUrl, HttpServletResponse response) throws IOException {
        fileStorageService.download(fileUrl, response);
    }

    /**
     * 文件删除（查询参数名 file_url，与 Python 端一致）
     */
    @DeleteMapping("/delete")
    public ApiResponse<Void> delete(@RequestParam("file_url") String fileUrl) {
        fileStorageService.delete(fileUrl);
        return ApiResponse.ok("删除成功");
    }

}
