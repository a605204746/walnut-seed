package com.walnut.seed.common.core.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 线程池配置
 * <p>
 * IO 密集型场景：核心线程 = CPU 核心数 + 1，最大线程 = 核心线程 * 2。
 * 业务代码通过 {@code @Qualifier("walnutExecutor")} 注入使用。
 *
 * @author deepin_sir
 **/
@Slf4j
@AutoConfiguration
@ConditionalOnProperty(name = "walnut.thread-pool.enabled", havingValue = "true", matchIfMissing = true)
public class ThreadPoolConfig {

    private static final int CPU_COUNT = Runtime.getRuntime().availableProcessors();

    /**
     * 业务线程池（IO 密集型默认参数）
     */
    @Bean(name = "walnutExecutor")
    public ThreadPoolTaskExecutor walnutExecutor() {
        int coreSize = CPU_COUNT + 1;
        int maxSize = coreSize * 2;
        int queueCapacity = 256;

        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(coreSize);
        executor.setMaxPoolSize(maxSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setKeepAliveSeconds(60);
        executor.setAllowCoreThreadTimeOut(true);
        executor.setThreadNamePrefix("walnut-async-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(120);
        executor.initialize();
        log.info("初始化 walnutExecutor 线程池 [cpu={}, core={}, max={}, queue={}]",
            CPU_COUNT, coreSize, maxSize, queueCapacity);
        return executor;
    }

    private static final AtomicLong SCHEDULED_COUNTER = new AtomicLong();

    /**
     * 定时任务线程池（SSE 心跳等场景使用）
     */
    @Bean
    public ScheduledExecutorService scheduledExecutorService() {
        int coreSize = CPU_COUNT + 1;
        ScheduledThreadPoolExecutor executor = new ScheduledThreadPoolExecutor(coreSize, r -> {
            Thread t = new Thread(r, "walnut-scheduled-" + SCHEDULED_COUNTER.incrementAndGet());
            t.setDaemon(true);
            return t;
        });
        log.info("初始化 scheduledExecutorService 线程池 [cpu={}, core={}]", CPU_COUNT, coreSize);
        return executor;
    }

}
