package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.ObjectUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.module.system.domain.entity.SysNotice;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.req.SysNoticeReq;
import com.walnut.seed.module.system.domain.resp.SysNoticeResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.module.system.mapper.SysNoticeMapper;
import com.walnut.seed.module.system.mapper.SysUserMapper;
import com.walnut.seed.module.system.service.SysNoticeService;
import org.springframework.stereotype.Service;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import com.walnut.seed.common.core.utils.StreamUtils;

import java.util.Arrays;
import java.util.Map;
import java.util.List;

/**
 * 公告 服务层实现
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysNoticeServiceImpl implements SysNoticeService {

    private final SysNoticeMapper baseMapper;
    private final SysUserMapper userMapper;

    /**
     * 批量回填公告展示字段（创建人账号）
     */
    private void fillNoticeResp(List<SysNoticeResp> list) {
        if (CollUtil.isEmpty(list)) {
            return;
        }
        List<Long> userIds = list.stream().map(SysNoticeResp::getCreateBy)
            .filter(ObjectUtil::isNotNull).distinct().toList();
        if (CollUtil.isEmpty(userIds)) {
            return;
        }
        List<SysUser> users = userMapper.selectList(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getId, SysUser::getUserName)
            .in(SysUser::getId, userIds));
        Map<Long, String> userNames = StreamUtils.toMap(users, SysUser::getId, SysUser::getUserName);
        list.forEach(notice -> notice.setCreateByName(userNames.get(notice.getCreateBy())));
    }

    @Override
    public PageResult<SysNoticeResp> selectPageNoticeList(SysNoticeReq req) {
        LambdaQueryWrapper<SysNotice> lqw = buildQueryWrapper(req);
        Page<SysNoticeResp> page = baseMapper.selectVoPage(req.buildPage(), lqw);
        fillNoticeResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public SysNoticeResp selectNoticeById(Long noticeId) {
        SysNoticeResp notice = baseMapper.selectVoById(noticeId);
        fillNoticeResp(notice == null ? null : List.of(notice));
        return notice;
    }

    @Override
    public List<SysNoticeResp> selectNoticeList(SysNoticeReq req) {
        LambdaQueryWrapper<SysNotice> lqw = buildQueryWrapper(req);
        List<SysNoticeResp> list = baseMapper.selectVoList(lqw);
        fillNoticeResp(list);
        return list;
    }

    private LambdaQueryWrapper<SysNotice> buildQueryWrapper(SysNoticeReq req) {
        LambdaQueryWrapper<SysNotice> lqw = Wrappers.lambdaQuery();
        lqw.like(StringUtils.isNotBlank(req.getNoticeTitle()), SysNotice::getNoticeTitle, req.getNoticeTitle());
        lqw.eq(StringUtils.isNotBlank(req.getNoticeType()), SysNotice::getNoticeType, req.getNoticeType());
        if (StringUtils.isNotBlank(req.getCreateByName())) {
            SysUserResp sysUser = userMapper.selectVoOne(new LambdaQueryWrapper<SysUser>().eq(SysUser::getUserName, req.getCreateByName()));
            lqw.eq(SysNotice::getCreateBy, ObjectUtils.notNullGetter(sysUser, SysUserResp::getId));
        }
        lqw.orderByAsc(SysNotice::getId);
        return lqw;
    }

    @Override
    public int insertNotice(SysNoticeReq req) {
        SysNotice notice = MapstructUtils.convert(req, SysNotice.class);
        return baseMapper.insert(notice);
    }

    @Override
    public int updateNotice(SysNoticeReq req) {
        SysNotice notice = MapstructUtils.convert(req, SysNotice.class);
        return baseMapper.updateById(notice);
    }

    @Override
    public int deleteNoticeById(Long noticeId) {
        return baseMapper.deleteById(noticeId);
    }

    @Override
    public int deleteNoticeByIds(Long[] noticeIds) {
        return baseMapper.deleteByIds(Arrays.asList(noticeIds));
    }
}
