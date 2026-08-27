package com.walnut.seed.common.redis.config;

import cn.hutool.core.util.ObjectUtil;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.jsontype.impl.LaissezFaireSubTypeValidator;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.fasterxml.jackson.datatype.jsr310.deser.LocalDateTimeDeserializer;
import com.fasterxml.jackson.datatype.jsr310.ser.LocalDateTimeSerializer;
import com.walnut.seed.common.redis.config.properties.RedissonProperties;
import com.walnut.seed.common.redis.handler.KeyPrefixHandler;
import lombok.extern.slf4j.Slf4j;
import org.redisson.client.codec.StringCodec;
import org.redisson.codec.CompositeCodec;
import org.redisson.codec.TypedJsonJacksonCodec;
import org.redisson.spring.starter.RedissonAutoConfigurationCustomizer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.TimeZone;

/**
 * redis配置
 *
 * @author deepin_sir
 */
@Slf4j
@AutoConfiguration
@EnableConfigurationProperties(RedissonProperties.class)
public class RedisConfig {

    @Autowired
    private RedissonProperties redissonProperties;

    @Bean
    public RedissonAutoConfigurationCustomizer redissonCustomizer() {
        return config -> {
            JavaTimeModule javaTimeModule = new JavaTimeModule();
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
            javaTimeModule.addSerializer(LocalDateTime.class, new LocalDateTimeSerializer(formatter));
            javaTimeModule.addDeserializer(LocalDateTime.class, new LocalDateTimeDeserializer(formatter));
            ObjectMapper om = new ObjectMapper();
            om.registerModule(javaTimeModule);
            om.setTimeZone(TimeZone.getDefault());
            om.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
            // 指定序列化输入的类型，类必须是非final修饰的。序列化时将对象全类名一起保存下来
            om.activateDefaultTyping(LaissezFaireSubTypeValidator.instance, ObjectMapper.DefaultTyping.NON_FINAL);
            // org.apache.fory.logging.LoggerFactory 包别引入错了
            // LoggerFactory.useSlf4jLogging(true);
            // ForyCodec foryCodec = new ForyCodec();
            // CompositeCodec codec = new CompositeCodec(StringCodec.INSTANCE, foryCodec, foryCodec);
            TypedJsonJacksonCodec jsonCodec = new TypedJsonJacksonCodec(Object.class, om);
            // 组合序列化 key 使用 String 内容使用通用 json 格式
            CompositeCodec codec = new CompositeCodec(StringCodec.INSTANCE, jsonCodec, jsonCodec);
            config
                    // 缓存 Lua 脚本 减少网络传输(redisson 大部分的功能都是基于 Lua 脚本实现)
                    .setUseScriptCache(true)
                    .setCodec(codec);
            ifPresent(redissonProperties.getThreads(), config::setThreads);
            ifPresent(redissonProperties.getNettyThreads(), config::setNettyThreads);
            // netty 对虚拟线程适配有问题 暂时禁止使用
            //if (SpringUtils.isVirtual()) {
            //    config.setNettyExecutor(new VirtualThreadTaskExecutor("redisson-"));
            //}
            RedissonProperties.SingleServerConfig singleServerConfig = redissonProperties.getSingleServerConfig();
            if (ObjectUtil.isNotNull(singleServerConfig)) {
                // 使用单机模式，设置 redis key 前缀
                var single = config.useSingleServer()
                        .setNameMapper(new KeyPrefixHandler(redissonProperties.getKeyPrefix()));
                ifPresent(singleServerConfig.getClientName(), single::setClientName);
                ifPresent(singleServerConfig.getTimeout(), single::setTimeout);
                ifPresent(singleServerConfig.getIdleConnectionTimeout(), single::setIdleConnectionTimeout);
                ifPresent(singleServerConfig.getConnectionMinimumIdleSize(), single::setConnectionMinimumIdleSize);
                ifPresent(singleServerConfig.getConnectionPoolSize(), single::setConnectionPoolSize);
                ifPresent(singleServerConfig.getSubscriptionConnectionPoolSize(), single::setSubscriptionConnectionPoolSize);
            }
            // 集群配置方式 参考下方注释
            RedissonProperties.ClusterServersConfig clusterServersConfig = redissonProperties.getClusterServersConfig();
            if (ObjectUtil.isNotNull(clusterServersConfig)) {
                var cluster = config.useClusterServers()
                        //设置redis key前缀
                        .setNameMapper(new KeyPrefixHandler(redissonProperties.getKeyPrefix()));
                ifPresent(clusterServersConfig.getClientName(), cluster::setClientName);
                ifPresent(clusterServersConfig.getTimeout(), cluster::setTimeout);
                ifPresent(clusterServersConfig.getIdleConnectionTimeout(), cluster::setIdleConnectionTimeout);
                ifPresent(clusterServersConfig.getMasterConnectionMinimumIdleSize(), cluster::setMasterConnectionMinimumIdleSize);
                ifPresent(clusterServersConfig.getMasterConnectionPoolSize(), cluster::setMasterConnectionPoolSize);
                ifPresent(clusterServersConfig.getSlaveConnectionMinimumIdleSize(), cluster::setSlaveConnectionMinimumIdleSize);
                ifPresent(clusterServersConfig.getSlaveConnectionPoolSize(), cluster::setSlaveConnectionPoolSize);
                ifPresent(clusterServersConfig.getSubscriptionConnectionPoolSize(), cluster::setSubscriptionConnectionPoolSize);
                ifPresent(clusterServersConfig.getReadMode(), cluster::setReadMode);
                ifPresent(clusterServersConfig.getSubscriptionMode(), cluster::setSubscriptionMode);
            }
            log.info("初始化 redis 配置");
        };
    }

    /**
     * 可选配置项：yml 未配置（null）时跳过，回退 Redisson 自身默认值
     */
    private static <T> void ifPresent(T value, java.util.function.Consumer<T> setter) {
        if (value != null) {
            setter.accept(value);
        }
    }

    /**
     * redis集群配置 yml
     *
     * --- # redis 集群配置(单机与集群只能开启一个另一个需要注释掉)
     * spring.data:
     *   redis:
     *     cluster:
     *       nodes:
     *         - 192.168.0.100:6379
     *         - 192.168.0.101:6379
     *         - 192.168.0.102:6379
     *     # 密码
     *     password:
     *     # 连接超时时间
     *     timeout: 10s
     *     # 是否开启ssl
     *     ssl.enabled: false
     *
     * redisson:
     *   # 线程池数量
     *   threads: 16
     *   # Netty线程池数量
     *   nettyThreads: 32
     *   # 集群配置
     *   clusterServersConfig:
     *     # 客户端名称
     *     clientName: ${app.name}
     *     # master最小空闲连接数
     *     masterConnectionMinimumIdleSize: 32
     *     # master连接池大小
     *     masterConnectionPoolSize: 64
     *     # slave最小空闲连接数
     *     slaveConnectionMinimumIdleSize: 32
     *     # slave连接池大小
     *     slaveConnectionPoolSize: 64
     *     # 连接空闲超时，单位：毫秒
     *     idleConnectionTimeout: 10000
     *     # 命令等待超时，单位：毫秒
     *     timeout: 3000
     *     # 发布和订阅连接池大小
     *     subscriptionConnectionPoolSize: 50
     *     # 读取模式
     *     readMode: "SLAVE"
     *     # 订阅模式
     *     subscriptionMode: "MASTER"
     */

}
