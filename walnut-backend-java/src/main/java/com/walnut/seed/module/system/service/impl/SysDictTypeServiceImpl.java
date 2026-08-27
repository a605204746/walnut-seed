package com.walnut.seed.module.system.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.module.system.domain.dto.DictDataDTO;
import com.walnut.seed.module.system.domain.dto.DictTypeDTO;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.service.DictService;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.SpringUtils;
import com.walnut.seed.common.core.utils.StreamUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.module.system.domain.entity.SysDictData;
import com.walnut.seed.module.system.domain.entity.SysDictType;
import com.walnut.seed.module.system.domain.req.SysDictTypeReq;
import com.walnut.seed.module.system.domain.resp.SysDictDataResp;
import com.walnut.seed.module.system.domain.resp.SysDictTypeResp;
import com.walnut.seed.module.system.mapper.SysDictDataMapper;
import com.walnut.seed.module.system.mapper.SysDictTypeMapper;
import com.walnut.seed.module.system.service.SysDictTypeService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

/**
 * 字典 业务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysDictTypeServiceImpl implements SysDictTypeService, DictService {

    private final SysDictTypeMapper baseMapper;
    private final SysDictDataMapper dictDataMapper;

    @Override
    public PageResult<SysDictTypeResp> selectPageDictTypeList(SysDictTypeReq req) {
        LambdaQueryWrapper<SysDictType> lqw = buildQueryWrapper(req);
        Page<SysDictTypeResp> page = baseMapper.selectVoPage(req.buildPage(), lqw);
        return PageResult.of(page);
    }

    @Override
    public List<SysDictTypeResp> selectDictTypeList(SysDictTypeReq req) {
        LambdaQueryWrapper<SysDictType> lqw = buildQueryWrapper(req);
        return baseMapper.selectVoList(lqw);
    }

    private LambdaQueryWrapper<SysDictType> buildQueryWrapper(SysDictTypeReq req) {
        LambdaQueryWrapper<SysDictType> lqw = Wrappers.lambdaQuery();
        lqw.like(StringUtils.isNotBlank(req.getDictName()), SysDictType::getDictName, req.getDictName());
        lqw.like(StringUtils.isNotBlank(req.getDictType()), SysDictType::getDictType, req.getDictType());
        lqw.between(req.getBeginTime() != null && req.getEndTime() != null,
                SysDictType::getCreateTime, req.getBeginTime(), req.getEndTime());
        lqw.orderByAsc(SysDictType::getId);
        return lqw;
    }

    @Override
    public List<SysDictTypeResp> selectDictTypeAll() {
        return baseMapper.selectVoList();
    }

    @Override
    public List<SysDictDataResp> selectDictDataByType(String dictType) {
        List<SysDictDataResp> dictDatas = RedisUtils.getOrLoad(CacheNames.SYS_DICT_KEY + dictType, null, () -> {
            List<SysDictDataResp> list = dictDataMapper.selectDictDataByType(dictType);
            // 空集合也缓存，防止缓存穿透
            return CollUtil.isNotEmpty(list) ? list : new ArrayList<>();
        });
        return dictDatas.isEmpty() ? null : dictDatas;
    }

    @Override
    public SysDictTypeResp selectDictTypeById(Long dictId) {
        return baseMapper.selectVoById(dictId);
    }

    @Override
    public SysDictTypeResp selectDictTypeByType(String dictType) {
        return RedisUtils.getOrLoad(CacheNames.SYS_DICT_TYPE + dictType, null,
                () -> baseMapper.selectVoOne(new LambdaQueryWrapper<SysDictType>().eq(SysDictType::getDictType, dictType)));
    }

    @Override
    public void deleteDictTypeByIds(List<Long> dictIds) {
        List<SysDictType> list = baseMapper.selectByIds(dictIds);
        list.forEach(x -> {
            boolean assigned = dictDataMapper.exists(new LambdaQueryWrapper<SysDictData>()
                    .eq(SysDictData::getDictType, x.getDictType()));
            if (assigned) {
                throw new ServiceException("{}已分配,不能删除", x.getDictName());
            }
        });
        baseMapper.deleteByIds(dictIds);
        list.forEach(x -> {
            RedisUtils.deleteObject(CacheNames.SYS_DICT_KEY + x.getDictType());
            RedisUtils.deleteObject(CacheNames.SYS_DICT_TYPE + x.getDictType());
        });
    }

    @Override
    public void resetDictCache() {
        RedisUtils.deleteByPattern(CacheNames.SYS_DICT_KEY + "*");
        RedisUtils.deleteByPattern(CacheNames.SYS_DICT_TYPE + "*");
    }

    @Override
    public List<SysDictDataResp> insertDictType(SysDictTypeReq req) {
        SysDictType dict = MapstructUtils.convert(req, SysDictType.class);
        int row = baseMapper.insert(dict);
        if (row > 0) {
            // 新增 type 下无 data 数据 缓存空集合防止缓存穿透
            RedisUtils.setCacheObject(CacheNames.SYS_DICT_KEY + req.getDictType(), new ArrayList<>());
            return new ArrayList<>();
        }
        throw new ServiceException("操作失败");
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<SysDictDataResp> updateDictType(SysDictTypeReq req) {
        SysDictType dict = MapstructUtils.convert(req, SysDictType.class);
        SysDictType oldDict = baseMapper.selectById(dict.getId());
        dictDataMapper.update(null, new LambdaUpdateWrapper<SysDictData>()
                .set(SysDictData::getDictType, dict.getDictType())
                .eq(SysDictData::getDictType, oldDict.getDictType()));
        int row = baseMapper.updateById(dict);
        if (row > 0) {
            // 事务内只做删除，提交后下次读取自动重建缓存
            RedisUtils.deleteObject(CacheNames.SYS_DICT_KEY + oldDict.getDictType());
            RedisUtils.deleteObject(CacheNames.SYS_DICT_TYPE + oldDict.getDictType());
            RedisUtils.deleteObject(CacheNames.SYS_DICT_KEY + dict.getDictType());
            RedisUtils.deleteObject(CacheNames.SYS_DICT_TYPE + dict.getDictType());
            return dictDataMapper.selectDictDataByType(dict.getDictType());
        }
        throw new ServiceException("操作失败");
    }

    @Override
    public boolean checkDictTypeUnique(SysDictTypeReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysDictType>()
                .eq(SysDictType::getDictType, req.getDictType())
                .ne(ObjectUtil.isNotNull(req.getId()), SysDictType::getId, req.getId()));
        return !exist;
    }

    @Override
    public String getDictLabel(String dictType, String dictValue, String separator) {
        List<SysDictDataResp> datas = SpringUtils.getAopProxy(this).selectDictDataByType(dictType);
        if (CollUtil.isEmpty(datas)) {
            return StringUtils.EMPTY;
        }
        Map<String, String> map = StreamUtils.toMap(datas, SysDictDataResp::getDictValue, SysDictDataResp::getDictLabel);
        if (StringUtils.containsAny(dictValue, separator)) {
            return Arrays.stream(dictValue.split(separator))
                    .map(v -> map.getOrDefault(v, StringUtils.EMPTY))
                    .collect(Collectors.joining(separator));
        } else {
            return map.getOrDefault(dictValue, StringUtils.EMPTY);
        }
    }

    @Override
    public String getDictValue(String dictType, String dictLabel, String separator) {
        List<SysDictDataResp> datas = SpringUtils.getAopProxy(this).selectDictDataByType(dictType);
        if (CollUtil.isEmpty(datas)) {
            return StringUtils.EMPTY;
        }
        Map<String, String> map = StreamUtils.toMap(datas, SysDictDataResp::getDictLabel, SysDictDataResp::getDictValue);
        if (StringUtils.containsAny(dictLabel, separator)) {
            return Arrays.stream(dictLabel.split(separator))
                    .map(l -> map.getOrDefault(l, StringUtils.EMPTY))
                    .collect(Collectors.joining(separator));
        } else {
            return map.getOrDefault(dictLabel, StringUtils.EMPTY);
        }
    }

    @Override
    public Map<String, String> getAllDictByDictType(String dictType) {
        List<SysDictDataResp> list = SpringUtils.getAopProxy(this).selectDictDataByType(dictType);
        if (CollUtil.isEmpty(list)) {
            return new HashMap<>();
        }
        // 保证顺序
        LinkedHashMap<String, String> map = new LinkedHashMap<>();
        for (SysDictDataResp vo : list) {
            map.put(vo.getDictValue(), vo.getDictLabel());
        }
        return map;
    }

    @Override
    public DictTypeDTO getDictType(String dictType) {
        SysDictTypeResp vo = SpringUtils.getAopProxy(this).selectDictTypeByType(dictType);
        if (ObjectUtil.isNull(vo)) {
            return null;
        }
        return BeanUtil.toBean(vo, DictTypeDTO.class);
    }

    @Override
    public List<DictDataDTO> getDictData(String dictType) {
        List<SysDictDataResp> list = SpringUtils.getAopProxy(this).selectDictDataByType(dictType);
        if (CollUtil.isEmpty(list)) {
            return new ArrayList<>();
        }
        return BeanUtil.copyToList(list, DictDataDTO.class);
    }

}
