package com.walnut.seed.common.oss;

import com.walnut.seed.common.oss.model.UploadResult;
import org.springframework.web.multipart.MultipartFile;

import jakarta.servlet.http.HttpServletResponse;
import java.io.File;
import java.io.IOException;

/**
 * 文件存储统一接口
 * <p>
 * 调用方无需关心底层使用的是本地存储还是阿里云 OSS。
 *
 * @author deepin_sir
 */
public interface FileStorageService {

    /**
     * 上传 MultipartFile
     *
     * @param file 上传的文件
     * @return 上传结果（含 URL 和原始文件名）
     */
    UploadResult upload(MultipartFile file);

    /**
     * 上传 File
     *
     * @param file 上传的文件
     * @return 上传结果（含 URL 和原始文件名）
     */
    UploadResult upload(File file);

    /**
     * 下载文件到 HTTP 响应
     *
     * @param fileUrl  文件 URL（upload 返回的 url）
     * @param response HTTP 响应对象
     */
    void download(String fileUrl, HttpServletResponse response) throws IOException;

    /**
     * 内联展示文件到 HTTP 响应（浏览器直接渲染，如图片回显；
     * 与 Python 后端 /upload/{file_path:path} 的公开访问语义一致）
     *
     * @param fileUrl  文件 URL（upload 返回的 url）
     * @param response HTTP 响应对象
     */
    void serve(String fileUrl, HttpServletResponse response) throws IOException;

    /**
     * 删除文件
     *
     * @param fileUrl 文件 URL（upload 返回的 url）
     */
    void delete(String fileUrl);

}
