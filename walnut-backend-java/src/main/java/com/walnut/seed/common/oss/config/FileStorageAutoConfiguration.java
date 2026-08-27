package com.walnut.seed.common.oss.config;

import com.walnut.seed.common.oss.FileStorageService;
import com.walnut.seed.common.oss.aliyun.AliyunFileStorageService;
import com.walnut.seed.common.oss.properties.FileStorageProperties;
import com.walnut.seed.common.oss.seaweed.SeaweedFileStorageService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

/**
 * 文件存储自动配置
 * <p>
 * 默认使用 SeaweedFS（type=seaweedfs 或不配置）。
 * 配置 oss.type=aliyun 后切换为阿里云 OSS。
 *
 * @author deepin_sir
 */
@Slf4j
@AutoConfiguration
@EnableConfigurationProperties(FileStorageProperties.class)
public class FileStorageAutoConfiguration {

    /**
     * SeaweedFS 文件存储（默认，S3 协议兼容）
     */
    @Bean
    @ConditionalOnMissingBean(FileStorageService.class)
    @ConditionalOnProperty(name = "oss.type", havingValue = "seaweedfs", matchIfMissing = true)
    public FileStorageService seaweedFileStorageService(FileStorageProperties properties) {
        return new SeaweedFileStorageService(properties.getSeaweedfs());
    }

    /**
     * 阿里云 OSS 文件存储
     */
    @Bean
    @ConditionalOnMissingBean(FileStorageService.class)
    @ConditionalOnProperty(name = "oss.type", havingValue = "aliyun")
    public FileStorageService aliyunFileStorageService(FileStorageProperties properties) {
        return new AliyunFileStorageService(properties.getAliyun());
    }

}
