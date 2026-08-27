package com.walnut.seed.common.core.domain;

import com.baomidou.mybatisplus.core.metadata.IPage;

import java.io.Serial;
import java.io.Serializable;
import java.util.List;

/**
 * 分页结果
 *
 * @author deepin_sir
 */
public record PageResult<T>(List<T> rows, long total) implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 从 MyBatis-Plus 分页结果构建
     *
     * @param page MyBatis-Plus 分页结果
     * @return 分页结果
     */
    public static <T> PageResult<T> of(IPage<T> page) {
        return new PageResult<>(page.getRecords(), page.getTotal());
    }
}
