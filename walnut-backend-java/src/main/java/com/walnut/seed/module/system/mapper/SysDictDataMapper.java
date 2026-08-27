package com.walnut.seed.module.system.mapper;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.walnut.seed.common.mybatis.core.mapper.BaseMapperPlus;
import com.walnut.seed.module.system.domain.entity.SysDictData;
import com.walnut.seed.module.system.domain.resp.SysDictDataResp;

import java.util.List;

/**
 * 字典表 数据层
 *
 * @author deepin_sir
 */
public interface SysDictDataMapper extends BaseMapperPlus<SysDictData, SysDictDataResp> {

    /**
     * 根据字典类型查询字典数据列表
     *
     * @param dictType 字典类型
     * @return 符合条件的字典数据列表
     */
    default List<SysDictDataResp> selectDictDataByType(String dictType) {
        return selectVoList(
                new LambdaQueryWrapper<SysDictData>()
                        .eq(SysDictData::getDictType, dictType)
                        .orderByAsc(SysDictData::getDictSort));
    }
}
