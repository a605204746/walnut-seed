package com.walnut.seed.common.oss.seaweed;

import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.StrUtil;
import com.walnut.seed.common.oss.FileStorageService;
import com.walnut.seed.common.oss.model.UploadResult;
import com.walnut.seed.common.oss.properties.FileStorageProperties;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.auth.credentials.AnonymousCredentialsProvider;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectResponse;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.model.S3Exception;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/**
 * SeaweedFS 文件存储实现（走 S3 协议网关，基于 AWS SDK v2）
 *
 * @author deepin_sir
 */
@Slf4j
public class SeaweedFileStorageService implements FileStorageService {

    private final FileStorageProperties.SeaweedProperties config;
    private final S3Client s3Client;
    /**
     * 浏览器可访问的公共 URL 前缀（含 bucket 段）
     */
    private final String publicUrl;

    public SeaweedFileStorageService(FileStorageProperties.SeaweedProperties config) {
        this.config = config;
        // 配置了凭证走静态凭证，否则匿名（SeaweedFS S3 网关默认信任访问者）
        AwsCredentialsProvider credentialsProvider = StrUtil.isAllNotBlank(config.getAccessKeyId(), config.getSecretAccessKey())
            ? StaticCredentialsProvider.create(AwsBasicCredentials.create(config.getAccessKeyId(), config.getSecretAccessKey()))
            : AnonymousCredentialsProvider.create();
        this.s3Client = S3Client.builder()
            .endpointOverride(URI.create(config.getEndpoint()))
            // S3 协议必备参数，SeaweedFS 不校验实际区域
            .region(Region.US_EAST_1)
            // path-style 寻址（host/bucket/key），兼容 SeaweedFS S3 网关
            .forcePathStyle(true)
            .credentialsProvider(credentialsProvider)
            .build();
        ensureBucket();
        String publicUrl = StrUtil.isNotBlank(config.getPublicUrl())
            ? config.getPublicUrl()
            : StrUtil.removeSuffix(config.getEndpoint(), "/") + "/" + config.getBucket();
        this.publicUrl = StrUtil.removeSuffix(publicUrl, "/");
        log.info("SeaweedFS 存储初始化完成，endpoint: {}, bucket: {}", config.getEndpoint(), config.getBucket());
    }

    /**
     * Bucket 不存在时自动创建，保证开箱即用
     */
    private void ensureBucket() {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(config.getBucket()).build());
        } catch (NoSuchBucketException e) {
            s3Client.createBucket(CreateBucketRequest.builder().bucket(config.getBucket()).build());
            log.info("SeaweedFS bucket 不存在，已自动创建: {}", config.getBucket());
        } catch (S3Exception e) {
            throw new RuntimeException("无法访问 SeaweedFS bucket: " + config.getBucket(), e);
        }
    }

    @Override
    public UploadResult upload(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("上传文件不能为空");
        }
        String originalFilename = file.getOriginalFilename();
        String objectKey = generateObjectKey(originalFilename);
        String contentType = file.getContentType() != null ? file.getContentType() : MediaType.APPLICATION_OCTET_STREAM_VALUE;
        try (InputStream inputStream = file.getInputStream()) {
            s3Client.putObject(PutObjectRequest.builder()
                    .bucket(config.getBucket()).key(objectKey).contentType(contentType).build(),
                RequestBody.fromInputStream(inputStream, file.getSize()));
        } catch (IOException e) {
            throw new RuntimeException("文件上传失败: " + originalFilename, e);
        }
        return new UploadResult(publicUrl + "/" + objectKey, originalFilename);
    }

    @Override
    public UploadResult upload(File file) {
        if (file == null || !file.exists()) {
            throw new IllegalArgumentException("上传文件不能为空");
        }
        String originalFilename = file.getName();
        String objectKey = generateObjectKey(originalFilename);
        String contentType;
        try {
            contentType = Files.probeContentType(file.toPath());
        } catch (IOException e) {
            contentType = null;
        }
        try {
            s3Client.putObject(PutObjectRequest.builder()
                    .bucket(config.getBucket()).key(objectKey)
                    .contentType(contentType != null ? contentType : MediaType.APPLICATION_OCTET_STREAM_VALUE).build(),
                RequestBody.fromFile(file));
        } catch (SdkException e) {
            throw new RuntimeException("文件上传失败: " + originalFilename, e);
        }
        return new UploadResult(publicUrl + "/" + objectKey, originalFilename);
    }

    @Override
    public void download(String fileUrl, HttpServletResponse response) throws IOException {
        String objectKey = extractObjectKey(fileUrl);
        try (ResponseInputStream<GetObjectResponse> in = s3Client.getObject(
            GetObjectRequest.builder().bucket(config.getBucket()).key(objectKey).build())) {
            GetObjectResponse meta = in.response();
            String contentType = meta.contentType();
            response.setContentType(StrUtil.isNotBlank(contentType) ? contentType : MediaType.APPLICATION_OCTET_STREAM_VALUE);
            if (meta.contentLength() != null) {
                response.setContentLengthLong(meta.contentLength());
            }
            String fileName = objectKey.substring(objectKey.lastIndexOf('/') + 1);
            response.setHeader("Content-Disposition", "attachment; filename=\"" + fileName + "\"");
            try (OutputStream out = response.getOutputStream()) {
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
        try (ResponseInputStream<GetObjectResponse> in = s3Client.getObject(
            GetObjectRequest.builder().bucket(config.getBucket()).key(objectKey).build())) {
            GetObjectResponse meta = in.response();
            String contentType = meta.contentType();
            response.setContentType(StrUtil.isNotBlank(contentType) ? contentType : MediaType.APPLICATION_OCTET_STREAM_VALUE);
            if (meta.contentLength() != null) {
                response.setContentLengthLong(meta.contentLength());
            }
            // 内联展示（浏览器直接渲染），区别于 download 的 attachment 下载
            response.setHeader("Content-Disposition", "inline");
            try (OutputStream out = response.getOutputStream()) {
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
            s3Client.deleteObject(DeleteObjectRequest.builder().bucket(config.getBucket()).key(objectKey).build());
        } catch (Exception e) {
            log.warn("删除 SeaweedFS 文件失败: {}", objectKey, e);
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
     * 从 URL 中提取对象 Key（依次尝试公共前缀、endpoint/bucket 前缀）
     */
    private String extractObjectKey(String fileUrl) {
        String endpointBucket = StrUtil.removeSuffix(config.getEndpoint(), "/") + "/" + config.getBucket();
        for (String prefix : new String[]{publicUrl, endpointBucket}) {
            if (fileUrl.startsWith(prefix)) {
                String key = fileUrl.substring(prefix.length());
                return key.startsWith("/") ? key.substring(1) : key;
            }
        }
        return fileUrl;
    }

}
