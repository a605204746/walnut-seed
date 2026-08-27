package com.walnut.seed.module.web.controller;

import cn.dev33.satoken.annotation.SaIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.walnut.seed.common.core.domain.ApiResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RedissonClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.io.File;
import java.lang.management.ManagementFactory;
import java.sql.Connection;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 健康检查
 * <p>
 * 与 Python 后端 /common/health/* 完全对齐（见
 * walnut-backend-python/app/api/v1/module_common/health/controller.py）：
 * check/live 为存活式探针（不依赖 DB/Redis），ready 为就绪探针（DB + Redis），
 * compose 编排以 /common/health/check 作为后端探活地址。
 *
 * @author deepin_sir
 */
@Slf4j
@SaIgnore
@RequiredArgsConstructor
@RestController
@RequestMapping("/common/health")
public class HealthController {

    private static final String VERSION = "1.0.0";

    private final DataSource dataSource;
    private final RedissonClient redissonClient;

    /**
     * 通用健康检查（compose healthcheck 探活地址），不依赖 DB/Redis
     */
    @GetMapping("/check")
    public ApiResponse<HealthOut> check() {
        return ApiResponse.ok("系统健康", HealthOut.now());
    }

    /**
     * 存活探针
     */
    @GetMapping("/live")
    public ApiResponse<HealthOut> live() {
        return ApiResponse.ok("进程存活", HealthOut.now());
    }

    /**
     * 就绪探针：数据库 + Redis 均就绪才返回 200，否则 HTTP 503
     */
    @GetMapping("/ready")
    public ResponseEntity<ApiResponse<ReadinessOut>> ready() {
        DependencyStatus database = checkDatabase();
        DependencyStatus redis = checkRedis();
        boolean ok = database.status() == 1 && redis.status() == 1;
        ReadinessOut out = new ReadinessOut(ok ? 1 : 0, timestamp(), VERSION, uptimeSeconds(),
            new Dependencies(database, redis), diskUsagePercent());
        if (ok) {
            return ResponseEntity.ok(ApiResponse.ok("依赖就绪", out));
        }
        return ResponseEntity.status(503).body(ApiResponse.fail(503, "依赖未就绪"));
    }

    private DependencyStatus checkDatabase() {
        long start = System.nanoTime();
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            stmt.execute("SELECT 1");
            return new DependencyStatus(1, latencyMs(start));
        } catch (Exception e) {
            log.warn("数据库健康检查失败: {}", e.getMessage());
            return new DependencyStatus(0, null);
        }
    }

    private DependencyStatus checkRedis() {
        long start = System.nanoTime();
        try {
            redissonClient.getBucket("walnut:health:probe").isExists();
            return new DependencyStatus(1, latencyMs(start));
        } catch (Exception e) {
            log.warn("Redis 健康检查失败: {}", e.getMessage());
            return new DependencyStatus(0, null);
        }
    }

    private static double latencyMs(long startNanos) {
        return Math.round((System.nanoTime() - startNanos) / 1_000_000.0 * 100.0) / 100.0;
    }

    private static String timestamp() {
        return LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
    }

    private static double uptimeSeconds() {
        return ManagementFactory.getRuntimeMXBean().getUptime() / 1000.0;
    }

    private static Integer diskUsagePercent() {
        try {
            File root = new File("/");
            long total = root.getTotalSpace();
            long usable = root.getUsableSpace();
            if (total <= 0) {
                return null;
            }
            return (int) ((total - usable) * 100 / total);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 基础健康信息（字段名与 Python HealthOut 一致，snake_case 输出）
     */
    public record HealthOut(int status, String timestamp, String version,
                            @JsonProperty("uptime_seconds") double uptimeSeconds) {

        static HealthOut now() {
            // 限定外层类名：record 内 timestamp()/uptimeSeconds() 会优先解析为组件访问器（实例方法）
            return new HealthOut(1, HealthController.timestamp(), VERSION, HealthController.uptimeSeconds());
        }
    }

    /**
     * 就绪信息（字段名与 Python ReadinessOut 一致）
     */
    public record ReadinessOut(int status, String timestamp, String version,
                               @JsonProperty("uptime_seconds") double uptimeSeconds,
                               Dependencies dependencies,
                               @JsonProperty("disk_usage") Integer diskUsage) {
    }

    public record Dependencies(DependencyStatus database, DependencyStatus redis) {
    }

    public record DependencyStatus(int status, @JsonProperty("latency_ms") Double latencyMs) {
    }

}
