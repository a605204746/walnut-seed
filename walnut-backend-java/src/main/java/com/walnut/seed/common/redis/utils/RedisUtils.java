package com.walnut.seed.common.redis.utils;

import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.SpringUtils;
import org.redisson.api.*;
import org.redisson.api.options.KeysScanOptions;

import java.time.Duration;
import java.util.Collection;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Redis 工具类 —— 全项目唯一的 Redis 操作入口（静态）
 * <p>
 * 业务缓存一律由业务代码显式定义：读取时加载（推荐 {@link #getOrLoad}，命中返回、未命中加载并缓存）、
 * 变更时删除（deleteObject），没有注解、CacheManager 等其他缓存机制。
 * </p>
 *
 * @author deepin_sir
 */
public class RedisUtils {

    private RedisUtils() {
    }

    private static RedissonClient CLIENT;

    /**
     * 惰性获取 RedissonClient（由 Spring 管理的单例，首次调用时经 SpringUtils 取得）
     */
    private static RedissonClient client() {
        if (CLIENT == null) {
            CLIENT = SpringUtils.getBean(RedissonClient.class);
        }
        return CLIENT;
    }

    // ===== KV 基础 =====

    public static <T> void setCacheObject(final String key, final T value) {
        client().getBucket(key).set(value);
    }

    public static <T> void setCacheObject(final String key, final T value, final Duration duration) {
        client().getBucket(key).set(value, duration);
    }

    /**
     * 写入新值，保留原有 TTL
     */
    public static <T> void setCacheObjectKeepTtl(final String key, final T value) {
        RBucket<T> bucket = client().getBucket(key);
        try {
            bucket.setAndKeepTTL(value);
        } catch (Exception e) {
            long ttl = bucket.remainTimeToLive();
            if (ttl == -1) {
                bucket.set(value);
            } else {
                bucket.set(value, Duration.ofMillis(ttl));
            }
        }
    }

    /**
     * key 不存在时写入并设置 TTL，返回是否写入成功
     */
    public static <T> boolean setObjectIfAbsent(final String key, final T value, final Duration duration) {
        return client().<T>getBucket(key).setIfAbsent(value, duration);
    }

    public static <T> T getCacheObject(final String key) {
        return client().<T>getBucket(key).get();
    }

    public static boolean deleteObject(final String key) {
        return client().getBucket(key).delete();
    }

    /**
     * 按 glob 模式批量删除（如 "sys_config:*"）
     */
    public static void deleteByPattern(final String pattern) {
        client().getKeys().deleteByPattern(pattern);
    }

    public static boolean expire(final String key, final Duration duration) {
        return client().getBucket(key).expire(duration);
    }

    /**
     * 返回剩余毫秒数；-1 = 永不过期；-2 = 不存在
     */
    public static long getTimeToLive(final String key) {
        return client().getBucket(key).remainTimeToLive();
    }

    public static boolean hasKey(final String key) {
        return client().getKeys().countExists(key) > 0;
    }

    /**
     * 读时加载（cache-aside）：命中直接返回；未命中执行 loader，结果非空时写入缓存
     *
     * @param key    缓存 key
     * @param ttl    过期时间，null 表示永不过期（依赖写路径主动删除）
     * @param loader 未命中时的数据加载逻辑（通常查数据库）
     */
    public static <T> T getOrLoad(final String key, final Duration ttl, final Supplier<T> loader) {
        T value = getCacheObject(key);
        if (value != null) {
            return value;
        }
        value = loader.get();
        if (value != null) {
            if (ttl != null) {
                setCacheObject(key, value, ttl);
            } else {
                setCacheObject(key, value);
            }
        }
        return value;
    }

    // ===== 分布式锁 =====

    /**
     * 默认获取锁等待时间（秒）
     */
    private static final long LOCK_WAIT_TIME = 3;
    /**
     * 默认锁持有时间（秒）
     */
    private static final long LOCK_LEASE_TIME = 30;

    /**
     * 获取分布式锁并执行业务逻辑（无返回值，默认等待 3 秒、固定持有 30 秒）
     *
     * @param key  锁 key
     * @param task 业务逻辑
     */
    public static void lock(final String key, final Runnable task) {
        lock(key, LOCK_WAIT_TIME, LOCK_LEASE_TIME, () -> {
            task.run();
            return null;
        });
    }

    /**
     * 获取分布式锁并执行业务逻辑（有返回值，默认等待 3 秒、固定持有 30 秒）
     *
     * @param key  锁 key
     * @param task 业务逻辑
     * @return 业务逻辑返回值
     */
    public static <T> T lock(final String key, final Supplier<T> task) {
        return lock(key, LOCK_WAIT_TIME, LOCK_LEASE_TIME, task);
    }

    /**
     * 获取分布式锁并执行业务逻辑（自定义等待/持有时间，到期强制释放，不续期）
     * <p>业务执行时长不可预知时，请改用 {@link #lockWatchdog}（看门狗自动续期）。</p>
     *
     * @param key       锁 key
     * @param waitTime  获取锁最长等待时间（秒）
     * @param leaseTime 锁持有时间（秒），到期自动释放
     * @param task      业务逻辑
     * @return 业务逻辑返回值
     */
    public static <T> T lock(final String key, final long waitTime, final long leaseTime, final Supplier<T> task) {
        RLock lock = client().getLock(key);
        boolean acquired = false;
        try {
            acquired = lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS);
            if (!acquired) {
                throw new ServiceException("分布式锁 [{}] 获取失败，请稍后重试", key);
            }
            return task.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ServiceException("分布式锁 [{}] 获取被中断", key);
        } finally {
            if (acquired && lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    /**
     * 获取分布式锁并执行业务逻辑（看门狗模式，无返回值）
     * <p>
     * 不指定持有时间，由 Redisson 看门狗自动续期：锁默认 30 秒到期
     * （redisson 配置 lockWatchdogTimeout），之后每 10 秒续期一次，
     * 业务执行多久锁就持有多久，进程崩溃则停止续期自动释放。
     * 适用于执行时长不可预知的业务；需要硬性持有上限时请用 {@link #lock}。
     * </p>
     *
     * @param key  锁 key
     * @param task 业务逻辑
     */
    public static void lockWatchdog(final String key, final Runnable task) {
        lockWatchdog(key, LOCK_WAIT_TIME, () -> {
            task.run();
            return null;
        });
    }

    /**
     * 获取分布式锁并执行业务逻辑（看门狗模式，有返回值）
     *
     * @param key  锁 key
     * @param task 业务逻辑
     * @return 业务逻辑返回值
     */
    public static <T> T lockWatchdog(final String key, final Supplier<T> task) {
        return lockWatchdog(key, LOCK_WAIT_TIME, task);
    }

    /**
     * 获取分布式锁并执行业务逻辑（看门狗模式，自定义等待时间）
     *
     * @param key      锁 key
     * @param waitTime 获取锁最长等待时间（秒）
     * @param task     业务逻辑
     * @return 业务逻辑返回值
     */
    public static <T> T lockWatchdog(final String key, final long waitTime, final Supplier<T> task) {
        RLock lock = client().getLock(key);
        boolean acquired = false;
        try {
            // leaseTime 传 -1：启用看门狗自动续期
            acquired = lock.tryLock(waitTime, -1, TimeUnit.SECONDS);
            if (!acquired) {
                throw new ServiceException("分布式锁 [{}] 获取失败，请稍后重试", key);
            }
            return task.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ServiceException("分布式锁 [{}] 获取被中断", key);
        } finally {
            if (acquired && lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    // ===== 限流 =====

    /**
     * @param rateType 0=OVERALL 1=PER_CLIENT；返回剩余许可数，-1 表示限流触发
     */
    public static long rateLimiter(String key, int rateType, int rate, int rateInterval, int timeout) {
        RRateLimiter limiter = client().getRateLimiter(key);
        RateType type = rateType == 1 ? RateType.PER_CLIENT : RateType.OVERALL;
        limiter.trySetRate(type, rate, Duration.ofSeconds(rateInterval),
                timeout > 0 ? Duration.ofSeconds(timeout) : Duration.ZERO);
        return limiter.tryAcquire() ? limiter.availablePermits() : -1L;
    }

    // ===== 发布订阅 =====

    public static <T> void publish(String channel, T msg) {
        client().getTopic(channel).publish(msg);
    }

    /**
     * 发布消息并本地回调（多实例场景下其他实例经 Redis 订阅接收）
     */
    public static <T> void publish(String channelKey, T msg, Consumer<T> consumer) {
        client().getTopic(channelKey).publish(msg);
        consumer.accept(msg);
    }

    public static <T> void subscribe(String channelKey, Class<T> clazz, Consumer<T> consumer) {
        RTopic topic = client().getTopic(channelKey);
        topic.addListener(clazz, (ch, msg) -> consumer.accept(msg));
    }

    // ===== 键扫描 =====

    /**
     * 按 glob 模式扫描 key（底层走 SCAN，避免 KEYS 阻塞）
     */
    public static Collection<String> keys(final String pattern) {
        Stream<String> stream = client().getKeys()
                .getKeysStream(KeysScanOptions.defaults().pattern(pattern).chunkSize(1000));
        return stream.collect(Collectors.toList());
    }

    // ===== 实例标识 =====

    /**
     * 当前实例标识，用于 CLUSTER 限流等需要区分实例的场景
     */
    public static String getInstanceId() {
        return client().getId();
    }
}
