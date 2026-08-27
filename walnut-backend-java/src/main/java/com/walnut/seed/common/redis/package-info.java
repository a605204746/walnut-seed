/**
 * Redis 子系统 —— Redis 是唯一缓存后端，全项目唯一缓存入口是 {@link com.walnut.seed.common.redis.utils.RedisUtils}
 * <p>
 * 业务缓存一律由业务代码显式定义：读取时加载（setCacheObject）、变更时删除（deleteObject），
 * 没有注解、CacheManager 等声明式缓存机制。
 * </p>
 *
 * <h2>包结构</h2>
 * <pre>
 * config/
 *   RedisConfig             Redisson 客户端装配（starter 自动配置 + 参数扩展）
 *   properties/             RedissonProperties — redisson.* 配置绑定
 * handler/
 *   KeyPrefixHandler        Redis key 前缀
 *   RedisExceptionHandler   Redisson 异常处理
 * ratelimiter/              @RateLimiter 限流（基于 RedisUtils.rateLimiter）
 * idempotent/               @RepeatSubmit 防重提交（基于 RedisUtils.setObjectIfAbsent）
 * utils/
 *   RedisUtils              唯一的 Redis 操作类（静态）
 * </pre>
 *
 * @author deepin_sir
 */
package com.walnut.seed.common.redis;
