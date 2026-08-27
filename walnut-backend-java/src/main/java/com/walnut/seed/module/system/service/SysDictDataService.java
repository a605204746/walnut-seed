package com.walnut.seed.module.system.service;
import com.walnut.seed.common.core.domain.PageResult;

import com.walnut.seed.module.system.domain.req.SysDictDataReq;
import com.walnut.seed.module.system.domain.resp.SysDictDataResp;

import java.util.List;

/**
 * 字典 业务层
 *
 * @author deepin_sir
 */
public interface SysDictDataService {

    /**
     * 分页查询字典数据列表
     *
     * @param dictData  查询条件
     * @param pageQuery 分页参数
     * @return 字典数据分页列表
     */
    PageResult<SysDictDataResp> selectPageDictDataList(SysDictDataReq dictData);

    /**
     * 根据条件分页查询字典数据
     *
     * @param dictData 字典数据信息
     * @return 字典数据集合信息
     */
    List<SysDictDataResp> selectDictDataList(SysDictDataReq dictData);

    /**
     * 根据字典类型和字典键值查询字典数据信息
     *
     * @param dictType  字典类型
     * @param dictValue 字典键值
     * @return 字典标签
     */
    String selectDictLabel(String dictType, String dictValue);

    /**
     * 根据字典数据ID查询信息
     *
     * @param dictCode 字典数据ID
     * @return 字典数据
     */
    SysDictDataResp selectDictDataById(Long dictCode);

    /**
     * 批量删除字典数据信息
     *
     * @param dictCodes 需要删除的字典数据ID
     */
    void deleteDictDataByIds(List<Long> dictCodes);

    /**
     * 新增保存字典数据信息
     *
     * @param req 字典数据信息
     * @return 结果
     */
    List<SysDictDataResp> insertDictData(SysDictDataReq req);

    /**
     * 修改保存字典数据信息
     *
     * @param req 字典数据信息
     * @return 结果
     */
    List<SysDictDataResp> updateDictData(SysDictDataReq req);

    /**
     * 校验字典键值是否唯一
     *
     * @param dict 字典数据
     * @return 结果
     */
    boolean checkDictDataUnique(SysDictDataReq dict);

}
