package com.walnut.seed.common.web.config;

import jakarta.servlet.ServletException;
import org.apache.catalina.connector.Request;
import org.apache.catalina.connector.Response;
import org.apache.catalina.valves.ValveBase;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;

import java.io.IOException;
import java.util.Set;

/**
 * Tomcat 自定义配置
 * <p>
 * 主要配置内容包括：
 * 1. 禁用不安全的 HTTP 方法（CONNECT、TRACE、TRACK）
 * </p>
 * <p>
 * 以下配置通过 application.yml 完成，无需代码干预：
 * - max-http-post-size → server.tomcat.max-http-form-post-size
 * - 虚拟线程 → spring.threads.virtual.enabled
 * - WebSocket 缓冲区 → Tomcat 原生管理
 * </p>
 *
 * @author deepin_sir
 */
@AutoConfiguration
@ConditionalOnClass(TomcatServletWebServerFactory.class)
public class TomcatConfig implements WebServerFactoryCustomizer<TomcatServletWebServerFactory> {

    private static final Set<String> DISALLOWED_METHODS = Set.of("CONNECT", "TRACE", "TRACK");

    @Override
    public void customize(TomcatServletWebServerFactory factory) {
        factory.addContextValves(new DisallowedMethodsValve());
    }

    /**
     * 拦截并拒绝不安全的 HTTP 方法，避免爬虫骚扰
     */
    static class DisallowedMethodsValve extends ValveBase {

        @Override
        public void invoke(Request request, Response response) throws IOException, ServletException {
            if (DISALLOWED_METHODS.contains(request.getMethod())) {
                response.sendError(405, "Method Not Allowed");
                return;
            }
            getNext().invoke(request, response);
        }
    }

}
