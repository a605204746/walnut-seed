package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.crypto.SecureUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.module.system.domain.entity.SysClient;
import com.walnut.seed.module.system.domain.req.SysClientReq;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.system.mapper.SysClientMapper;
import com.walnut.seed.module.system.service.SysClientService;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Collection;
import java.util.List;

/**
 * 客户端管理Service业务层处理
 *
 * @author deepin_sir
 */
@Slf4j
@RequiredArgsConstructor
@Service
public class SysClientServiceImpl implements SysClientService {

    private final SysClientMapper baseMapper;

    @Override
    public SysClientResp queryById(Long id) {
        SysClientResp vo = baseMapper.selectVoById(id);
        vo.setGrantTypeList(StringUtils.splitList(vo.getGrantType()));
        return vo;
    }

    @Override
    public SysClientResp queryByClientId(String clientId) {
        return RedisUtils.getOrLoad(CacheNames.SYS_CLIENT + clientId, Duration.ofDays(30),
            () -> baseMapper.selectVoOne(new LambdaQueryWrapper<SysClient>().eq(SysClient::getClientId, clientId)));
    }

    @Override
    public PageResult<SysClientResp> queryPageList(SysClientReq req) {
        LambdaQueryWrapper<SysClient> lqw = buildQueryWrapper(req);
        Page<SysClientResp> result = baseMapper.selectVoPage(req.buildPage(), lqw);
        result.getRecords().forEach(r -> r.setGrantTypeList(StringUtils.splitList(r.getGrantType())));
        return PageResult.of(result);
    }

    @Override
    public List<SysClientResp> queryList(SysClientReq req) {
        LambdaQueryWrapper<SysClient> lqw = buildQueryWrapper(req);
        return baseMapper.selectVoList(lqw);
    }

    private LambdaQueryWrapper<SysClient> buildQueryWrapper(SysClientReq req) {
        LambdaQueryWrapper<SysClient> lqw = Wrappers.lambdaQuery();
        lqw.eq(StringUtils.isNotBlank(req.getClientId()), SysClient::getClientId, req.getClientId());
        lqw.eq(StringUtils.isNotBlank(req.getClientKey()), SysClient::getClientKey, req.getClientKey());
        lqw.eq(StringUtils.isNotBlank(req.getClientSecret()), SysClient::getClientSecret, req.getClientSecret());
        lqw.eq(StringUtils.isNotBlank(req.getStatus()), SysClient::getStatus, req.getStatus());
        lqw.orderByAsc(SysClient::getId);
        return lqw;
    }

    @Override
    public Boolean insertByBo(SysClientReq req) {
        SysClient add = MapstructUtils.convert(req, SysClient.class);
        add.setGrantType(CollUtil.join(req.getGrantTypeList(), StringUtils.SEPARATOR));
        // 生成clientid
        String clientKey = req.getClientKey();
        String clientSecret = req.getClientSecret();
        add.setClientId(SecureUtil.md5(clientKey + clientSecret));
        boolean flag = baseMapper.insert(add) > 0;
        if (flag) {
            req.setId(add.getId());
        }
        return flag;
    }

    @Override
    public Boolean updateByBo(SysClientReq req) {
        SysClient update = MapstructUtils.convert(req, SysClient.class);
        update.setGrantType(StringUtils.joinComma(req.getGrantTypeList()));
        boolean flag = baseMapper.updateById(update) > 0;
        if (flag) {
            RedisUtils.deleteObject(CacheNames.SYS_CLIENT + req.getClientId());
        }
        return flag;
    }

    @Override
    public int updateClientStatus(String clientId, String status) {
        int row = baseMapper.update(null,
            new LambdaUpdateWrapper<SysClient>()
                .set(SysClient::getStatus, status)
                .eq(SysClient::getClientId, clientId));
        if (row > 0) {
            RedisUtils.deleteObject(CacheNames.SYS_CLIENT + clientId);
        }
        return row;
    }

    @Override
    public Boolean deleteWithValidByIds(Collection<Long> ids, Boolean isValid) {
        boolean flag = baseMapper.deleteByIds(ids) > 0;
        if (flag) {
            RedisUtils.deleteByPattern(CacheNames.SYS_CLIENT + "*");
        }
        return flag;
    }

    @Override
    public boolean checkClickKeyUnique(SysClientReq client) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysClient>()
            .eq(SysClient::getClientKey, client.getClientKey())
            .ne(ObjectUtil.isNotNull(client.getId()), SysClient::getId, client.getId()));
        return !exist;
    }

}
