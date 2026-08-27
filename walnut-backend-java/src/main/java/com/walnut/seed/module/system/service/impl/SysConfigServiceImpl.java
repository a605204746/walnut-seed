package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.convert.Convert;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.ObjectUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.module.system.domain.entity.SysConfig;
import com.walnut.seed.module.system.domain.req.SysConfigReq;
import com.walnut.seed.module.system.domain.resp.SysConfigResp;
import com.walnut.seed.module.system.mapper.SysConfigMapper;
import com.walnut.seed.module.system.service.SysConfigService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 参数配置 服务层实现
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysConfigServiceImpl implements SysConfigService {

    private final SysConfigMapper baseMapper;

    @Override
    public PageResult<SysConfigResp> selectPageConfigList(SysConfigReq req) {
        LambdaQueryWrapper<SysConfig> lqw = buildQueryWrapper(req);
        Page<SysConfigResp> page = baseMapper.selectVoPage(req.buildPage(), lqw);
        return PageResult.of(page);
    }

    @Override
    public SysConfigResp selectConfigById(Long configId) {
        return baseMapper.selectVoById(configId);
    }

    @Override
    public String selectConfigByKey(String configKey) {
        return RedisUtils.getOrLoad(CacheNames.SYS_CONFIG_KEY + configKey, null, () -> {
            SysConfig retConfig = baseMapper.selectOne(new LambdaQueryWrapper<SysConfig>()
                .eq(SysConfig::getConfigKey, configKey));
            return ObjectUtils.notNullGetter(retConfig, SysConfig::getConfigValue, StringUtils.EMPTY);
        });
    }

    @Override
    public boolean selectRegisterEnabled() {
        String configValue = this.selectConfigByKey("sys.account.registerUser");
        return Convert.toBool(configValue);
    }

    @Override
    public List<SysConfigResp> selectConfigList(SysConfigReq req) {
        LambdaQueryWrapper<SysConfig> lqw = buildQueryWrapper(req);
        return baseMapper.selectVoList(lqw);
    }

    private LambdaQueryWrapper<SysConfig> buildQueryWrapper(SysConfigReq req) {
        LambdaQueryWrapper<SysConfig> lqw = Wrappers.lambdaQuery();
        lqw.like(StringUtils.isNotBlank(req.getConfigName()), SysConfig::getConfigName, req.getConfigName());
        lqw.eq(StringUtils.isNotBlank(req.getConfigType()), SysConfig::getConfigType, req.getConfigType());
        lqw.like(StringUtils.isNotBlank(req.getConfigKey()), SysConfig::getConfigKey, req.getConfigKey());
        lqw.between(req.getBeginTime() != null && req.getEndTime() != null,
            SysConfig::getCreateTime, req.getBeginTime(), req.getEndTime());
        lqw.orderByAsc(SysConfig::getId);
        return lqw;
    }

    @Override
    public String insertConfig(SysConfigReq req) {
        SysConfig config = MapstructUtils.convert(req, SysConfig.class);
        int row = baseMapper.insert(config);
        if (row > 0) {
            RedisUtils.setCacheObject(CacheNames.SYS_CONFIG_KEY + req.getConfigKey(), req.getConfigValue());
            return req.getConfigValue();
        }
        throw new ServiceException("操作失败");
    }

    @Override
    public String updateConfig(SysConfigReq req) {
        int row = 0;
        SysConfig config = MapstructUtils.convert(req, SysConfig.class);
        if (req.getId() != null) {
            SysConfig temp = baseMapper.selectById(req.getId());
            if (!StringUtils.equals(temp.getConfigKey(), req.getConfigKey())) {
                RedisUtils.deleteObject(CacheNames.SYS_CONFIG_KEY + temp.getConfigKey());
            }
            row = baseMapper.updateById(config);
        } else {
            RedisUtils.deleteObject(CacheNames.SYS_CONFIG_KEY + req.getConfigKey());
            row = baseMapper.update(config, new LambdaQueryWrapper<SysConfig>()
                .eq(SysConfig::getConfigKey, req.getConfigKey()));
        }
        if (row > 0) {
            RedisUtils.setCacheObject(CacheNames.SYS_CONFIG_KEY + req.getConfigKey(), req.getConfigValue());
            return req.getConfigValue();
        }
        throw new ServiceException("操作失败");
    }

    @Override
    public void deleteConfigByIds(List<Long> configIds) {
        List<SysConfig> list = baseMapper.selectByIds(configIds);
        list.forEach(req -> {
            if (StringUtils.equals(SystemConstants.YES, req.getConfigType())) {
                throw new ServiceException("内置参数【{}】不能删除", req.getConfigKey());
            }
            RedisUtils.deleteObject(CacheNames.SYS_CONFIG_KEY + req.getConfigKey());
        });
        baseMapper.deleteByIds(configIds);
    }

    @Override
    public void resetConfigCache() {
        RedisUtils.deleteByPattern(CacheNames.SYS_CONFIG_KEY + "*");
    }

    @Override
    public boolean checkConfigKeyUnique(SysConfigReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysConfig>()
            .eq(SysConfig::getConfigKey, req.getConfigKey())
            .ne(ObjectUtil.isNotNull(req.getId()), SysConfig::getId, req.getId()));
        return !exist;
    }

}
