package com.walnut.seed.common.oss.aliyun;

import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.StrUtil;
import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSClientBuilder;
import com.aliyun.oss.model.OSSObject;
import com.walnut.seed.common.oss.FileStorageService;
import com.walnut.seed.common.oss.model.UploadResult;
import com.walnut.seed.common.oss.properties.FileStorageProperties;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/**
 * 阿里云 OSS 文件存储实现（基于官方 SDK）
 *
 * @author deepin_sir
 */
@Slf4j
public class AliyunFileStorageService implements FileStorageService {

    private final FileStorageProperties.AliyunProperties config;
    private final OSS ossClient;

    public AliyunFileStorageService(FileStorageProperties.AliyunProperties config) {
        this.config = config;
        this.ossClient = new OSSClientBuilder().build(
            config.getEndpoint(), config.getAccessKeyId(), config.getAccessKeySecret());
        log.info("阿里云 OSS 存储初始化完成，endpoint: {}, bucket: {}", config.getEndpoint(), config.getBucketName());
    }

    @Override
    public UploadResult upload(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("上传文件不能为空");
        }
        String originalFilename = file.getOriginalFilename();
        String objectKey = generateObjectKey(originalFilename);
        try (InputStream inputStream = file.getInputStream()) {
            ossClient.putObject(config.getBucketName(), objectKey, inputStream);
        } catch (IOException e) {
            throw new RuntimeException("文件上传失败: " + originalFilename, e);
        }
        return new UploadResult(buildUrl(objectKey), originalFilename);
    }

    @Override
    public UploadResult upload(File file) {
        if (file == null || !file.exists()) {
            throw new IllegalArgumentException("上传文件不能为空");
        }
        String originalFilename = file.getName();
        String objectKey = generateObjectKey(originalFilename);
        try (InputStream inputStream = new FileInputStream(file)) {
            ossClient.putObject(config.getBucketName(), objectKey, inputStream);
        } catch (IOException e) {
            throw new RuntimeException("文件上传失败: " + originalFilename, e);
        }
        return new UploadResult(buildUrl(objectKey), originalFilename);
    }

    @Override
    public void download(String fileUrl, HttpServletResponse response) throws IOException {
        String objectKey = extractObjectKey(fileUrl);
        try {
            OSSObject ossObject = ossClient.getObject(config.getBucketName(), objectKey);
            String fileName = objectKey.substring(objectKey.lastIndexOf('/') + 1);
            response.setContentType(MediaType.APPLICATION_OCTET_STREAM_VALUE);
            response.setHeader("Content-Disposition", "attachment; filename=\"" + fileName + "\"");
            try (InputStream in = ossObject.getObjectContent();
                 OutputStream out = response.getOutputStream()) {
                in.transferTo(out);
                out.flush();
            }
        } catch (Exception e) {
            throw new RuntimeException("文件下载失败: " + objectKey, e);
        }
    }

    @Override
    public void serve(String fileUrl, HttpServletResponse response) throws IOException {
        String objectKey = extractObjectKey(fileUrl);
        try {
            OSSObject ossObject = ossClient.getObject(config.getBucketName(), objectKey);
            String contentType = ossObject.getObjectMetadata().getContentType();
            response.setContentType(StrUtil.isNotBlank(contentType) ? contentType : MediaType.APPLICATION_OCTET_STREAM_VALUE);
            // 内联展示（浏览器直接渲染），区别于 download 的 attachment 下载
            response.setHeader("Content-Disposition", "inline");
            try (InputStream in = ossObject.getObjectContent();
                 OutputStream out = response.getOutputStream()) {
                in.transferTo(out);
                out.flush();
            }
        } catch (Exception e) {
            throw new RuntimeException("文件访问失败: " + objectKey, e);
        }
    }

    @Override
    public void delete(String fileUrl) {
        String objectKey = extractObjectKey(fileUrl);
        try {
            ossClient.deleteObject(config.getBucketName(), objectKey);
        } catch (Exception e) {
            log.warn("删除 OSS 文件失败: {}", objectKey, e);
        }
    }

    /**
     * 生成对象 Key：{yyyy/MM/dd}/{uuid}.{ext}
     */
    private String generateObjectKey(String originalFilename) {
        String dateDir = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        String ext = FileUtil.extName(originalFilename);
        String fileName = IdUtil.fastSimpleUUID();
        if (ext != null && !ext.isEmpty()) {
            fileName = fileName + "." + ext;
        }
        return dateDir + "/" + fileName;
    }

    /**
     * 构建完整 URL
     */
    private String buildUrl(String objectKey) {
        String prefix = config.getUrlPrefix();
        if (prefix != null && !prefix.isEmpty()) {
            return prefix.endsWith("/") ? prefix + objectKey : prefix + "/" + objectKey;
        }
        return "https://" + config.getBucketName() + "." + config.getEndpoint() + "/" + objectKey;
    }

    /**
     * 从 URL 中提取对象 Key
     */
    private String extractObjectKey(String fileUrl) {
        String prefix = config.getUrlPrefix();
        if (prefix != null && !prefix.isEmpty() && fileUrl.startsWith(prefix)) {
            String key = fileUrl.substring(prefix.length());
            return key.startsWith("/") ? key.substring(1) : key;
        }
        // fallback: 取 URL 路径部分
        int idx = fileUrl.indexOf(".com/");
        if (idx > 0) {
            return fileUrl.substring(idx + 5);
        }
        return fileUrl;
    }

}
