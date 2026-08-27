package com.walnut.seed.module.system.service.impl;

import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.module.system.domain.entity.SysSocial;
import com.walnut.seed.module.system.domain.req.SysSocialReq;
import com.walnut.seed.module.system.domain.resp.SysSocialResp;
import com.walnut.seed.module.system.mapper.SysSocialMapper;
import com.walnut.seed.module.system.service.SysSocialService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 社会化关系Service业务层处理
 *
 * @author deepin_sir
 * @date 2023-06-12
 */
@RequiredArgsConstructor
@Service
public class SysSocialServiceImpl implements SysSocialService {

    private final SysSocialMapper baseMapper;


    /**
     * 查询社会化关系
     */
    @Override
    public SysSocialResp queryById(String id) {
        return baseMapper.selectVoById(id);
    }

    /**
     * 授权列表
     */
    @Override
    public List<SysSocialResp> queryList(SysSocialReq req) {
        LambdaQueryWrapper<SysSocial> lqw = new LambdaQueryWrapper<SysSocial>()
            .eq(ObjectUtil.isNotNull(req.getUserId()), SysSocial::getUserId, req.getUserId())
            .eq(StringUtils.isNotBlank(req.getAuthId()), SysSocial::getAuthId, req.getAuthId())
            .eq(StringUtils.isNotBlank(req.getSource()), SysSocial::getSource, req.getSource());
        return baseMapper.selectVoList(lqw);
    }

    @Override
    public List<SysSocialResp> queryListByUserId(Long userId) {
        return baseMapper.selectVoList(new LambdaQueryWrapper<SysSocial>().eq(SysSocial::getUserId, userId));
    }


    /**
     * 新增社会化关系
     */
    @Override
    public Boolean insertByBo(SysSocialReq req) {
        SysSocial add = MapstructUtils.convert(req, SysSocial.class);
        validEntityBeforeSave(add);
        boolean flag = baseMapper.insert(add) > 0;
        if (flag) {
            if (add != null) {
                req.setId(add.getId());
            } else {
                return false;
            }
        }
        return flag;
    }

    /**
     * 更新社会化关系
     */
    @Override
    public Boolean updateByBo(SysSocialReq req) {
        SysSocial update = MapstructUtils.convert(req, SysSocial.class);
        validEntityBeforeSave(update);
        return baseMapper.updateById(update) > 0;
    }

    /**
     * 保存前的数据校验
     */
    private void validEntityBeforeSave(SysSocial entity) {
        //TODO 做一些数据校验,如唯一约束
    }


    /**
     * 删除社会化关系
     */
    @Override
    public Boolean deleteWithValidById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }


    /**
     * 根据 authId 查询用户信息
     *
     * @param authId 认证id
     * @return 授权信息
     */
    @Override
    public List<SysSocialResp> selectByAuthId(String authId) {
        return baseMapper.selectVoList(new LambdaQueryWrapper<SysSocial>().eq(SysSocial::getAuthId, authId));
    }

}
