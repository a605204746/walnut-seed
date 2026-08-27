package com.walnut.seed.module.system.service.impl;

import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.module.system.domain.entity.SysDictData;
import com.walnut.seed.module.system.domain.req.SysDictDataReq;
import com.walnut.seed.module.system.domain.resp.SysDictDataResp;
import com.walnut.seed.module.system.mapper.SysDictDataMapper;
import com.walnut.seed.module.system.service.SysDictDataService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 字典 业务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysDictDataServiceImpl implements SysDictDataService {

    private final SysDictDataMapper baseMapper;

    @Override
    public PageResult<SysDictDataResp> selectPageDictDataList(SysDictDataReq req) {
        LambdaQueryWrapper<SysDictData> lqw = buildQueryWrapper(req);
        Page<SysDictDataResp> page = baseMapper.selectVoPage(req.buildPage(), lqw);
        return PageResult.of(page);
    }

    @Override
    public List<SysDictDataResp> selectDictDataList(SysDictDataReq req) {
        LambdaQueryWrapper<SysDictData> lqw = buildQueryWrapper(req);
        return baseMapper.selectVoList(lqw);
    }

    private LambdaQueryWrapper<SysDictData> buildQueryWrapper(SysDictDataReq req) {
        LambdaQueryWrapper<SysDictData> lqw = Wrappers.lambdaQuery();
        lqw.eq(req.getDictSort() != null, SysDictData::getDictSort, req.getDictSort());
        lqw.like(StringUtils.isNotBlank(req.getDictLabel()), SysDictData::getDictLabel, req.getDictLabel());
        lqw.eq(StringUtils.isNotBlank(req.getDictType()), SysDictData::getDictType, req.getDictType());
        lqw.orderByAsc(SysDictData::getDictSort, SysDictData::getId);
        return lqw;
    }

    @Override
    public String selectDictLabel(String dictType, String dictValue) {
        return baseMapper.selectOne(new LambdaQueryWrapper<SysDictData>()
                        .select(SysDictData::getDictLabel)
                        .eq(SysDictData::getDictType, dictType)
                        .eq(SysDictData::getDictValue, dictValue))
                .getDictLabel();
    }

    @Override
    public SysDictDataResp selectDictDataById(Long dictCode) {
        return baseMapper.selectVoById(dictCode);
    }

    @Override
    public void deleteDictDataByIds(List<Long> dictCodes) {
        List<SysDictData> list = baseMapper.selectByIds(dictCodes);
        baseMapper.deleteByIds(dictCodes);
        list.forEach(x -> RedisUtils.deleteObject(CacheNames.SYS_DICT_KEY + x.getDictType()));
    }

    @Override
    public List<SysDictDataResp> insertDictData(SysDictDataReq req) {
        SysDictData data = MapstructUtils.convert(req, SysDictData.class);
        int row = baseMapper.insert(data);
        if (row > 0) {
            List<SysDictDataResp> dictDatas = baseMapper.selectDictDataByType(data.getDictType());
            RedisUtils.setCacheObject(CacheNames.SYS_DICT_KEY + data.getDictType(), dictDatas);
            return dictDatas;
        }
        throw new ServiceException("操作失败");
    }

    @Override
    public List<SysDictDataResp> updateDictData(SysDictDataReq req) {
        SysDictData data = MapstructUtils.convert(req, SysDictData.class);
        int row = baseMapper.updateById(data);
        if (row > 0) {
            List<SysDictDataResp> dictDatas = baseMapper.selectDictDataByType(data.getDictType());
            RedisUtils.setCacheObject(CacheNames.SYS_DICT_KEY + data.getDictType(), dictDatas);
            return dictDatas;
        }
        throw new ServiceException("操作失败");
    }

    @Override
    public boolean checkDictDataUnique(SysDictDataReq dict) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysDictData>()
                .eq(SysDictData::getDictType, dict.getDictType())
                .eq(SysDictData::getDictValue, dict.getDictValue())
                .ne(ObjectUtil.isNotNull(dict.getId()), SysDictData::getId, dict.getId()));
        return !exist;
    }

}
