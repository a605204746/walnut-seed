package com.walnut.seed;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;

/**
 * 启动程序
 *
 * @author deepin_sir
 */

@SpringBootApplication
@MapperScan("com.walnut.seed.**.mapper")
public class WalnutSeedApplication {

    public static void main(String[] args) {
        SpringApplication application = new SpringApplication(WalnutSeedApplication.class);
        application.setApplicationStartup(new BufferingApplicationStartup(2048));
        application.run(args);
    }

}
