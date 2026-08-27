package com.walnut.seed.common.mybatis.helper;

import cn.hutool.core.convert.Convert;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;
import com.walnut.seed.common.core.utils.sql.SqlUtil;

/**
 * 数据库助手（MySQL）
 *
 * @author deepin_sir
 */
@NoArgsConstructor(access = AccessLevel.PRIVATE)
public class DataBaseHelper {

    /**
     * 生成 FIND_IN_SET 语句片段，用于判断指定值是否存在于逗号分隔的字符串列中
     *
     * @param var1 要查找的值（支持任意类型，内部会转换成字符串）
     * @param var2 存储逗号分隔值的数据库列名
     * @return SQL 条件字符串，通常用于 where 或 apply 中拼接
     */
    public static String findInSet(Object var1, String var2) {
        String var = Convert.toStr(var1);
        SqlUtil.filterKeyword(var);
        SqlUtil.filterKeyword(var2);
        // find_in_set(100 , '0,100,101')
        return "find_in_set('%s' , %s) <> 0".formatted(var, var2);
    }
}
