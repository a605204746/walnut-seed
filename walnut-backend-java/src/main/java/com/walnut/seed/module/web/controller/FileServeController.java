package com.walnut.seed.module.web.controller;

import com.walnut.seed.common.oss.FileStorageService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;

/**
 * 上传文件内联访问（公开、无鉴权，路径已列入 security.excludes）
 * <p>
 * 与 Python 后端根路径的 /upload/{file_path:path} 对齐（见
 * walnut-backend-python/app/api/v1/module_common/file/controller.py 的 FileServeRouter）：
 * 对象经后端从对象存储（默认 SeaweedFS）流式内联返回，浏览器经
 * /api（vite 代理）或 /prod-api + /upload（nginx 代理）前缀访问。
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@RestController
public class FileServeController {

    private final FileStorageService fileStorageService;

    /**
     * 上传文件访问（内联展示）
     *
     * @param filePath /upload/ 之后的对象 Key（含前导斜杠，如 /2026-08-26/xxx.png）
     */
    @GetMapping("/upload/{*filePath}")
    public void serve(@PathVariable String filePath, HttpServletResponse response) throws IOException {
        // 存储服务的 extractObjectKey 会剥离 publicUrl(/upload) 前缀得到对象 Key
        fileStorageService.serve("/upload" + filePath, response);
    }

}
