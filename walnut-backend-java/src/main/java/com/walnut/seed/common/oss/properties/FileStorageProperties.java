package com.walnut.seed.common.oss.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 文件存储配置属性
 *
 * @author deepin_sir
 */
@Data
@ConfigurationProperties(prefix = "oss")
public class FileStorageProperties {

    /**
     * 存储类型：seaweedfs（默认）、aliyun
     */
    private String type = "seaweedfs";

    /**
     * SeaweedFS（S3 协议兼容）配置
     */
    private SeaweedProperties seaweedfs = new SeaweedProperties();

    /**
     * 阿里云 OSS 配置
     */
    private AliyunProperties aliyun = new AliyunProperties();

    @Data
    public static class SeaweedProperties {
        /**
         * S3 API 地址（SeaweedFS all-in-one 默认端口 8333）
         */
        private String endpoint = "http://localhost:8333";

        /**
         * Bucket 名称（不存在时启动自动创建）
         */
        private String bucket = "walnut-seed";

        /**
         * 浏览器访问的公共 URL 前缀（含 bucket 段）。
         * 缺省为 endpoint/bucket（直连 S3 网关，适用开发环境）；
         * 生产经 nginx /s3/ 只读反代暴露时覆盖为 /s3/walnut-seed 之类的相对前缀。
         */
        private String publicUrl;

        /**
         * 访问凭证（可选）。
         * SeaweedFS S3 网关默认信任访问者（上游 #4728/#8331，静态 -s3.config 身份不生效），
         * 不配置即匿名访问；后续版本支持鉴权后再填写。
         */
        private String accessKeyId;

        /**
         * 访问凭证密钥（可选，说明见 accessKeyId）
         */
        private String secretAccessKey;
    }

    @Data
    public static class AliyunProperties {
        /**
         * OSS Endpoint，如 oss-cn-beijing.aliyuncs.com
         */
        private String endpoint;

        /**
         * AccessKey ID
         */
        private String accessKeyId;

        /**
         * AccessKey Secret
         */
        private String accessKeySecret;

        /**
         * Bucket 名称
         */
        private String bucketName;

        /**
         * URL 前缀，如 <a href="https://bucket.oss-cn-beijing.aliyuncs.com">...</a>
         */
        private String urlPrefix;
    }

}
