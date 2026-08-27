package com.walnut.seed.common.core.domain;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.metadata.OrderItem;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.sql.SqlUtil;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

/**
 * 分页查询基类 — Req 类继承此类即可获得分页能力
 *
 * @author deepin_sir
 */
@Data
public class PageReq implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 当前页码（默认第1页）
     */
    private Integer pageNum;

    /**
     * 每页条数（默认查全部）
     */
    private Integer pageSize;

    /**
     * 排序列
     */
    private String orderByColumn;

    /**
     * 排序方向 desc 或 asc
     */
    private String isAsc;

    private static final int DEFAULT_PAGE_NUM = 1;
    private static final int DEFAULT_PAGE_SIZE = Integer.MAX_VALUE;

    /**
     * 构建 MyBatis-Plus 分页对象
     */
    @JsonIgnore
    public <T> Page<T> buildPage() {
        int pn = ObjectUtil.defaultIfNull(getPageNum(), DEFAULT_PAGE_NUM);
        int ps = ObjectUtil.defaultIfNull(getPageSize(), DEFAULT_PAGE_SIZE);
        if (pn <= 0) {
            pn = DEFAULT_PAGE_NUM;
        }
        Page<T> page = new Page<>(pn, ps);
        List<OrderItem> orderItems = buildOrderItem();
        if (CollUtil.isNotEmpty(orderItems)) {
            page.addOrder(orderItems);
        }
        return page;
    }

    private List<OrderItem> buildOrderItem() {
        if (StringUtils.isBlank(orderByColumn) || StringUtils.isBlank(isAsc)) {
            return null;
        }
        String orderBy = SqlUtil.escapeOrderBySql(orderByColumn);
        orderBy = StringUtils.toUnderScoreCase(orderBy);
        isAsc = StringUtils.replaceEach(isAsc, new String[]{"ascending", "descending"}, new String[]{"asc", "desc"});

        String[] orderByArr = orderBy.split(StringUtils.SEPARATOR);
        String[] isAscArr = isAsc.split(StringUtils.SEPARATOR);
        if (isAscArr.length != 1 && isAscArr.length != orderByArr.length) {
            throw new ServiceException("排序参数有误");
        }

        List<OrderItem> list = new ArrayList<>();
        for (int i = 0; i < orderByArr.length; i++) {
            String orderByStr = orderByArr[i];
            String isAscStr = isAscArr.length == 1 ? isAscArr[0] : isAscArr[i];
            if ("asc".equals(isAscStr)) {
                list.add(OrderItem.asc(orderByStr));
            } else if ("desc".equals(isAscStr)) {
                list.add(OrderItem.desc(orderByStr));
            } else {
                throw new ServiceException("排序参数有误");
            }
        }
        return list;
    }
}
